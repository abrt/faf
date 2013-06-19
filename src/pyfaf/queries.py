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

from pyfaf.storage import (Arch,
                           Build,
                           KernelModule,
                           KernelTaintFlag,
                           OpSys,
                           OpSysComponent,
                           OpSysRelease,
                           Package,
                           Report,
                           ReportArch,
                           ReportBacktrace,
                           ReportBtHash,
                           ReportExecutable,
                           ReportHash,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           ReportOpSysRelease,
                           ReportPackage,
                           ReportReason,
                           Symbol,
                           SymbolSource)

from sqlalchemy import func, desc

__all__ = ["get_arch_by_name", "get_backtrace_by_hash", "get_component_by_name",
           "get_history_day", "get_history_month", "get_history_sum",
           "get_history_target", "get_history_week", "get_kernelmodule_by_name",
           "get_opsys_by_name", "get_osrelease", "get_package_by_nevra",
           "get_release_ids", "get_releases", "get_report_by_hash",
           "get_report_count_by_component", "get_report_stats_by_component",
           "get_reportarch", "get_reportexe", "get_reportosrelease",
           "get_reportpackage", "get_reportreason", "get_ssource_by_bpo",
           "get_symbol_by_name_path", "get_symbolsource",
           "get_taint_flag_by_ureport_name"]

def get_arch_by_name(db, arch_name):
    """
    Return pyfaf.storage.Arch object from architecture
    name or None if not found.
    """

    return (db.session.query(Arch)
                      .filter(Arch.name == arch_name)
                      .first())

def get_backtrace_by_hash(db, bthash):
    """
    Return pyfaf.storage.ReportBacktrace object from ReportBtHash.hash
    or None if not found.
    """

    return (db.session.query(ReportBacktrace)
                      .join(ReportBtHash)
                      .filter(ReportBtHash.hash == bthash)
                      .first())

def get_component_by_name(db, component_name, opsys_name):
    """
    Return pyfaf.storage.OpSysComponent from component name
    and operating system name or None if not found.
    """

    return (db.session.query(OpSysComponent)
                      .join(OpSys)
                      .filter(OpSysComponent.name == component_name)
                      .filter(OpSys.name == opsys_name)
                      .first())

def get_history_day(db, db_report, db_osrelease, day):
    """
    Return pyfaf.storage.ReportHistoryDaily object for a given
    report, opsys release and day or None if not found.
    """

    return (db.session.query(ReportHistoryDaily)
                      .filter(ReportHistoryDaily.report == db_report)
                      .filter(ReportHistoryDaily.opsysrelease == db_osrelease)
                      .filter(ReportHistoryDaily.day == day)
                      .first())

def get_history_month(db, db_report, db_osrelease, month):
    """
    Return pyfaf.storage.ReportHistoryMonthly object for a given
    report, opsys release and month or None if not found.
    """

    return (db.session.query(ReportHistoryMonthly)
                      .filter(ReportHistoryMonthly.report == db_report)
                      .filter(ReportHistoryMonthly.opsysrelease == db_osrelease)
                      .filter(ReportHistoryMonthly.month == month)
                      .first())

def get_history_sum(db, opsys_name=None, opsys_version=None,
                    history='daily'):
    """
    Return query summing ReportHistory(Daily|Weekly|Monthly)
    records optinaly filtered by `opsys_name` and `opsys_version`.
    """

    opsysrelease_ids = get_release_ids(db, opsys_name, opsys_version)
    hist_table, hist_field = get_history_target(history)
    hist_sum = db.session.query(func.sum(hist_table.count).label('cnt'))
    if opsysrelease_ids:
        hist_sum = hist_sum.filter(
            hist_table.opsysrelease_id.in_(opsysrelease_ids))

    return hist_sum

def get_history_target(target='daily'):
    """
    Return tuple of `ReportHistory(Daily|Weekly|Monthly)` and
    proper date field `ReportHistory(Daily.day|Weekly.week|Monthly.month)`
    according to `target` parameter which should be one of
    `daily|weekly|monthly` or shortened version `d|w|m`.
    """

    if target == 'd' or target == 'daily':
        return (ReportHistoryDaily, ReportHistoryDaily.day)

    if target == 'w' or target == 'weekly':
        return (ReportHistoryWeekly, ReportHistoryWeekly.week)

    return (ReportHistoryMonthly, ReportHistoryMonthly.month)

def get_history_week(db, db_report, db_osrelease, week):
    """
    Return pyfaf.storage.ReportHistoryWeekly object for a given
    report, opsys release and week or None if not found.
    """

    return (db.session.query(ReportHistoryWeekly)
                      .filter(ReportHistoryWeekly.report == db_report)
                      .filter(ReportHistoryWeekly.opsysrelease == db_osrelease)
                      .filter(ReportHistoryWeekly.week == week)
                      .first())

def get_kernelmodule_by_name(db, module_name):
    """
    Return pyfaf.storage.KernelModule from module name or None if not found.
    """

    return (db.session.query(KernelModule)
                      .filter(KernelModule.name == module_name)
                      .first())

def get_opsys_by_name(db, name):
    """
    Return pyfaf.storage.OpSys from operating system
    name or None if not found.
    """

    return (db.session.query(OpSys)
                      .filter(OpSys.name == name)
                      .first())

def get_osrelease(db, name, version):
    """
    Return pyfaf.storage.OpSysRelease from operating system
    name and version or None if not found.
    """

    return (db.session.query(OpSysRelease)
                      .join(OpSys)
                      .filter(OpSys.name == name)
                      .filter(OpSysRelease.version == version)
                      .first())

def get_package_by_nevra(db, name, epoch, version, release, arch):
    """
    Return pyfaf.storage.Package object from NEVRA or None if not found.
    """

    return (db.session.query(Package)
                      .join(Build)
                      .join(Arch)
                      .filter(Package.name == name)
                      .filter(Build.epoch == epoch)
                      .filter(Build.version == version)
                      .filter(Build.release == release)
                      .filter(Arch.name == arch)
                      .first())

def get_release_ids(db, opsys_name=None, opsys_version=None):
    """
    Return list of `OpSysRelease` ids optionaly filtered
    by `opsys_name` and `opsys_version`.
    """

    return [opsysrelease.id for opsysrelease in
            get_releases(db, opsys_name, opsys_version).all()]

def get_releases(db, opsys_name=None, opsys_version=None):
    """
    Return query of `OpSysRelease` records optionaly filtered
    by `opsys_name` and `opsys_version`.
    """

    opsysquery = (
        db.session.query(OpSysRelease)
        .join(OpSys))

    if opsys_name:
        opsysquery = opsysquery.filter(OpSys.name == opsys_name)

    if opsys_version:
        opsysquery = opsysquery.filter(OpSysRelease.version == opsys_version)

    return opsysquery

def get_report_by_hash(db, report_hash):
    """
    Return pyfaf.storage.Report object from pyfaf.storage.ReportHash
    or None if not found.
    """

    return (db.session.query(Report)
                      .join(ReportHash)
                      .filter(ReportHash.hash == report_hash)
                      .first())

def get_report_count_by_component(db, opsys_name=None, opsys_version=None,
                                  history='daily'):
    """
    Return query for `OpSysComponent` and number of reports this
    component received.

    It's possible to filter the results by `opsys_name` and
    `opsys_version`.
    """

    opsysrelease_ids = get_release_ids(db, opsys_name, opsys_version)
    hist_table, hist_field = get_history_target(history)

    comps = (
        db.session.query(OpSysComponent,
                         func.sum(hist_table.count).label('cnt'))
        .join(Report)
        .join(hist_table)
        .group_by(OpSysComponent)
        .order_by(desc('cnt')))

    if opsysrelease_ids:
        comps = comps.filter(hist_table.opsysrelease_id.in_(opsysrelease_ids))

    return comps

def get_report_stats_by_component(db, component, history='daily'):
    """
    Return query with reports for `component` along with
    summed counts from `history` table (one of daily/weekly/monthly).
    """

    hist_table, hist_field = get_history_target(history)

    return (db.session.query(Report,
                             func.sum(hist_table.count).label('cnt'))
            .join(hist_table)
            .join(OpSysComponent)
            .filter(OpSysComponent.id == component.id)
            .group_by(Report)
            .order_by(desc('cnt')))

def get_reportarch(db, report, arch):
    """
    Return pyfaf.storage.ReportArch object from pyfaf.storage.Report
    and pyfaf.storage.Arch or None if not found.
    """

    return (db.session.query(ReportArch)
                      .filter(ReportArch.report == report)
                      .filter(ReportArch.arch == arch)
                      .first())

def get_reportexe(db, report, executable):
    """
    Return pyfaf.storage.ReportExecutable object from pyfaf.storage.Report
    and the absolute path of executable or None if not found.
    """

    return (db.session.query(ReportExecutable)
                      .filter(ReportExecutable.report == report)
                      .filter(ReportExecutable.path == executable)
                      .first())

def get_reportosrelease(db, report, osrelease):
    """
    Return pyfaf.storage.ReportOpSysRelease object from pyfaf.storage.Report
    and pyfaf.storage.OpSysRelease or None if not found.
    """

    return (db.session.query(ReportOpSysRelease)
                      .filter(ReportOpSysRelease.report == report)
                      .filter(ReportOpSysRelease.opsysrelease == osrelease)
                      .first())

def get_reportpackage(db, report, package):
    """
    Return pyfaf.storage.ReportPackage object from pyfaf.storage.Report
    and pyfaf.storage.Package or None if not found.
    """

    return (db.session.query(ReportPackage)
                      .filter(ReportPackage.report == report)
                      .filter(ReportPackage.installed_package == package)
                      .first())

def get_reportreason(db, report, reason):
    """
    Return pyfaf.storage.ReportReason object from pyfaf.storage.Report
    and the textual reason or None if not found.
    """

    return (db.session.query(ReportReason)
                      .filter(ReportReason.report == report)
                      .filter(ReportReason.reason == reason)
                      .first())

def get_ssource_by_bpo(db, build_id, path, offset):
    """
    Return pyfaf.storage.SymbolSource object from build id,
    path and offset or None if not found.
    """

    return (db.session.query(SymbolSource)
                      .filter(SymbolSource.build_id == build_id)
                      .filter(SymbolSource.path == path)
                      .filter(SymbolSource.offset == offset)
                      .first())

def get_symbol_by_name_path(db, name, path):
    """
    Return pyfaf.storage.Symbol object from symbol name
    and normalized path or None if not found.
    """

    return (db.session.query(Symbol)
                      .filter(Symbol.name == name)
                      .filter(Symbol.normalized_path == path)
                      .first())

def get_symbolsource(db, symbol, filename, offset):
    """
    Return pyfaf.storage.SymbolSource object from pyfaf.storage.Symbol,
    file name and offset or None if not found.
    """

    return (db.session.query(SymbolSource)
                      .filter(SymbolSource.symbol == symbol)
                      .filter(SymbolSource.path == filename)
                      .filter(SymbolSource.offset == offset)
                      .first())

def get_taint_flag_by_ureport_name(db, ureport_name):
    """
    Return pyfaf.storage.KernelTaintFlag from flag name or None if not found.
    """

    return (db.session.query(KernelTaintFlag)
                      .filter(KernelTaintFlag.ureport_name == ureport_name)
                      .first())
