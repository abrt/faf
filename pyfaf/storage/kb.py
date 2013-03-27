from . import Column
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import UniqueConstraint
from . import relationship

class KbSolution(GenericTable):
    __tablename__ = "kbsolutions"

    id = Column(Integer, primary_key=True)
    cause = Column(String(256), nullable=False)
    url = Column(String(4096))
    note_text = Column(String(8192), nullable=False)
    note_html = Column(String(16384))

class KbBacktracePath(GenericTable):
    __tablename__ = "kbbacktracepath"
    __table_args__ = ( UniqueConstraint("pattern"), )

    id = Column(Integer, primary_key=True)
    pattern = Column(String(256), nullable=False, index=True)
    solution_id = Column(Integer, ForeignKey("{0}.id".format(KbSolution.__tablename__)), nullable=False, index=True)

    solution = relationship(KbSolution)
