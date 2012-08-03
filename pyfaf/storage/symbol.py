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

import os
import re
import shutil
import logging
import subprocess

from . import Column
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import Package
from . import PackageDependency
from . import UniqueConstraint
from . import relationship
from pyfaf import package
from pyfaf import support
from pyfaf.common import get_libname

class Symbol(GenericTable):
    __tablename__ = "symbols"
    __table_args__ = ( UniqueConstraint('name', 'normalized_path'), )

    id = Column(Integer, primary_key=True)
    name = Column(String(1024), nullable=False)
    normalized_path = Column(String(512), nullable=False)

class SymbolSource(GenericTable):
    __tablename__ = "symbolsources"
    __table_args__ = ( UniqueConstraint('build_id', 'path', 'offset'), )

    id = Column(Integer, primary_key=True)
    symbol_id = Column(Integer, ForeignKey("{0}.id".format(
        Symbol.__tablename__)), nullable=True, index=True)
    build_id = Column(String(64), nullable=False)
    path = Column(String(512), nullable=False)
    offset = Column(Integer, nullable=False)
    hash = Column(String(1024), nullable=True)
    source_path = Column(String(512), nullable=True)
    line_number = Column(Integer, nullable=True)
    symbol = relationship(Symbol, backref="sources")

def retrace_symbol(binary_path, binary_offset, binary_dir, debuginfo_dir):
    '''
    Handle actual retracing. Call eu-unstrip and eu-addr2line
    on unpacked rpms.

    Returns tuple containing function, source code file and line or
    None if retracing failed.
    '''

    cmd = ["eu-unstrip", "-n", "-e",
        os.path.join(binary_dir, binary_path[1:])]

    unstrip_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = unstrip_proc.communicate()
    if unstrip_proc.returncode != 0:
        logging.error('eu-unstrip failed.'
            ' command {0} \n stdout: {1} \n stderr: {2} \n'.format(
            ' '.join(cmd), stdout, stderr))
        return None

    offset_match = re.match("((0x)?[0-9a-f]+)", stdout)
    offset = int(offset_match.group(0), 16)

    cmd = ["eu-addr2line",
           "--executable={0}".format(
              os.path.join(binary_dir, binary_path[1:])),
           "--debuginfo-path={0}".format(
              os.path.join(debuginfo_dir, "usr/lib/debug")),
           "--functions",
              str(offset + binary_offset)]

    addr2line_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    stdout, stderr = addr2line_proc.communicate()
    if addr2line_proc.returncode != 0:
        logging.error('eu-addr2line failed.'
            ' command {0} \n stdout: {1} \n stderr: {2} \n'.format(
            ' '.join(cmd), stdout, stderr))
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
    '''
    Handle database references. Delete old symbol with '??' if
    reference count is 1 and add new symbol if there is no such
    symbol already.
    '''

    result = retrace_symbol(source.path, source.offset, binary_dir,
        debuginfo_dir)

    logging.debug('Result: {0}'.format(result))
    if result is not None:
        (symbol_name, source.source_path, source.line_number) = result

        # Delete old symbol with '??' name
        references = (session.query(SymbolSource).filter(
            SymbolSource.symbol == source.symbol)).all()

        if len(references) == 1:
            # is this the last reference?
            session.delete(source.symbol)

        # Search for already existing identical symbol.
        normalized_path = get_libname(source.path)
        symbol = (session.query(Symbol).filter(
            (Symbol.name == symbol_name) &
            (Symbol.normalized_path == normalized_path))).first()

        if symbol:
            # Some symbol has been found.
            logging.debug('Already got this symbol')
            source.symbol = symbol

            check_duplicate_backtraces(session, source)
        else:
            # Create new symbol.
            symbol = Symbol()
            symbol.name = symbol_name
            symbol.normalized_path = normalized_path
            session.add(symbol)
            source.symbol = symbol

        session.add(source)
        session.flush()

def retrace_symbols(session):
    '''
    Find all Symbol Sources of Symbols that require retracing.
    Symbol Sources are grouped by build_id to lower the need of
    installing the same RPM multiple times.
    '''

    symbol_sources = (session.query(SymbolSource)
        .join(Symbol)
        .filter(Symbol.name == '??')
        .order_by(SymbolSource.build_id, SymbolSource.path)).all()

    logging.debug('Retracing {0} symbols'.format(len(symbol_sources)))

    while any(symbol_sources):
        source = symbol_sources.pop()
        logging.debug('Retracing {0} with offset {1}'.format(source.path,
            source.offset))

        # Find debuginfo and then binary package providing the build id.
        # FEDORA/RHEL SPECIFIC
        debuginfo_path = "/usr/lib/debug/.build-id/{0}/{1}.debug".format(
            source.build_id[:2], source.build_id[2:])

        #pylint: disable=E1103
        # Class 'Package' has no 'dependencies' member (but some types
        # could not be inferred)
        debuginfo_packages = (session.query(Package)
            .join(PackageDependency)
            .filter(
                (PackageDependency.name == debuginfo_path) &
                (PackageDependency.type == "PROVIDES")
            )).all()

        logging.debug("Found {0} debuginfo packages".format(
            len(debuginfo_packages)))

        for debuginfo_package in debuginfo_packages:
            # Check whether there is a binary package corresponding to
            # the debuginfo package that provides the required binary.
            binary_package = (session.query(Package)
                .join(PackageDependency)
                .filter(
                    (Package.build_id == debuginfo_package.build_id) &
                    (Package.arch_id == debuginfo_package.arch_id) &
                    (PackageDependency.name == source.path) &
                    (PackageDependency.type == "PROVIDES")
                )).first()

            if binary_package is None:
                logging.debug("Matching binary package not found")
                continue

            # We found a valid pair of binary and debuginfo packages.
            # Unpack them to temporary directories.
            binary_dir = package.unpack_rpm_to_tmp(
                binary_package.get_lob_path("package"),
                prefix="faf-symbol-retrace")
            debuginfo_dir = package.unpack_rpm_to_tmp(
                debuginfo_package.get_lob_path("package"),
                prefix="faf-symbol-retrace")

            retrace_symbol_wrapper(session, source, binary_dir, debuginfo_dir)

            while (any(symbol_sources) and
                symbol_sources[0].build_id == source.build_id and
                symbol_sources[0].path == source.path):

                source = symbol_sources.pop()
                retrace_symbol_wrapper(session, source, binary_dir,
                    debuginfo_dir)

            shutil.rmtree(binary_dir)
            shutil.rmtree(debuginfo_dir)

def check_duplicate_backtraces(session, source):
    '''
    Check backtraces where the symbol source is used, if
    they contain duplicate backtraces.

    Merge duplicate backtraces.
    '''
    reports = set()
    for frame in source.frames:
        reports.add(frame.backtrace.report)

    for report in reports:
        for i in range(0, len(report.backtraces)):
            try:
                for j in range(i + 1, len(report.backtraces)):
                    bt1 = report.backtraces[i]
                    bt2 = report.backtraces[j]

                    if len(bt1.frames) != len(bt2.frames):
                        raise support.GetOutOfLoop

                    for f in range(0, len(bt1.frames)):
                        if (bt1.frames[f].symbolsource.symbol_id !=
                            bt2.frames[f].symbolsource.symbol_id):
                            raise support.GetOutOfLoop

                # The two backtraces are identical.
                # Remove one of them.
                logging.info('Found duplicate backtrace, deleting')
                session.delete(report.backtraces[i])

            except support.GetOutOfLoop:
                pass
