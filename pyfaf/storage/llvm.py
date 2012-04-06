from . import Boolean
from . import Build
from . import Column
from . import DateTime
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import relationship

class LlvmBuild(GenericTable):
    __tablename__ = "llvm_builds"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("build_id", Integer, ForeignKey("{0}.id".format(Build.__tablename__)), nullable=True, index=True),
                    Column("started", DateTime, nullable=False),
                    Column("duration", Integer, nullable=False),
                    Column("success", Boolean, nullable=False) ]

    __lobs__ = { "result": 1 << 31 }

class LlvmBcFile(GenericTable):
    __tablename__ = "llvm_bcfiles"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("llvmbuild_id", Integer, ForeignKey("{0}.id".format(LlvmBuild.__tablename__)), nullable=False, index=True),
                    Column("path", String(256), nullable=False, index=True) ]

    __lobs__ = { "bcfile": 1 << 28 }

class LlvmResultFiles(GenericTable):
    __tablename__ = "llvm_resultfiles"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("llvmbuild_id", Integer, ForeignKey("{0}.id".format(LlvmBuild.__tablename__)), nullable=False,index=True),
                    Column("path", String(256), nullable=False, index=True) ]
