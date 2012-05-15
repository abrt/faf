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
from . import Arch
from . import Column
from . import Date
from . import DateTime
from . import Enum
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import OpSysComponent
from . import OpSysRelease
from . import Package
from . import Problem
from . import String
from . import SymbolSource
from . import UniqueConstraint
from . import backref
from . import relationship

class Report(GenericTable):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    type = Column(Enum("USERSPACE", "KERNEL", "PYTHON", "SELINUX", name="report_type"), nullable=False)
    first_occurence = Column(DateTime)
    last_occurence = Column(DateTime)
    count = Column(Integer, nullable=False)
    component_id = Column(Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), nullable=False, index=True)
    problem_id = Column(Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), nullable=True, index=True)
    component = relationship(OpSysComponent)
    problem = relationship(Problem, backref="reports")

class ReportBacktrace(GenericTable):
    __tablename__ = "reportbacktraces"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False, index=True)
    report = relationship(Report, backref="backtraces")

class ReportBtFrame(GenericTable):
    __tablename__ = "reportbtframes"

    backtrace_id = Column(Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), primary_key=True)
    order = Column(Integer, nullable=False, primary_key=True)
    symbolsource_id = Column(Integer, ForeignKey("{0}.id".format(SymbolSource.__tablename__)), nullable=False, index=True)
    backtrace = relationship(ReportBacktrace, backref=backref('frames', order_by="ReportBtFrame.order"))
    symbolsource = relationship(SymbolSource, backref=backref('frames'))

class ReportBtHash(GenericTable):
    __tablename__ = "reportbthashes"

    type = Column(Enum("NAMES", "HASHES", name="reportbt_hashtype"), nullable=False, primary_key=True)
    hash = Column(String(64), nullable=False, primary_key=True)
    backtrace_id = Column(Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), nullable=False, index=True, primary_key=True)
    backtrace = relationship(ReportBacktrace)

class ReportOpSysRelease(GenericTable):
    __tablename__ = "reportopsysreleases"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)
    opsysrelease = relationship(OpSysRelease)

class ReportArch(GenericTable):
    __tablename__ = "reportarchs"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    arch_id = Column(Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)
    arch = relationship(Arch)

class ReportPackage(GenericTable):
    __tablename__ = "reportpackages"
    __table_args__ = ( UniqueConstraint('report_id', 'type', 'installed_package_id', 'running_package_id'), )

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False)
    type = Column(Enum("CRASHED", "RELATED", "SELINUX_POLICY", name="reportpackage_type"))
    installed_package_id = Column(Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False)
    running_package_id = Column(Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)
    installed_package = relationship(Package, primaryjoin="Package.id==ReportPackage.installed_package_id")
    running_package = relationship(Package, primaryjoin="Package.id==ReportPackage.running_package_id")

class ReportUnknownPackage(GenericTable):
    __tablename__ = "reportunknownpackages"
    __table_args__ = ( UniqueConstraint('report_id', 'type', 'name', 'installed_epoch',
        'installed_version', 'installed_release', 'installed_arch_id', 'running_epoch',
        'running_version', 'running_release', 'running_arch_id'), )

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False)
    type = Column(Enum("CRASHED", "RELATED", "SELINUX_POLICY", name="reportpackage_type"))
    name = Column(String(64), nullable=False, index=True)
    installed_epoch = Column(Integer, nullable=False)
    installed_version = Column(String(64), nullable=False)
    installed_release = Column(String(64), nullable=False)
    installed_arch_id = Column(Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), nullable=False)
    running_epoch = Column(Integer, nullable=True)
    running_version = Column(String(64), nullable=True)
    running_release = Column(String(64), nullable=True)
    running_arch_id = Column(Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), nullable=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)
    installed_arch = relationship(Arch, primaryjoin="Arch.id==ReportUnknownPackage.installed_arch_id")
    running_arch = relationship(Arch, primaryjoin="Arch.id==ReportUnknownPackage.running_arch_id")

class ReportExecutable(GenericTable):
    __tablename__ = "reportexecutables"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    path = Column(String(512), nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="executables")

class ReportUptime(GenericTable):
    __tablename__ = "reportuptimes"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    # stored as log(uptime, 10)
    uptime_exp = Column(Integer, nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)

class ReportReason(GenericTable):
    __tablename__ = "reportreasons"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    reason = Column(String(512), nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="reasons")

class ReportSelinuxContext(GenericTable):
    __tablename__ = "reportselinuxcontexts"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    context = Column(String(256), nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="selinux_contexts")

class ReportSelinuxMode(GenericTable):
    __tablename__ = "reportselinuxmodes"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    mode = Column(Enum("DISABLED", "PERMISSIVE", "ENFORCING", name="reportselinuxmode_mode"), primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)

class ReportHistoryMonthly(GenericTable):
    __tablename__ = "reporthistorymonthly"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    month = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)
    opsysrelease = relationship(OpSysRelease)

class ReportHistoryWeekly(GenericTable):
    __tablename__ = "reporthistoryweekly"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    week = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)
    opsysrelease = relationship(OpSysRelease)

class ReportHistoryDaily(GenericTable):
    __tablename__ = "reporthistorydaily"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    day = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report)
    opsysrelease = relationship(OpSysRelease)

class ReportKernelTaintState(GenericTable):
    __tablename__ = "reportkerneltaintstates"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    state = Column(String(16), nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="kernel_taint_states")
