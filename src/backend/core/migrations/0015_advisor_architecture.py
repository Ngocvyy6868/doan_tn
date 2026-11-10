import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import core.advisor.fields


def extensions(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('CREATE EXTENSION IF NOT EXISTS vector')
        schema_editor.execute('CREATE EXTENSION IF NOT EXISTS unaccent')


def search_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION public.advisor_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent', $1) $$
    """)
    schema_editor.execute("""
        ALTER TABLE core_product ADD COLUMN search_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', public.advisor_unaccent(
            coalesce(payload->>'name','') || ' ' || coalesce(payload->>'brand','') || ' ' ||
            coalesce(payload->>'description','') || ' ' || coalesce(payload->>'specs','') || ' ' ||
            coalesce(payload->>'attributes','')
        ))) STORED
    """)
    schema_editor.execute("""
        ALTER TABLE core_product
        ADD COLUMN advisor_price numeric GENERATED ALWAYS AS
            (CASE WHEN jsonb_typeof(payload->'price') = 'number' THEN (payload->>'price')::numeric END) STORED,
        ADD COLUMN advisor_stock numeric GENERATED ALWAYS AS
            (CASE WHEN jsonb_typeof(payload->'stock') = 'number' THEN (payload->>'stock')::numeric END) STORED
    """)
    schema_editor.execute('CREATE INDEX advisor_search_gin ON core_product USING gin(search_tsv)')
    schema_editor.execute('CREATE INDEX advisor_specs_gin ON core_product USING gin ((payload->\'specs\'))')
    schema_editor.execute('CREATE INDEX advisor_embedding_hnsw ON core_product USING hnsw (embedding vector_cosine_ops)')
    schema_editor.execute("CREATE INDEX advisor_catalog_filter ON core_product (category_id, advisor_stock, advisor_price)")


def undo_search(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        for name in ('advisor_search_gin', 'advisor_specs_gin', 'advisor_embedding_hnsw', 'advisor_catalog_filter'):
            schema_editor.execute(f'DROP INDEX IF EXISTS {name}')
        schema_editor.execute('ALTER TABLE core_product DROP COLUMN IF EXISTS search_tsv, DROP COLUMN IF EXISTS advisor_price, DROP COLUMN IF EXISTS advisor_stock')
        schema_editor.execute('DROP FUNCTION IF EXISTS public.advisor_unaccent(text)')


class Migration(migrations.Migration):
    dependencies = [('core', '0014_remove_khe_ram'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.RunPython(extensions, migrations.RunPython.noop),
        migrations.AddField(model_name='product', name='embedding',
                            field=core.advisor.fields.ProductVectorField(null=True, editable=False)),
        migrations.AddField(model_name='product', name='embedding_hash',
                            field=models.CharField(max_length=64, blank=True, default='', editable=False)),
        migrations.RunPython(search_index, undo_search),
        migrations.CreateModel(name='ChatSession', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('state', models.JSONField(default=dict)),
            ('active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                      related_name='advisor_sessions', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='ChatMessage', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('role', models.CharField(max_length=12)),
            ('text', models.TextField()),
            ('data', models.JSONField(default=dict)),
            ('latency_ms', models.PositiveIntegerField(default=0)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                         related_name='messages', to='core.chatsession')),
        ], options={'ordering': ['id']}),
    ]
