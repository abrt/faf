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

from . import Column
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import Package
from . import PackageProvides
from . import UniqueConstraint
from . import relationship
from .. import package
from .. import support
import shutil
import subprocess
import os
import re

class Symbol(GenericTable):
    __tablename__ = "symbols"
    __table_args__ = ( UniqueConstraint('name', 'normalized_path'), )

    id = Column(Integer, primary_key=True)
    name = Column(String(2048), nullable=False)
    normalized_path = Column(String(512), nullable=False)

class SymbolSource(GenericTable):
    __tablename__ = "symbolsources"
    __table_args__ = ( UniqueConstraint('build_id', 'path', 'offset'), )

    id = Column(Integer, primary_key=True)
    symbol_id = Column(Integer, ForeignKey("{0}.id".format(Symbol.__tablename__)), nullable=True, index=True)
    build_id = Column(String(64), nullable=False)
    path = Column(String(512), nullable=False)
    offset = Column(Integer, nullable=False)
    hash = Column(String(64), nullable=True)
    source_path = Column(String(512), nullable=True)
    line_number = Column(Integer, nullable=True)
    symbol = relationship(Symbol, backref="sources")

def retrace_symbol(binary_path, binary_offset, binary_dir, debuginfo_dir):
    """
    Returns True if successful, False otherwise.
    """
    unstrip_proc = subprocess.Popen(["eu-unstrip", "-n", "-e", os.path.join(binary_dir, binary_path)],
                                    stdout=subprocess.PIPE)
    stdout, _ = unstrip_proc.communicate()
    if unstrip_proc.returncode != 0:
        return None

    offset_match = re.match("((0x)?[0-9a-f]+)", stdout)
    offset = int(offset_match.group(0))

    addr2line_proc = subprocess.Popen(["eu-addr2line",
                                       "--executable={0}".format(os.path.join(binary_dir, binary_path)),
                                       "--debuginfo-path={0}".format(os.path.join(debuginfo_dir, "/usr/lib/debug")),
                                       "--functions",
                                       str(offset + binary_offset)],
                                      stdout=subprocess.PIPE)
    stdout, _ = addr2line_proc.communicate()
    if addr2line_proc.returncode != 0:
        return None
    #pylint: disable=E1103
    # Instance of 'list' has no 'splitlines' member (but some types
    # could not be inferred)
    lines = stdout.splitlines()
    source = lines[1].split(":")

    function_name = lines[0]
    source_file = source[0]
    line_number = source[1]
    return (function_name, source_file, line_number)

def retrace_symbol_wrapper(session, source, binary_dir, debuginfo_dir):
    result = retrace_symbol(source.path, source.offset, binary_dir, debuginfo_dir)
    if result is not None:
        (symbol_name, source.source_path, source.line_number) = result

        # Search for already existing identical symbol.
        normalized_path = source.path # TODO: normalize
        symbol = session.query(Symbol).filter((Symbol.name == symbol_name) & (Symbol.normalized_path == normalized_path)).one()
        if any(symbol):
            # Some symbol has been found.
            source.symbol_id = symbol[0].id
            session.commit()

            # Check backtraces where the symbol source is used, if
            # they contain duplicate backtraces.
            reports = set()
            for frame in source.frames:
                reports.add(frame.backtrace.report)
            for report in reports:
                for b1 in range(0, len(report.backtraces)):
                    try:
                        for b2 in range(b1 + 1, len(report.backtraces)):
                            if len(b1.frames) != len(b2.frames):
                                raise support.GetOutOfLoop
                            for f in range(0, len(b1.frames)):
                                if b1.frames[f].symbol_source.symbol_id != b2.frames[f].symbol_source.symbol_id:
                                    raise support.GetOutOfLoop

                        # The two backtraces are identical.  Remove one of them.
                        # TODO
                    except support.GetOutOfLoop:
                        pass
        else:
            # Create new symbol.
            symbol = Symbol()
            symbol.name = symbol_name
            symbol.normalized_path = normalized_path
            session.add(symbol)
            source.symbol = symbol
            session.commit()

def retrace_symbols(session):
    # Find all Symbol Sources of Symbols that require retracing.
    # Symbol Sources are grouped by build_id to lower the need of
    # installing the same RPM multiple times.
    symbol_sources = session.query(SymbolSource).\
        filter(SymbolSource.symbol_id == None).\
        group_by(SymbolSource.build_id,SymbolSource.path)

    while any(symbol_sources):
        source = symbol_sources.pop()

        # Find debuginfo and then binary package providing the build id.
        # FEDORA/RHEL SPECIFIC
        debuginfo_path = "/usr/lib/debug/.build-id/{0}/{1}.debug".format(source.build_id[:2], source.build_id[2:])

        #pylint: disable=E1103
        # Class 'Package' has no 'provides' member (but some types
        # could not be inferred)
        debuginfo_packages = session.query(Package).join(Package.provides).filter(PackageProvides.provides == debuginfo_path)
        for debuginfo_package in debuginfo_packages:
            # Check whether there is a binary package corresponding to
            # the debuginfo package that provides the required binary.
            binary_package = session.query(Package).filter(Package.build_id == debuginfo_package.build_id & \
                                                    Package.arch_id == debuginfo_package.arch_id & \
                                                    PackageProvides.provides == source.path).first()
            if binary_package is None:
                continue

            # We found a valid pair of binary and debuginfo packages.
            # Unpack them to temporary directories.
            binary_dir = package.unpack_rpm_to_tmp(binary_package._get_lobpath("package"),
                                                   prefix="faf-symbol-retrace")
            debuginfo_dir = package.unpack_rpm_to_tmp(debuginfo_package._get_lobpath("package"),
                                                      prefix="faf-symbol-retrace")

            retrace_symbol_wrapper(session, source, binary_dir, debuginfo_dir)

            while any(symbol_sources) and symbol_sources[0].build_id == source.build_id and symbol_sources[0].path == source.path:
                source = symbol_sources.pop()
                retrace_symbol_wrapper(session, source, binary_dir, debuginfo_dir)

            shutil.rmtree(binary_dir)
            shutil.rmtree(debuginfo_dir)
