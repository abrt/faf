# Copyright (C) 2012 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import datetime
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
    __lobs__ = { "packages": 1 << 22,
                 "result": 1 << 31,
                 "stdout": 1 << 22,
                 "stderr": 1 << 22 }

    id = Column(Integer, primary_key=True)
    build_id = Column(Integer, ForeignKey("{0}.id".format(Build.__tablename__)), nullable=True, index=True)
    started = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)

    build = relationship(Build)

    def add_human_readable_duration(self):
        self.dur = str(datetime.timedelta(seconds=self.duration))

    def add_nvr(self):
        self.nvr = self.build.nvr()

    def count_bcfiles(self):
        self.bcfiles_count = len(self.bc_files)

class LlvmBcFile(GenericTable):
    __tablename__ = "llvm_bcfiles"
    __lobs__ = { "bcfile": 1 << 28 }

    id = Column(Integer, primary_key=True)
    llvmbuild_id = Column(Integer, ForeignKey("{0}.id".format(LlvmBuild.__tablename__)), nullable=False, index=True)
    path = Column(String(256), nullable=False, index=True)
    llvm_build = relationship(LlvmBuild, backref="bc_files")

class LlvmResultFile(GenericTable):
    __tablename__ = "llvm_resultfiles"

    id = Column(Integer, primary_key=True)
    llvmbuild_id = Column(Integer, ForeignKey("{0}.id".format(LlvmBuild.__tablename__)), nullable=False,index=True)
    path = Column(String(256), nullable=False, index=True)
    llvm_build = relationship(LlvmBuild, backref="result_files")
