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

from pyfaf import package
from pyfaf import support
from pyfaf.common import get_libname
from pyfaf.storage.opsys import (Package, PackageDependency)
from pyfaf.storage.symbol import (Symbol, SymbolSource)

def retrace_symbol(binary_path, binary_offset, binary_dir, debuginfo_dir):
    '''
    Handle actual retracing. Call eu-unstrip and eu-addr2line
    on unpacked rpms.

    Returns tuple containing function, source code file and line or
    None if retracing failed.
    '''

    cmd = ["eu-unstrip", "-n", "-e",
        os.path.join(binary_dir, binary_path[1:])]

    logging.debug("Calling {0}".format(' '.join(cmd)))

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

    logging.debug("Calling {0}".format(' '.join(cmd)))

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

def is_duplicate_source(session, source):
    '''
    If current source object is already present in database,
    remove this object and update ReportBtFrame pointing to it
    to the duplicate one.

    This can happen during rewriting of /usr moved SymbolSources.

    Returns True if duplicate was found and handled.
    '''
    dup = (session.query(SymbolSource).filter(
        (SymbolSource.build_id == source.build_id) &
        (SymbolSource.path == source.path) &
        (SymbolSource.offset == source.offset)).first())

    if dup is not source:
        logging.debug("Duplicate symbol found, merging")
        frame = source.frames[0]
        frame.symbolsource = dup
        session.delete(source)
        return True

    return False

def retrace_symbol_wrapper(session, source, binary_dir, debuginfo_dir):
    '''
    Handle database references. Delete old symbol with '??' if
    reference count is 1 and add new symbol if there is no such
    symbol already.
    '''

    result = retrace_symbol(source.path, source.offset, binary_dir,
        debuginfo_dir)

    logging.info('Result: {0}'.format(result))
    if result is not None:
        (symbol_name, source.source_path, source.line_number) = result

        # Handle eu-addr2line not returing correct function name
        if symbol_name == '??':
            symbol_name = source.symbol.name

            logging.warning('eu-addr2line failed to return function'
                ' name, using reported name: "{0}"'.format(symbol_name))

        # Search for already existing identical symbol.
        normalized_path = get_libname(source.path)
        symbol = (session.query(Symbol).filter(
            (Symbol.name == symbol_name) &
            (Symbol.normalized_path == normalized_path))).first()

        possible_duplicates = []

        if symbol:
            # Some symbol has been found.
            logging.debug('Already got this symbol')
            source.symbol = symbol

            for frame in source.frames:
                possible_duplicates.append(frame.backtrace)
        else:
            # Create new symbol.
            symbol = Symbol()
            symbol.name = symbol_name
            symbol.normalized_path = normalized_path
            session.add(symbol)
            source.symbol = symbol

        if not is_duplicate_source(session, source):
            session.add(source)

        session.flush()

        # delete unreferenced symbols
        session.query(Symbol).filter(
            (Symbol.name == '??') &
            (Symbol.sources == None)).delete(False)

        check_duplicate_backtraces(session, possible_duplicates)

def retrace_symbols(session):
    '''
    Find all Symbol Sources of Symbols that require retracing.
    Symbol Sources are grouped by build_id to lower the need of
    installing the same RPM multiple times.
    '''

    symbol_sources = (session.query(SymbolSource)
        .filter(SymbolSource.source_path == None)
        .order_by(SymbolSource.build_id, SymbolSource.path)).all()

    logging.info('Retracing {0} symbols'.format(len(symbol_sources)))

    while symbol_sources:
        source = symbol_sources.pop()
        logging.info('Retracing {0} with offset {1}'.format(source.path,
            source.offset))

        # Find debuginfo and then binary package providing the build id.
        # FEDORA/RHEL SPECIFIC
        debuginfo_path = "/usr/lib/debug/.build-id/{0}/{1}.debug".format(
            source.build_id[:2], source.build_id[2:])

        logging.debug('Looking for: {0}'.format(debuginfo_path))

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

            def find_binary_package(path):
                logging.debug('Looking for: {0}'.format(path))
                return (session.query(Package)
                    .join(PackageDependency)
                    .filter(
                        (Package.build_id == debuginfo_package.build_id) &
                        (Package.arch_id == debuginfo_package.arch_id) &
                        (PackageDependency.name == path) &
                        (PackageDependency.type == "PROVIDES")
                    )).first()

            binary_package = find_binary_package(source.path)

            if binary_package is None:
                logging.info("Binary package not found, trying /usr fix")

                # Try adding/stripping /usr
                orig_path = source.path
                if '/usr' in source.path:
                    logging.debug('Stripping /usr')
                    source.path = source.path.replace('/usr', '')
                    binary_package = find_binary_package(source.path)
                else:
                    logging.debug('Adding /usr')
                    source.path = '/usr' + source.path
                    binary_package = find_binary_package(source.path)

                if binary_package is None:
                    # Revert to original path
                    source.path = orig_path
                    logging.warning("Matching binary package not found")
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

            while (symbol_sources and
                symbol_sources[0].build_id == source.build_id and
                symbol_sources[0].path == source.path):

                source = symbol_sources.pop()
                retrace_symbol_wrapper(session, source, binary_dir,
                    debuginfo_dir)

            shutil.rmtree(binary_dir)
            shutil.rmtree(debuginfo_dir)

def check_duplicate_backtraces(session, bts):
    '''
    Check backtraces where the symbol source is used, if
    they contain duplicate backtraces.

    Merge duplicate backtraces.
    '''

    # Disabled due to trac#696
    return

    for i in range(0, len(bts)):
        try:
            for j in range(i + 1, len(bts)):
                bt1 = bts[i]
                bt2 = bts[j]

                if len(bt1.frames) != len(bt2.frames):
                    raise support.GetOutOfLoop

                for f in range(0, len(bt1.frames)):
                    if (bt1.frames[f].symbolsource.symbol_id !=
                        bt2.frames[f].symbolsource.symbol_id):
                        raise support.GetOutOfLoop

                # The two backtraces are identical.
                # Remove one of them.
                logging.info('Found duplicate backtrace, deleting')

                # Delete ReportBtHash
                session.delete(bt1.hash)

                # Delete ReportBtFrame(s)
                for frame in bt1.frames:
                    session.delete(frame)

                # Update report to use the second backtrace
                report = bt1.report
                report.backtraces.append(bt2)

                # Delete ReportBacktrace
                session.delete(bt1)

                session.flush()

        except support.GetOutOfLoop:
            pass
