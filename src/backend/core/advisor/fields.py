"""Small pgvector field with a JSON text representation for SQLite tests."""
import json
import math
from django.core.exceptions import ValidationError
from django.db import models


class ProductVectorField(models.TextField):
    def db_type(self, connection):
        return 'vector(1024)' if connection.vendor == 'postgresql' else 'text'

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        return value

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        value = self.to_python(value)
        if not isinstance(value, list) or len(value) != 1024 or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value
        ):
            raise ValidationError('Embedding phải có 1024 số hữu hạn.')
        return json.dumps(value)
