"""Export the project's PostgreSQL snapshot for import into an empty SQL Server DB.

Run: docker compose -f docker-compose.dev.yml exec -T backend python export_sqlserver.py
"""
import datetime
import json
import os
import re
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


def quote(name):
    return '[' + name.replace(']', ']]') + ']'


def literal(value, kind):
    if value is None:
        return 'NULL'
    if kind == 'jsonb':
        value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, bytes):
        return '0x' + value.hex()
    if isinstance(value, datetime.datetime):
        value = value.isoformat()
    if isinstance(value, str):
        # Avoid a standalone GO line inside text being interpreted by SSMS.
        parts = re.split(r'(\r|\n)', value)
        return ' + '.join('NCHAR(13)' if p == '\r' else 'NCHAR(10)' if p == '\n'
                          else "N'" + p.replace("'", "''") + "'" for p in parts)
    return str(value)


def column_type(c):
    kind = c['data_type']
    if kind == 'character varying':
        length = c['character_maximum_length']
        return f'nvarchar({length if length and length <= 4000 else "max"}) COLLATE Latin1_General_100_BIN2'
    return {'bigint': 'bigint', 'integer': 'int', 'smallint': 'smallint',
            'boolean': 'bit', 'text': 'nvarchar(max)', 'jsonb': 'nvarchar(max)',
            'bytea': 'varbinary(max)', 'timestamp with time zone': 'datetimeoffset(6)'}[kind]


def main():
    out = Path(__file__).parent / 'exports'
    out.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
    target = out / f'techzone_sqlserver_{stamp}.sql'
    counts = {}
    with psycopg.connect(dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'],
                         password=os.environ['POSTGRES_PASSWORD'], host=os.environ['POSTGRES_HOST'],
                         port=os.environ.get('POSTGRES_PORT', '5432'), row_factory=dict_row) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        tables = [r['table_name'] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")]
        constraints = conn.execute("""SELECT t.relname AS tbl, c.conname AS name, c.contype AS kind,
            pg_get_constraintdef(c.oid) AS definition
            FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
            WHERE c.connamespace='public'::regnamespace ORDER BY c.contype, c.conname""").fetchall()
        with target.open('w', encoding='utf-8-sig', newline='\n') as f:
            def emit(line):
                f.write(line + '\n')
            emit('-- PostgreSQL snapshot. Select an EMPTY destination database in SSMS before executing.')
            emit('-- JSON -> nvarchar(max); binary -> varbinary(max); timezone -> datetimeoffset(6).')
            emit('-- Secondary PostgreSQL indexes are not copied. Django app still uses PostgreSQL.')
            emit('SET NOCOUNT ON;\nSET XACT_ABORT ON;\nBEGIN TRY\nBEGIN TRANSACTION;')
            emit("IF EXISTS (SELECT 1 FROM sys.tables WHERE is_ms_shipped=0) THROW 50000, 'Destination database must be empty.', 1;")
            for table in tables:
                columns = conn.execute("SELECT * FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (table,)).fetchall()
                definitions = []
                identity = False
                for c in columns:
                    auto = c['is_identity'] == 'YES' or (c['column_default'] or '').startswith('nextval(')
                    if c['column_default'] and not auto:
                        raise ValueError(f'Unmapped default: {table}.{c["column_name"]}')
                    identity |= auto
                    definitions.append(quote(c['column_name']) + ' ' + column_type(c) +
                                       (' IDENTITY(1,1)' if auto else '') +
                                       (' NULL' if c['is_nullable'] == 'YES' else ' NOT NULL'))
                dest = '[dbo].' + quote(table)
                emit(f'CREATE TABLE {dest} (\n  ' + ',\n  '.join(definitions) + '\n);')
                if identity:
                    emit(f'SET IDENTITY_INSERT {dest} ON;')
                count = 0
                with conn.cursor(name='export_rows') as cur:
                    cur.execute(sql.SQL('SELECT * FROM public.{}').format(sql.Identifier(table)))
                    for row in cur:
                        values = [literal(row[c['column_name']], c['data_type']) for c in columns]
                        emit(f'INSERT INTO {dest} (' + ','.join(quote(c['column_name']) for c in columns) + ') VALUES (' + ','.join(values) + ');')
                        count += 1
                if identity:
                    emit(f'SET IDENTITY_INSERT {dest} OFF;')
                counts[table] = count
            for c in constraints:
                definition = c['definition'].replace(' DEFERRABLE INITIALLY DEFERRED', '')
                if c['kind'] not in ('p', 'u', 'f', 'c'):
                    raise ValueError(f'Unsupported constraint: {definition}')
                # This project's constraint expressions use only simple identifiers,
                # parentheses and integer comparisons, verified from pg_constraint.
                if not re.fullmatch(r'[A-Za-z0-9_ (),>=]+', definition):
                    raise ValueError(f'Unsupported constraint expression: {definition}')
                definition = re.sub(r'REFERENCES (\w+)', lambda m: 'REFERENCES [dbo].' + quote(m[1]), definition)
                emit(f'ALTER TABLE [dbo].{quote(c["tbl"])} ADD CONSTRAINT {quote(c["name"])} {definition};')
            for table, count in counts.items():
                emit(f"IF (SELECT COUNT_BIG(*) FROM [dbo].{quote(table)}) <> {count} THROW 50001, 'Row count mismatch: {table}', 1;")
            emit("COMMIT TRANSACTION;\nEND TRY\nBEGIN CATCH\nIF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;\nTHROW;\nEND CATCH;")
            emit("SELECT 'Import completed' AS result;")
    report = {'file': target.name, 'tables': len(counts), 'rows': sum(counts.values()), 'table_rows': counts}
    target.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
