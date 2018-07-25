import json
import sqlalchemy as sa


class JSONType(sa.types.TypeDecorator):
    impl = sa.UnicodeText

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

    def process_literal_param(self, value, dialect):
        return value

    def python_type(self):
        return json
