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

from storage import (Arch,
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
                     ReportOpSysRelease,
                     ReportPackage,
                     ReportReason,
                     Symbol,
                     SymbolSource)

__all__ = ["get_arch_by_name", "get_backtrace_by_hash", "get_component_by_name",
           "get_kernelmodule_by_name", "get_osrelease", "get_package_by_nevra",
           "get_report_by_hash", "get_reportarch", "get_reportexe",
           "get_reportosrelease", "get_reportpackage", "get_reportreason",
           "get_symbol_by_name_path", "get_symbolsource",
           "get_taint_flag_by_name"]

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

def get_kernelmodule_by_name(db, module_name):
    """
    Return pyfaf.storage.KernelModule from module name or None if not found.
    """

    return (db.session.query(KernelModule)
                      .filter(KernelModule.name == module_name)
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

def get_report_by_hash(db, report_hash):
    """
    Return pyfaf.storage.Report object from pyfaf.storage.ReportHash
    or None if not found.
    """

    return (db.session.query(Report)
                      .join(ReportHash)
                      .filter(ReportHash.hash == report_hash)
                      .first())

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
