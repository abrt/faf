from . import Column
from . import GenericTable
from . import Integer
from . import String
from . import UniqueConstraint

class KbBacktracePath(GenericTable):
    __tablename__ = "kbbacktracepath"
    __table_args__ = ( UniqueConstraint("pattern"), )

    id = Column(Integer, primary_key=True)
    pattern = Column(String(256), nullable=False, index=True)
    cause = Column(String(256), nullable=False)
    url = Column(String(4096))
    note_text = Column(String(8192), nullable=False)
    note_html = Column(String(16384))
