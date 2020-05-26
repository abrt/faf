import json

from typing import Any, Optional

import sqlalchemy as sa

class JSONType(sa.types.TypeDecorator):
    impl = sa.UnicodeText

    def process_bind_param(self, value, dialect) -> Optional[str]:
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect) -> Optional[dict]:
        if value is not None:
            value = json.loads(value)
        return value

    def process_literal_param(self, value, dialect) -> Any:
        return value

    @property
    def python_type(self) -> type:
        return json
