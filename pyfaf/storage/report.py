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

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("type", Enum("USERSPACE", "KERNEL", "PYTHON", "SELINUX", name="report_type"), nullable=False),
                    Column("first_occurence", DateTime),
                    Column("last_occurence", DateTime),
                    Column("component_id", Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), nullable=False, index=True),
                    Column("problem_id", Integer, ForeignKey("{0}.id".format(Problem.__tablename__)), nullable=True, index=True) ]

    __relationships__ = { "component": relationship(OpSysComponent),
                          "problem": relationship(Problem, backref="reports") }

class ReportBacktrace(GenericTable):
    __tablename__ = "reportbacktraces"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False, index=True) ]

    __relationships__ = { "report": relationship(Report, backref="backtraces") }

class ReportBtFrame(GenericTable):
    __tablename__ = "reportbtframes"

    __columns__ = [ Column("backtrace_id", Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), primary_key=True),
                    Column("order", Integer, nullable=False, primary_key=True),
                    Column("symbolsource_id", Integer, ForeignKey("{0}.id".format(SymbolSource.__tablename__)), nullable=False, index=True) ]

    __relationships__ = { "backtrace": "relationship(ReportBacktrace, backref=backref('frames', order_by=cls.table.c.order))",
                          "symbolsource": "relationship(SymbolSource, backref=backref('frames', order_by=cls.table.c.order))" }

class ReportBtHash(GenericTable):
    __tablename__ = "reportbthashes"

    __columns__ = [ Column("type", Enum("NAMES", "HASHES", name="reportbt_hashtype"), nullable=False, primary_key=True),
                    Column("hash", String(64), nullable=False, primary_key=True),
                    Column("backtrace_id", Integer, ForeignKey("{0}.id".format(ReportBacktrace.__tablename__)), nullable=False, index=True, primary_key=True) ]

    __relationships__ = { "backtrace": relationship(ReportBacktrace) }

class ReportOpSysRelease(GenericTable):
    __tablename__ = "reportopsysreleases"

    __columns__ = [ Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True),
                    Column("opsysrelease_id", Integer, ForeignKey("{0}.id".format(OpSysRelease.__tablename__)), primary_key=True),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "report": relationship(Report),
                          "opsysrelease": relationship(OpSysRelease) }

class ReportArch(GenericTable):
    __tablename__ = "reportarchs"

    __columns__ = [ Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True),
                    Column("arch_id", Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), nullable=False, primary_key=True),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "report": relationship(Report),
                          "arch": relationship(Arch) }

class ReportPackage(GenericTable):
    __tablename__ = "reportpackages"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False),
                    Column("installed_package_id", Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False),
                    Column("running_package_id", Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=True),
                    Column("count", Integer, nullable=False),
                    UniqueConstraint('report_id', 'installed_package_id', 'running_package_id') ]

    __relationships__ = { "report": relationship(Report),
                          "installed_package": "relationship(Package, primaryjoin=Package.id==cls.table.c.installed_package_id)",
                          "running_package": "relationship(Package, primaryjoin=Package.id==cls.table.c.running_package_id)" }

class ReportRelatedPackage(GenericTable):
    __tablename__ = "reportrelatedpackages"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), nullable=False),
                    Column("installed_package_id", Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False),
                    Column("running_package_id", Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=True),
                    Column("count", Integer, nullable=False),
                    UniqueConstraint('report_id', 'installed_package_id', 'running_package_id') ]

    __relationships__ = { "report": relationship(Report),
                          "installed_package": "relationship(Package, primaryjoin=Package.id==cls.table.c.installed_package_id)",
                          "running_package": "relationship(Package, primaryjoin=Package.id==cls.table.c.running_package_id)" }

class ReportExecutable(GenericTable):
    __tablename__ = "reportexecutables"

    __columns__ = [ Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True),
                    Column("path", String(512), nullable=False, primary_key=True),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "report": relationship(Report) }

class ReportHistoryMonthly(GenericTable):
    __tablename__ = "reporthistorymonthly"

    __columns__ = [ Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True),
                    Column("month", Date, primary_key=True),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "report": relationship(Report) }

class ReportHistoryWeekly(GenericTable):
    __tablename__ = "reporthistoryweekly"

    __columns__ = [ Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True),
                    Column("week", Date, primary_key=True),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "report": relationship(Report) }

class ReportHistoryDaily(GenericTable):
    __tablename__ = "reporthistorydaily"

    __columns__ = [ Column("report_id", Integer, ForeignKey("{0}.id".format(Report.__tablename__)), primary_key=True),
                    Column("day", Date, primary_key=True),
                    Column("count", Integer, nullable=False) ]

    __relationships__ = { "report": relationship(Report) }
