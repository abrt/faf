from . import Column
from . import DateTime
from . import GenericTable
from . import Integer
from . import String


class InvalidUReport(GenericTable):
    __tablename__ = "invalidureports"
    __lobs__ = {"ureport": 1 << 22}

    id = Column(Integer, primary_key=True)
    errormsg = Column(String(512), nullable=False)
    reporter = Column(String(64), nullable=True)
    date = Column(DateTime, nullable=False, index=True)


class UnknownOpSys(GenericTable):
    __tablename__ = "unknownopsys"

    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=True, index=True)
    version = Column(String(512), nullable=True, index=True)
    count = Column(Integer, nullable=False, default=0)
