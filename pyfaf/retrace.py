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
import threading

from pyfaf import package
from pyfaf import support
from pyfaf.common import get_libname, cpp_demangle
from pyfaf.storage.opsys import (Package, PackageDependency)
from pyfaf.storage.symbol import (Symbol, SymbolSource)
from pyfaf.storage import ReportBtFrame, Arch, Build
from subprocess import call, Popen, PIPE, STDOUT

INLINED_PARSER = re.compile("^(.+) inlined at ([^:]+):([0-9]+) in (.*)$")

def bt_shift_frames(session, backtrace, first):
    shift = [f for f in backtrace.frames if f.order >= first]
    logging.debug("Shifting {0} frames for backtrace #{1}" \
                  .format(len(shift), backtrace.id))
    shift_sorted = sorted(shift, key=lambda x: x.order, reverse=True)
    for frame in shift_sorted:
        frame.order += 1
        session.flush()

def parse_kernel_build_id(build_id, archs=None):
    if archs is None:
        archs = set(["i386", "i486", "i586", "i686", "x86_64"])

    arch = None
    flavour = None

    head, tail = build_id.rsplit(".", 1)
    if tail in archs:
        arch = tail
    else:
        flavour = tail
        head, tail = head.rsplit(".", 1)
        if not tail in archs:
            raise Exception, "Unable to determine architecture"

        arch = tail

    version, release = head.rsplit("-", 1)

    return version, release, arch, flavour

def parse_inlined(raw):
    logging.debug("Separating inlined function: {0}".format(raw))
    match = INLINED_PARSER.match(raw)
    if not match:
        raise Exception, "Unable to parse inlined function"

    return match.group(1), (match.group(4), match.group(2), match.group(3))

def retrace_symbol(binary_path, binary_offset, binary_dir, debuginfo_dir, absolute_offset=False):
    '''
    Handle actual retracing. Call eu-unstrip and eu-addr2line
    on unpacked rpms.

    Returns list of tuples containing function, source code file and line or
    None if retracing failed.
    '''

    offset = 0
    if not absolute_offset:
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
    inlined = None

    if " inlined at " in function_name:
        function_name, inlined = parse_inlined(function_name)

    result = [(function_name, source_file, line_number)]
    if inlined:
        result.insert(0, inlined)

    return result

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

    if dup and dup is not source:
        logging.debug("Duplicate symbol found, merging")
        for frame in source.frames[:]:
            frame.symbolsource = dup
        session.expunge(source)
        session.flush()
        # delete original symbolsource
        session.query(SymbolSource).filter(
            SymbolSource.id == source.id).delete()
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
        normalized_path = get_libname(source.path)

        if len(result) > 1:
            # <ugly>We have no offset for inlined functions,
            # so use -1 * line_number</ugly>
            inlined_name, inlined_source_path, inlined_line_number = result[1]
            inlined_line_number = int(inlined_line_number)

            logging.debug("Handling inlined function '{0}'".format(inlined_name))
            inlined_source = session.query(SymbolSource) \
                             .filter((SymbolSource.build_id == source.build_id) &
                                     (SymbolSource.path == source.path) &
                                     (SymbolSource.offset == -inlined_line_number)) \
                             .first()

            if not inlined_source:
                logging.debug("Creating new SymbolSource")
                inlined_source = SymbolSource()
                inlined_source.build_id = source.build_id
                inlined_source.path = source.path
                inlined_source.offset = -inlined_line_number
                inlined_source.line_number = inlined_line_number
                inlined_source.source_path = inlined_source_path

                inlined_symbol = session.query(Symbol) \
                                 .filter((Symbol.name == inlined_name) &
                                         (Symbol.normalized_path == normalized_path)) \
                                 .first()

                if not inlined_symbol:
                    logging.debug("Creating new Symbol")
                    inlined_symbol = Symbol()
                    inlined_symbol.name = inlined_name

                    demangled = cpp_demangle(inlined_symbol.name)
                    if demangled != inlined_symbol.name:
                        inlined_symbol.nice_name = demangled

                    inlined_symbol.normalized_path = normalized_path
                    session.add(inlined_symbol)
                    session.flush()

                inlined_source.symbol_id = inlined_symbol.id
                session.add(inlined_source)
                session.flush()
            else:
                # although this is strange, it happens
                # it is probably a bug somewhere
                # ToDo: fix it
                if inlined_source.line_number != inlined_line_number:
                    logging.warn("Different line number for same"
                                 " build_id+soname+offset")
                    inlined_line_number = inlined_source.line_number

                if inlined_source.source_path != inlined_source_path:
                    logging.warn("Different source_path for same"
                                 " build_id+soname+offset")
                    inlined_source_path = inlined_source.source_path

            affected = session.query(ReportBtFrame) \
                       .filter(ReportBtFrame.symbolsource_id == source.id).all()

            for frame in affected:
                order = frame.order
                prevframe = frame.backtrace.frames[order - 1]
                if prevframe.inlined and \
                   prevframe.symbolsource_id == inlined_source.id:
                    logging.debug("Already separated, skipping")
                    continue

                bt_shift_frames(session, frame.backtrace, order)

                logging.debug("Creating new ReportBtFrame")
                newframe = ReportBtFrame()
                newframe.backtrace_id = frame.backtrace_id
                newframe.order = order
                newframe.symbolsource_id = inlined_source.id
                newframe.inlined = True
                session.add(newframe)
                session.flush()

        (symbol_name, source.source_path, source.line_number) = result[0]

        # Handle eu-addr2line not returing correct function name
        if symbol_name == '??':
            symbol_name = source.symbol.name

            logging.warning('eu-addr2line failed to return function'
                ' name, using reported name: "{0}"'.format(symbol_name))

        # Search for already existing identical symbol.
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

            demangled = cpp_demangle(symbol.name)
            if demangled != symbol.name:
                symbol.nice_name = demangled

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

    total = len(symbol_sources)
    retraced = 0
    logging.info('Retracing {0} symbols'.format(total))

    while symbol_sources:
        retraced += 1
        source = symbol_sources.pop()
        logging.info('[{0}/{1}] Retracing {2} with offset {3}'.format(
            retraced, total, source.path, source.offset))

        if not source.frames:
            logging.debug('No frames assigned with this symbol, skipping')
            continue

        if source.frames[0].backtrace.report.type != 'USERSPACE':
            logging.debug('Skipping non-USERSPACE symbol')
            continue

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

        packages_found = False

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

            orig_path = source.path
            if ('/../' in source.path) or ('/./' in source.path):
                logging.debug("Source path is not normalized, normalizing")
                source.path = os.path.abspath(source.path)

            binary_package = find_binary_package(source.path)

            if binary_package is None:
                logging.info("Binary package not found, trying /usr fix")

                # Try adding/stripping /usr
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
                    session.expunge(source)
                    logging.warning("Matching binary package not found")
                    continue

            # We found a valid pair of binary and debuginfo packages.
            # Unpack them to temporary directories.
            # Search for possible conflicts with normalized path
            conflict = session.query(SymbolSource) \
                       .filter((SymbolSource.path == source.path) &
                               (SymbolSource.offset == source.offset) &
                               (SymbolSource.build_id == source.build_id)) \
                       .first()

            if conflict and  conflict.id != source.id:
                logging.debug("Merging SymbolSource {0}".format(conflict.id))
                session.expunge(source)

                # replace SymbolSource by the existing one
                for frame in source.frames:
                    frame.symbolsource_id = conflict.id
                session.flush()

                # delete the unnecessary SymbolSource
                session.query(SymbolSource).filter(SymbolSource.id == source.id).delete()
                session.flush()

                source = conflict

            try:
                binary_dir = package.unpack_rpm_to_tmp(
                    binary_package.get_lob_path("package"),
                    prefix="faf-symbol-retrace")
            except Exception, e:
                logging.error("Unable to extract binary package RPM: {0},"
                    " path: {1}, reason: {2}".format(binary_package.nvra(),
                    binary_package.get_lob_path("package"), e))
                continue

            try:
                debuginfo_dir = package.unpack_rpm_to_tmp(
                    debuginfo_package.get_lob_path("package"),
                    prefix="faf-symbol-retrace")
            except:
                logging.error("Unable to extract debuginfo RPM: {0},"
                    " path: {1}, reason: {2}".format(debuginfo_package.nvra(),
                    debuginfo_package.get_lob_path("package"), e))
                continue

            logging.debug("Binary package RPM: {0},"
                " path: {1}".format(binary_package.nvra(),
                binary_package.get_lob_path("package")))
            logging.debug("Debuginfo package RPM: {0},"
                " path: {1}".format(debuginfo_package.nvra(),
                debuginfo_package.get_lob_path("package")))

            # Found matching pair, stop trying.
            packages_found = True
            break

        if not packages_found:
            continue

        retrace_symbol_wrapper(session, source, binary_dir, debuginfo_dir)

        while (symbol_sources and
            symbol_sources[-1].build_id == source.build_id and
            symbol_sources[-1].path == source.path):

            logging.debug("Reusing extracted directories")
            retraced += 1
            source = symbol_sources.pop()
            logging.info('[{0}/{1}] Retracing {2} with offset {3}'.format(
                retraced, total, source.path, source.offset))

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

### New algorithm ###

"""
Task format:
{
  "debuginfo": {
                 "package": <pyfaf.storage.Package object>,
                 "nvra": "glibc-debuginfo-2.12-1.89.el6.x86_64",
                 "rpm_path": "/var/spool/faf/lob/Package/package/00/00/1",
               },
  "source":    {
                 "package": <pyfaf.storage.Package object>,
                 "nvra": "glibc-2.12-1.89.el6.src",
                 "rpm_path": "/var/spool/faf/lob/Package/package/00/00/0",
               },
  "packages":  [
                 {
                   "package": <pyfaf.storage.Package object>,
                   "nvra": "glibc-2.12-1.89.el6.x86_64",
                   "rpm_path": "/var/spool/faf/lob/Package/package/00/00/2",
                   "symbols": set([<pyfaf.storage.SymbolSource object>,
                                   <pyfaf.storage.SymbolSource object>,
                                   <pyfaf.storage.SymbolSource object>]),
                 },
                 {
                   "package": <pyfaf.storage.Package object>,
                   "nvra": "glibc-common-2.12-1.89.el6.x86_64",
                   "rpm_path": "/var/spool/faf/lob/Package/package/00/00/3",
                   "symbols": set([<pyfaf.storage.SymbolSource object>,
                                   <pyfaf.storage.SymbolSource object>,
                                   <pyfaf.storage.SymbolSource object>]),
                 },
               ],
}

pyfaf.storage objects are not thread-safe,
do not access them in FafAsyncRpmUnpacker!!!

FafAsyncRpmUnpacker adds "unpacked_path" field to each
package (including source and debuginfo)
"""

def get_function_offset_map(kernel_debuginfo_dir):
    result = {}

    files = walk(kernel_debuginfo_dir)
    for filename in files:
        if filename.endswith("/vmlinux") or filename.endswith(".ko.debug"):
            modulename = filename.rsplit("/", 1)[1].replace("-", "_")
            if modulename.endswith(".ko.debug"):
                modulename = str(modulename[:-9])

            if not modulename in result:
                result[modulename] = {}

            child = Popen(["eu-readelf", "-s", filename],
                          stdout=PIPE, stderr=STDOUT)
            stdout = child.communicate()[0]
            for line in stdout.splitlines():
                if not "FUNC" in line and not "NOTYPE" in line:
                    continue

                spl = line.split()
                try:
                    result[modulename][spl[7].lstrip("_")] = int(spl[1], 16)
                except IndexError:
                    continue

    return result

def get_debug_file(build_id):
    return "/usr/lib/debug/.build-id/{0}/{1}.debug".format(build_id[:2],
                                                           build_id[2:])

def walk(directory):
    """
    Walks the directory and its subdirectories
    and returns a set of names of found files.
    """
    if not directory.startswith("/"):
        raise Exception, "an absolute path is required"

    result = set()
    for filename in os.listdir(directory):
        fullpath = os.path.join(directory, filename)
        if os.path.isfile(fullpath):
            result.add(fullpath)
        elif os.path.isdir(fullpath):
            result = result.union(walk(fullpath))

    return result

def find_source_in_dir(filename, srcdir, srcfiles=None):
    """
    Tries to find source file in a directory.
    Cuts subdirectories one by one from the left
    and checks whether srcdir contains a file whose path
    ends with the result.
    """
    if not srcdir.startswith("/"):
        raise Exception, "srcdir must be an absolute path"

    filename = filename.lstrip("/")
    candidate = os.path.join(srcdir, filename)
    if os.path.isfile(candidate):
        return candidate

    candidate = candidate.replace("../", "")
    candidate = candidate.replace("./", "")
    candidate = candidate.replace("//", "/")
    if os.path.isfile(candidate):
        return candidate

    if srcfiles is None:
        srcfiles = walk(srcdir)

    while candidate:
        for filename in srcfiles:
            try:
                if filename.endswith(candidate):
                    return filename
            except:
                pass

        if not "/" in candidate:
            break

        candidate = candidate.split("/", 1)[1]

    return None

def read_source_snippets(srcfile, line):
    """
    Opens the file and reads lines line, line +/- 1.
    Returns tuple (line - 1, line, line + 1)
    """
    with open(srcfile, "r") as f:
        lines = [l.rstrip() for l in f.readlines()]

    # lines are numbered from 1, array is indexed from 0
    line = int(line) - 1

    if len(lines) < line:
        raise Exception, "Requested line #{0}, but the file only " \
                         "has {1} lines".format(line + 1, len(lines))

    exact_line = None
    try:
        exact_line = unicode(lines[line], "utf-8")
    except:
        pass

    pre_line = None
    try:
        pre_line = unicode(lines[line - 1], "utf-8")
    except:
        pass

    post_line = None
    try:
        post_line = unicode(lines[line + 1], "utf-8")
    except:
        pass

    return pre_line, exact_line, post_line

class FafAsyncRpmUnpacker(threading.Thread):
    """
    Unpacks RPMs asynchronously. Operates on tasks described above.
    """
    def __init__(self, name, inqueue, outqueue):
        threading.Thread.__init__(self, name=name)
        self.inqueue = inqueue
        self.outqueue = outqueue

    def _handle_next(self):
        task = self.inqueue.popleft()
        logging.info("{0} unpacking {1}".format(self.name,
                                                task["debuginfo"]["nvra"]))
        task["debuginfo"]["unpacked_path"] = \
                package.unpack_rpm_to_tmp(task["debuginfo"]["rpm_path"],
                                          prefix=task["debuginfo"]["nvra"])
        if task["debuginfo"]["nvra"].startswith("kernel-"):
            logging.info("Generating function offset map for kernel modules")
            task["function_offset_map"] = \
                    get_function_offset_map(task["debuginfo"]["unpacked_path"])

        logging.info("{0} unpacking {1}".format(self.name, task["source"]["nvra"]))
        task["source"]["unpacked_path"] = \
                package.unpack_rpm_to_tmp(task["source"]["rpm_path"],
                                          prefix=task["source"]["nvra"])

        if not task["source"]["nvra"].startswith("kernel-debuginfo-common"):
            specfile = None
            for f in os.listdir(task["source"]["unpacked_path"]):
                if f.endswith(".spec"):
                    specfile = os.path.join(task["source"]["unpacked_path"], f)

            if not specfile:
                logging.info("Unable to find specfile")
            else:
                src_dir = os.path.join(task["source"]["unpacked_path"],
                                       "usr", "src", "debug")
                logging.debug("SPEC file: {0}".format(specfile))
                logging.debug("Running rpmbuild")
                with open("/dev/null", "w") as null:
                    retcode = call(["rpmbuild", "--nodeps", "-bp", "--define",
                                    "_sourcedir {0}".format(task["source"]["unpacked_path"]),
                                    "--define", "_builddir {0}".format(src_dir),
                                    "--define",
                                    "_specdir {0}".format(task["source"]["unpacked_path"]),
                                    specfile], stdout=null, stderr=null)
                    if retcode:
                        logging.warn("rpmbuild exitted with {0}".format(retcode))

        task["source"]["files"] = walk(task["source"]["unpacked_path"])

        for pkg in task["packages"]:
            logging.info("{0} unpacking {1}".format(self.name, pkg["nvra"]))
            if pkg["rpm_path"] == task["debuginfo"]["rpm_path"]:
                logging.debug("Already unpacked")
                pkg["unpacked_path"] = task["debuginfo"]["unpacked_path"]
                continue

            pkg["unpacked_path"] = \
                    package.unpack_rpm_to_tmp(pkg["rpm_path"],
                                              prefix=pkg["nvra"])
        self.outqueue.put(task)

    def run(self):
        while True:
            try:
                self._handle_next()
            except IndexError:
                logging.info("{0} terminated".format(self.name))
                break
            except Exception as ex:
                logging.error("{0}: {1}".format(self.name, str(ex)))
                break

def prepare_debuginfo_map(db):
    """
    Prepares the mapping debuginfo ~> packages ~> symbols
    """
    result = {}
    symbolsources = db.session.query(SymbolSource) \
                              .filter(SymbolSource.source_path == None).all()
    todelete = set()
    total = len(symbolsources)
    i = 0
    for symbolsource in symbolsources:
        i += 1
        try:
            if not symbolsource.symbol:
                logging.info("Empty symbol for symbolsource #{0} @ '{1}'" \
                              .format(symbolsource.id, symbolsource.path))
                continue
        except:
            continue

        logging.info("[{0}/{1}] Processing {2} @ '{3}'" \
                     .format(i, total, symbolsource.symbol.name, symbolsource.path))
        if not symbolsource.frames:
            logging.info("No frames found")
            continue

        if symbolsource.frames[0].backtrace.report.type.lower() == "kerneloops":
            version, release, arch, flavour = parse_kernel_build_id(symbolsource.build_id)
            logging.debug("Version = {0}; Release = {1}; Arch = {2}; Flavour = {3}" \
                          .format(version, release, arch, flavour))
            pkgname = "kernel"
            if not flavour is None:
                pkgname = "kernel-{0}".format(flavour)

            debugpkgname = "{0}-debuginfo".format(pkgname)
            debuginfo = db.session.query(Package) \
                                  .join(Build) \
                                  .join(Arch) \
                                  .filter((Package.name == debugpkgname) &
                                          (Build.version == version) &
                                          (Build.release == release) &
                                          (Arch.name == arch)) \
                                  .first()
            if not debuginfo:
                logging.debug("Matching kernel debuginfo not found")
                continue

            if not debuginfo in result:
                result[debuginfo] = {}

            # ugly, but whatever - there is no binary package required
            if not debuginfo in result[debuginfo]:
                result[debuginfo][debuginfo] = set()

            result[debuginfo][debuginfo].add(symbolsource)

            continue

        if symbolsource.frames[0].backtrace.report.type.lower() != "userspace":
            logging.info("Skipping non-userspace symbol")
            continue

        debug_file = get_debug_file(symbolsource.build_id)
        debuginfos = db.session.query(Package) \
                               .join(PackageDependency) \
                               .filter((PackageDependency.name == debug_file) &
                                       (PackageDependency.type == "PROVIDES")) \
                               .all()
        logging.debug("Found {0} debuginfo packages".format(len(debuginfos)))
        for debuginfo in debuginfos:
            package = db.session.query(Package) \
                                .join(PackageDependency) \
                                .filter((PackageDependency.name == symbolsource.path) &
                                        (Package.arch == debuginfo.arch) &
                                        (Package.build_id == debuginfo.build_id)) \
                                .first()
            if not package:
                logging.debug("Trying UsrMove fix")
                if symbolsource.path.startswith("/usr"):
                    newpath = symbolsource.path[4:]
                else:
                    newpath = "/usr{0}".format(symbolsource.path)

                package = db.session.query(Package) \
                                    .join(PackageDependency) \
                                    .filter((PackageDependency.name == newpath) &
                                            (Package.arch == debuginfo.arch) &
                                            (Package.build_id == debuginfo.build_id)) \
                                    .first()
                if package:
                    logging.info("Applying UsrMove fix")
                    conflict = db.session.query(SymbolSource) \
                                         .filter((SymbolSource.path == newpath) &
                                                 (SymbolSource.offset == symbolsource.offset) &
                                                 (SymbolSource.build_id == symbolsource.build_id)) \
                                         .first()
                    if conflict:
                        db.session.execute("UPDATE {0} SET symbolsource_id = :newid " \
                                           "WHERE symbolsource_id = :oldid" \
                                           .format(ReportBtFrame.__tablename__),
                                           {"oldid": symbolsource.id, "newid": conflict.id })
                        todelete.add(symbolsource.id)
                        db.session.expunge(symbolsource)
                        symbolsource = conflict
                    else:
                        symbolsource.path = newpath

            if not package:
                logging.debug("Matching binary package not found")
                continue

            if not debuginfo in result:
                result[debuginfo] = {}

            if not package in result[debuginfo]:
                result[debuginfo][package] = set()

            result[debuginfo][package].add(symbolsource)
            break
        else:
            logging.warn("Unable to find a suitable package combination")

    db.session.flush()
    if todelete:
        # cond1 | cond2 | cond3 | ... | cond_n-1 | cond_n
        # delete by slices of 100 members - reduce is recursive
        todelete = list(todelete)
        for i in xrange((len(todelete) + 99) / 100):
            part = todelete[(100 * i):(100 * (i + 1))]
            cond = reduce(lambda x, y: x | y, [SymbolSource.id == id for id in part])
            db.session.query(SymbolSource).filter(cond).delete()

    return result

def prepare_tasks(db, debuginfo_map):
    """
    Creates tasks from debuginfo map
    """
    result = []
    for debuginfo in debuginfo_map:
        packages = []
        for package in debuginfo_map[debuginfo]:
            pkg_entry = { "package": package,
                          "nvra": package.nvra(),
                          "rpm_path": package.get_lob_path("package"),
                          "symbols": debuginfo_map[debuginfo][package] }
            packages.append(pkg_entry)

        if debuginfo.name.startswith("kernel"):
            common = "kernel-debuginfo-common-{0}".format(debuginfo.arch.name)
            source = db.session.query(Package) \
                               .join(Arch) \
                               .join(Build) \
                               .filter((Build.id == debuginfo.build_id) &
                                       (Package.arch == debuginfo.arch) &
                                       (Package.name == common)) \
                               .one()
        else:
            source = db.session.query(Package) \
                               .join(Arch) \
                               .join(Build) \
                               .filter((Build.id == debuginfo.build_id) &
                                       (Arch.name == "src")) \
                               .one()

        task = { "debuginfo": { "package": debuginfo,
                                "nvra": debuginfo.nvra(),
                                "rpm_path": debuginfo.get_lob_path("package") },
                 "source":    { "package": source,
                                "nvra": source.nvra(),
                                "rpm_path": source.get_lob_path("package") },
                 "packages":  packages }

        result.append(task)

    return result

def retrace_task(db, task):
    """
    Runs the retrace logic on a task and saves results to storage
    """

    for pkg in task["packages"]:
        for symbolsource in pkg["symbols"]:
            normalized_path = get_libname(symbolsource.path)

            # userspace
            if symbolsource.path.startswith("/"):
                result = retrace_symbol(symbolsource.path,
                                        symbolsource.offset,
                                        pkg["unpacked_path"],
                                        task["debuginfo"]["unpacked_path"])
            # kerneloops
            else:
                filename = "vmlinux"
                if symbolsource.path != "vmlinux":
                    filename = "{0}.ko.debug".format(symbolsource.path.replace("_", "-"))

                dep = db.session.query(PackageDependency) \
                                .filter((PackageDependency.name.like("%/{0}".format(filename))) &
                                        (PackageDependency.package_id == pkg["package"].id) &
                                        (PackageDependency.type == "PROVIDES")) \
                                .first()

                if not dep:
                    logging.debug("{0} not found".format(filename))
                    continue


                fmap = task["function_offset_map"]
                if not symbolsource.path in fmap:
                    logging.debug("Module {0} has no functions associated" \
                                  .format(symbolsource.path))
                    continue

                modmap = fmap[symbolsource.path]
                if not symbolsource.symbol.name in modmap:
                    logging.debug("Function {0} is not present in {1} module" \
                                  .format(symbolsource.symbol.name,
                                          symbolsource.path))
                    continue

                offset = task["function_offset_map"][symbolsource.path][symbolsource.symbol.name]
                result = retrace_symbol(dep.name,
                                        symbolsource.offset + offset,
                                        pkg["unpacked_path"],
                                        task["debuginfo"]["unpacked_path"],
                                        absolute_offset=True)

            if result is None:
                logging.warn("eu-unstrip failed")
                continue

            logging.debug("Result: {0}".format(str(result)))
            if len(result) > 1:
                inlined_name, inlined_source_path, inlined_line_number = result[1]
                logging.debug("Separating inlined function {0}" \
                        .format(inlined_name))
                inlined_line_number = int(inlined_line_number)

                inlined_source = db.session.query(SymbolSource) \
                                           .filter((SymbolSource.build_id == symbolsource.build_id) &
                                                   (SymbolSource.path == symbolsource.path) &
                                                   (SymbolSource.offset == -inlined_line_number)) \
                                           .first()
                if not inlined_source:
                    logging.debug("Creating new SymbolSource")
                    inlined_source = SymbolSource()
                    inlined_source.build_id = symbolsource.build_id
                    inlined_source.path = symbolsource.path
                    inlined_source.offset = -inlined_line_number
                    inlined_source.source_path = inlined_source_path
                    inlined_source.line_number = inlined_line_number
                    db.session.add(inlined_source)

                    inlined_symbol = db.session.query(Symbol) \
                                               .filter((Symbol.name == inlined_name) &
                                                       (Symbol.normalized_path == normalized_path)) \
                                               .first()
                    if not inlined_symbol:
                        nice_name = cpp_demangle(inlined_name)
                        logging.debug("Creating new Symbol")
                        inlined_symbol = Symbol()
                        inlined_symbol.name = inlined_name
                        if nice_name != inlined_name:
                            logging.debug("Demangled {0} = {1}".format(inlined_name,
                                                                       nice_name))
                            inlined_symbol.nice_name = nice_name
                        inlined_symbol.normalized_path = normalized_path
                        db.session.add(inlined_symbol)
                        db.session.flush()

                    inlined_source.symbol = inlined_symbol

                    logging.debug("Trying to read source snippet")
                    srcfile = find_source_in_dir(inlined_source.source_path,
                                                 task["source"]["unpacked_path"],
                                                 task["source"]["files"])
                    if srcfile:
                        logging.debug("Reading file '{0}'".format(srcfile))
                        try:
                            l1, l2, l3 = read_source_snippets(srcfile,
                                                              inlined_source.line_number)
                            inlined_source.presrcline = l1
                            inlined_source.srcline = l2
                            inlined_source.postsrcline = l3
                        except Exception as ex:
                            logging.debug(str(ex))
                    else:
                        logging.debug("Source file not found")

                    db.session.flush()

                total = len(symbolsource.frames)
                for i in xrange(total):
                    frame = sorted(symbolsource.frames,
                                   key=lambda x: (x.backtrace_id, x.order))[i]
                    order = frame.order
                    backtrace = frame.backtrace
                    backtrace_id = backtrace.id
                    frames = backtrace.frames

                    if frames[order - 1].inlined:
                        logging.debug("Already shifted")
                        continue

                    logging.debug("Shifting frames")
                    safe_shift_distance = 2 * len(frames)
                    for f in frames:
                        db.session.expunge(f)
                    db.session.expunge(backtrace)

                    db.session.execute("UPDATE {0} "
                                       "SET \"order\" = \"order\" + :safe_distance "
                                       "WHERE backtrace_id = :bt_id AND \"order\" >= :from" \
                                       .format(ReportBtFrame.__tablename__),
                                       {"safe_distance": safe_shift_distance,
                                        "bt_id": backtrace_id,
                                        "from": order})

                    db.session.execute("UPDATE {0} "
                                       "SET \"order\" = \"order\" - :safe_distance + 1 "
                                       "WHERE backtrace_id = :bt_id AND "
                                       "      \"order\" >= :from + :safe_distance" \
                                       .format(ReportBtFrame.__tablename__),
                                       {"safe_distance": safe_shift_distance,
                                        "bt_id": backtrace_id,
                                        "from": order})

                    logging.debug("Creating new ReportBtFrame")
                    newframe = ReportBtFrame()
                    newframe.backtrace_id = backtrace_id
                    newframe.order = order
                    newframe.symbolsource = inlined_source
                    newframe.inlined = True
                    db.session.add(newframe)
                    db.session.flush()

            symbol_name, symbolsource.source_path, symbolsource.line_number = result[0]
            if symbol_name == "??":
                logging.debug("eu-addr2line returned '??', using original "
                              "'{0}' for function name".format(symbolsource.symbol.name))
                symbol_name = symbolsource.symbol.name

            symbol = db.session.query(Symbol) \
                               .filter((Symbol.name == symbol_name) &
                                       (Symbol.normalized_path == normalized_path)) \
                               .first()
            if not symbol:
                nice_name = cpp_demangle(symbol_name)
                logging.debug("Creating new Symbol")
                symbol = Symbol()
                symbol.name = symbol_name
                if nice_name != symbol_name:
                    logging.debug("Demangled {0} = {1}".format(symbol_name, nice_name))
                    symbol.nice_name = nice_name
                symbol.normalized_path = normalized_path
                db.session.add(symbol)
                db.session.flush()

            symbolsource.symbol = symbol

            logging.debug("Trying to read source snippet")
            srcfile = find_source_in_dir(symbolsource.source_path,
                                         task["source"]["unpacked_path"],
                                         task["source"]["files"])
            if srcfile:
                logging.debug("Reading file '{0}'".format(srcfile))
                try:
                    l1, l2, l3 = read_source_snippets(srcfile,
                                                      symbolsource.line_number)
                    symbolsource.presrcline = l1
                    symbolsource.srcline = l2
                    symbolsource.postsrcline = l3
                except Exception as ex:
                    logging.info(str(ex))
            else:
                logging.debug("Source file not found")

        # pkg == debuginfo for kerneloops
        if pkg["unpacked_path"] != task["debuginfo"]["unpacked_path"]:
            logging.debug("Deleting {0}".format(pkg["unpacked_path"]))
            shutil.rmtree(pkg["unpacked_path"])

    logging.debug("Deleting {0}".format(task["source"]["unpacked_path"]))
    shutil.rmtree(task["source"]["unpacked_path"])

    logging.debug("Deleting {0}".format(task["debuginfo"]["unpacked_path"]))
    shutil.rmtree(task["debuginfo"]["unpacked_path"])

    db.session.flush()
