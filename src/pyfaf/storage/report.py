# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

from collections import namedtuple

#no need
#import btparser

from . import Arch
from . import Boolean
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
from . import RhbzBug
from . import String
from . import SymbolSource
from . import UniqueConstraint
from . import backref
from . import relationship

from pyfaf.common import format_reason


class Report(GenericTable):
    __tablename__ = "reports"
    __lobs__ = {"oops": 1 << 16}

    id = Column(Integer, primary_key=True)
    type = Column(String(64), nullable=False, index=True)
    first_occurrence = Column(DateTime)
    last_occurrence = Column(DateTime)
    count = Column(Integer, nullable=False)
    errname = Column(String(256), nullable=True)
    component_id = Column(Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), nullable=False, index=True)
    problem_id = Column(Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), nullable=True, index=True)
    component = relationship(OpSysComponent)
    problem = relationship(Problem, backref="reports")

    @property
    def bugs(self):
        my_bugs = []

        for bug in self.rhbz_bugs:
            my_bugs.append(bug.rhbzbug)

        return my_bugs

    @property
    def oops(self):
        return self.get_lob('oops')

    @property
    def sorted_backtraces(self):
        '''
        List of all backtraces assigned to this report
        sorted by quality.
        '''
        return sorted(self.backtraces, key=lambda bt: bt.quality, reverse=True)


class ReportHash(GenericTable):
    __tablename__ = "reporthashes"

    hash = Column(String(64), nullable=False, primary_key=True)
    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False, index=True, primary_key=True)

    report = relationship(Report, backref="hashes")


class ReportBacktrace(GenericTable):
    __tablename__ = "reportbacktraces"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False, index=True)
    report = relationship(Report, backref="backtraces")
    crashfn = Column(String(1024), nullable=True)

    @property
    def crash_function(self):
        if self.crashfn:
            return self.crashfn

        return 'unknown function'

    @property
    def quality(self):
        '''
        Frames with missing information lower the backtrace quality.
        '''
        quality = 0

        for frame in self.frames:
            if not frame.symbolsource.symbol:
                quality -= 1
            else:
                if frame.symbolsource.symbol.name == '??':
                    quality -= 1

            if not frame.symbolsource.source_path:
                quality -= 1

            if not frame.symbolsource.line_number:
                quality -= 1

        return quality

    # just a temporary workaround to make webui work
    # will break as soon as multiple threads are used
    # ToDo: fix it
    @property
    def frames(self):
        return self.threads[0].frames

    #def btp_thread(self):
    #    thread = ""
    #    for frame in self.frames:
    #        if frame.symbolsource.symbol:
    #            name = frame.symbolsource.symbol.name
    #            if frame.symbolsource.symbol.nice_name:
    #                name = frame.symbolsource.symbol.nice_name
    #            thread += "{0} {1}\n".format(name,
    #                frame.symbolsource.symbol.normalized_path)
    #        else:
    #            thread += "?? {0}\n".format(frame.symbolsource.path)
    #
    #    return btparser.Thread(thread, True)

    def normalized(self):
        result = self.btp_thread()

        if self.report.type == "KERNELOOPS":
            result.normalize_kerneloops()
        elif self.report.type == "USERSPACE":
            result.normalize_userspace()

        return result

    def as_named_tuples(self):
        '''
        Return list of named tuples containing name, path,
        source and line fields for each frame of this backtrace.
        '''
        result = []

        for frame in self.frames:
            frame_t = namedtuple('Frame', ['name', 'path', 'source', 'line'])
            if frame.symbolsource.symbol:
                name = frame.symbolsource.symbol.name
                if frame.symbolsource.symbol.nice_name:
                    name = frame.symbolsource.symbol.nice_name

                frame_t.name = name
            else:
                frame_t.name = '??'

            frame_t.path = frame.symbolsource.path
            frame_t.source_path = None
            frame_t.line_num = None
            if (frame.symbolsource.source_path and
                frame.symbolsource.line_number):

                frame_t.source_path = frame.symbolsource.source_path
                frame_t.line_num = frame.symbolsource.line_number

            result.append(frame_t)

        return result


class ReportBtThread(GenericTable):
    __tablename__ = "reportbtthreads"

    id = Column(Integer, primary_key=True)
    backtrace_id = Column(Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), nullable=False, index=True)
    number = Column(Integer, nullable=True)
    crashthread = Column(Boolean, nullable=False)

    backtrace = relationship(ReportBacktrace, backref=backref("threads", order_by="ReportBtThread.number"))


class ReportBtFrame(GenericTable):
    __tablename__ = "reportbtframes"

    thread_id = Column(Integer, ForeignKey("{0}.id".format(ReportBtThread.__tablename__)), primary_key=True)
    order = Column(Integer, nullable=False, primary_key=True)
    symbolsource_id = Column(Integer, ForeignKey("{0}.id".format(SymbolSource.__tablename__)), nullable=False, index=True)
    inlined = Column(Boolean, nullable=False, default=False)
    reliable = Column(Boolean, nullable=False, default=True)
    thread = relationship(ReportBtThread, backref=backref('frames', order_by="ReportBtFrame.order"))
    symbolsource = relationship(SymbolSource, backref=backref('frames'))


class ReportBtHash(GenericTable):
    __tablename__ = "reportbthashes"

    type = Column(Enum("NAMES", "HASHES", name="reportbt_hashtype"), nullable=False, primary_key=True)
    hash = Column(String(64), nullable=False, primary_key=True)
    backtrace_id = Column(Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), nullable=False, index=True, primary_key=True)
    backtrace = relationship(ReportBacktrace,
                             backref="hashes")

    def __str__(self):
        return self.hash


class ReportOpSysRelease(GenericTable):
    __tablename__ = "reportopsysreleases"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="opsysreleases")
    opsysrelease = relationship(OpSysRelease)

    def __str__(self):
        return str(self.opsysrelease)


class ReportArch(GenericTable):
    __tablename__ = "reportarchs"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    arch_id = Column(Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="arches")
    arch = relationship(Arch)

    def __str__(self):
        return str(self.arch)


class ReportPackage(GenericTable):
    __tablename__ = "reportpackages"
    __table_args__ = (UniqueConstraint('report_id', 'type', 'installed_package_id', 'running_package_id'),)

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False)
    type = Column(Enum("CRASHED", "RELATED", "SELINUX_POLICY", name="reportpackage_type"))
    installed_package_id = Column(Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False)
    running_package_id = Column(Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="packages")
    installed_package = relationship(Package, primaryjoin="Package.id==ReportPackage.installed_package_id")
    running_package = relationship(Package, primaryjoin="Package.id==ReportPackage.running_package_id")


class ReportUnknownPackage(GenericTable):
    __tablename__ = "reportunknownpackages"
    __table_args__ = (
        UniqueConstraint('report_id', 'type', 'name', 'installed_epoch',
                         'installed_version', 'installed_release',
                         'installed_arch_id', 'running_epoch',
                         'running_version', 'running_release',
                         'running_arch_id'),)

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
    report = relationship(Report, backref="unknown_packages")
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
    report = relationship(Report, backref="uptimes")


class ReportReason(GenericTable):
    __tablename__ = "reportreasons"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    reason = Column(String(512), nullable=False, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="reasons")

    def __str__(self):
        crash_fn = 'unknown function'
        if self.report.backtraces:
            crash_fn = self.report.backtraces[0].crash_function

        return format_reason(self.report.type, self.reason, crash_fn)


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
    report = relationship(Report, backref="selinux_modes")

    def __str__(self):
        return self.mode.lower().capitalize()


class ReportHistoryMonthly(GenericTable):
    __tablename__ = "reporthistorymonthly"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    month = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="history_monthly")
    opsysrelease = relationship(OpSysRelease)


class ReportHistoryWeekly(GenericTable):
    __tablename__ = "reporthistoryweekly"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    week = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="history_weekly")
    opsysrelease = relationship(OpSysRelease)


class ReportHistoryDaily(GenericTable):
    __tablename__ = "reporthistorydaily"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True)
    day = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False)
    report = relationship(Report, backref="history_daily")
    opsysrelease = relationship(OpSysRelease)


class KernelTaintFlag(GenericTable):
    __tablename__ = "kerneltaintedflags"

    id = Column(Integer, primary_key=True)
    ureport_name = Column(String(32), index=True, unique=True, nullable=False)
    nice_name = Column(String(256), nullable=False)
    character = Column(String(1), index=True, nullable=False)


class ReportBtTaintFlag(GenericTable):
    __tablename__ = "reportbttaintflags"

    backtrace_id = Column(Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), primary_key=True, index=True)
    taintflag_id = Column(Integer, ForeignKey("{0}.id".format(KernelTaintFlag.__tablename__)), primary_key=True, index=True)

    backtrace = relationship(ReportBacktrace, backref="taint_flags")
    taintflag = relationship(KernelTaintFlag, backref="backtraces")


class KernelModule(GenericTable):
    __tablename__ = "kernelmodules"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True, index=True)


class ReportBtKernelModule(GenericTable):
    __tablename__ = "reportbtkernelmodules"

    backtrace_id = Column(Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), primary_key=True, index=True)
    kernelmodule_id = Column(Integer, ForeignKey("{0}.id".format(KernelModule.__tablename__)), primary_key=True, index=True)

    backtrace = relationship(ReportBacktrace, backref="modules")
    kernelmodule = relationship(KernelModule, backref="backtraces")


class ReportRhbz(GenericTable):
    __tablename__ = "reportrhbz"

    report_id = Column(Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True)
    rhbzbug_id = Column(Integer, ForeignKey("{0}.id".format(RhbzBug.__tablename__)), primary_key=True)
    report = relationship(Report, backref="rhbz_bugs")
    rhbzbug = relationship(RhbzBug)
