import re
import threading
from pyfaf.common import FafError, log
from pyfaf.queries import get_debug_files
from pyfaf.rpm import unpack_rpm_to_tmp
from pyfaf.utils.proc import safe_popen
from six.moves import range

# Instance of 'RootLogger' has no 'getChildLogger' member
# Invalid name "log" for type constant
# pylint: disable-msg=C0103,E1103
log = log.getChildLogger(__name__)
# pylint: enable-msg=C0103

RE_ADDR2LINE_LINE1 = re.compile(r"^([_0-9a-zA-Z\.~<>@:\*&,\)"
                                r"\( \[\]=]+|operator[^ ]+|\?\?)"
                                r"(\+0x[0-9a-f]+)?"
                                r"( inlined at ([^:]+):([0-9]+) in (.*))?$")

RE_UNSTRIP_BASE_OFFSET = re.compile(r"^((0x)?[0-9a-f]+)")

__all__ = ["IncompleteTask", "RetraceTaskPackage", "RetraceTask",
           "RetraceWorker", "addr2line", "demangle", "get_base_address",
           "ssource2funcname", "usrmove"]

class IncompleteTask(FafError):
    pass


class RetraceTaskPackage(object):
    """
    A "buffer" representing pyfaf.storage.Package. SQL Alchemy objects are
    not threadsafe and this object is used to query and buffer all
    the necessary information so that DB calls are not required from workers.
    """

    def __init__(self, db_package):
        self.db_package = db_package

        self.nvra = db_package.nvra()

        if db_package.pkgtype.lower() == "rpm":
            self.unpack_to_tmp = unpack_rpm_to_tmp

        self.path = None
        if db_package.has_lob("package"):
            self.path = db_package.get_lob_path("package")

        self.unpacked_path = None

    # An attribute affected in pyfaf.retrace line 32 hide this method
    # pylint: disable-msg=E0202
    def unpack_to_tmp(self, *args, **kwargs):
        """
        Used to unpack the package to a temp directory. Is dependent on
        package type: RPM/DEB/...
        """

        raise NotImplementedError
    # pylint: disable-msg=E0202


# Too few public methods
# pylint: disable-msg=R0903
class RetraceTask(object):
    """
    A class representing the retrace task, containing information about
    all packages and symbols related to the task.
    """

    def __init__(self, db_debug_package, db_src_package, bin_pkg_map, db=None):
        self.debuginfo = RetraceTaskPackage(db_debug_package)
        if self.debuginfo.path is None:
            raise IncompleteTask("Package lob for {0} not found in storage"
                                 .format(self.debuginfo.nvra))

        if db is None:
            self.debuginfo.debug_files = None
        else:
            self.debuginfo.debug_files = get_debug_files(db, db_debug_package)

        if db_src_package is None:
            self.source = None
        else:
            self.source = RetraceTaskPackage(db_src_package)
            if self.source.path is None:
                raise IncompleteTask("Package lob for {0} not found in storage"
                                     .format(self.source.nvra))

        self.binary_packages = {}
        if bin_pkg_map is not None:
            for db_bin_package, db_ssources in bin_pkg_map.items():
                pkgobj = RetraceTaskPackage(db_bin_package)
                if pkgobj.path is None:
                    raise IncompleteTask("Package lob for {0} not found in "
                                         "storage".format(pkgobj.nvra))

                self.binary_packages[pkgobj] = db_ssources
# pylint: enable-msg=R0903


class RetraceWorker(threading.Thread, object):
    """
    The worker providing asynchronous unpacking of packages.
    """

    def __init__(self, worker_id, inqueue, outqueue):
        name = "Worker #{0}".format(worker_id)
        super(RetraceWorker, self).__init__(name=name)
        self.inqueue = inqueue
        self.outqueue = outqueue
        self.stop = False
        # Instance of 'RootLogger' has no 'getChildLogger' member
        # pylint: disable-msg=E1103
        self.log = log.getChildLogger("{0}.{1}".format(self.__class__.__name__,
                                                       self.name))
        # pylint: enable-msg=E1103

    def _process_task(self, task):
        """
        Asynchronously unpack one set of packages (debuginfo, source, binary)
        """

        self.log.info("Unpacking '{0}'".format(task.debuginfo.nvra))
        task.debuginfo.unpacked_path = \
            task.debuginfo.unpack_to_tmp(task.debuginfo.path,
                                         prefix=task.debuginfo.nvra)

        if task.source is not None:
            self.log.info("Unpacking '{0}'".format(task.source.nvra))
            task.source.unpacked_path = \
                task.source.unpack_to_tmp(task.source.path,
                                          prefix=task.source.nvra)

        for bin_pkg in task.binary_packages.keys():
            self.log.info("Unpacking '{0}'".format(bin_pkg.nvra))
            if bin_pkg.path == task.debuginfo.path:
                self.log.info("Already unpacked")
                continue

            bin_pkg.unpacked_path = bin_pkg.unpack_to_tmp(bin_pkg.path,
                                                          prefix=bin_pkg.nvra)

    def run(self):
        while not self.stop:
            try:
                task = self.inqueue.popleft()
                self._process_task(task)
                self.outqueue.put(task)
            except FafError as ex:
                self.log.warn("Unpacking failed: {0}".format(str(ex)))
                continue
            except IndexError:
                break

        self.log.info("{0} terminated".format(self.name))


def addr2line(binary_path, address, debuginfo_dir):
    """
    Calls eu-addr2line on a binary, address and directory with debuginfo.
    Returns an ordered list of triplets (function name, source file, line no).
    The last element is always the symbol given to retrace. The elements
    before are inlined symbols that should be placed above the given symbol
    (assuming that entry point is on the bottom of the stacktrace).
    """

    result = []
    funcname = None
    srcfile = "??"
    srcline = 0

    # eu-addr2line often finds the symbol if we decrement the address by one.
    # we try several addresses that maps to no file or to the same source file
    # and source line as the original address.
    for addr_enh in range(0, 15):
        if addr_enh > address:
            break

        addr = "0x{0:x}".format(address - addr_enh)
        child = safe_popen("eu-addr2line",
                           "--executable", binary_path,
                           "--debuginfo-path", debuginfo_dir,
                           "--functions", addr)

        if child is None:
            raise FafError("eu-add2line failed")

        line1, line2 = child.stdout.splitlines()
        line2_parts = line2.split(":", 1)
        line2_srcfile = line2_parts[0]
        line2_srcline = int(line2_parts[1])

        match = RE_ADDR2LINE_LINE1.match(line1)
        if match is None:
            raise FafError("Unexpected output from eu-addr2line: '{0}'"
                           .format(line1))

        if srcfile != line2_srcfile or srcline != line2_srcline:
            if srcfile != "??" or srcline != 0:
                break

        if match.group(1) == "??":
            srcfile = line2_srcfile
            srcline = line2_srcline
            continue
        elif match.group(3) is None:
            funcname = match.group(1)
            srcfile = line2_srcfile
            srcline = line2_srcline
        else:
            funcname = match.group(6)
            srcfile = match.group(4)
            srcline = int(match.group(5))

            result.append((match.group(1), line2_srcfile, line2_srcline))

        break

    if funcname is None:
        raise FafError("eu-addr2line cannot find function name")

    result.append((funcname, srcfile, srcline))

    return result


def get_base_address(binary_path):
    """
    Runs eu-unstrip on a binary to get the address used
    as base for calculating relative offsets.
    """

    child = safe_popen("eu-unstrip", "-n", "-e", binary_path)

    if child is None:
        raise FafError("eu-unstrip failed")

    match = RE_UNSTRIP_BASE_OFFSET.match(child.stdout)
    if match is None:
        raise FafError("Unexpected output from eu-unstrip: '{0}'"
                       .format(child.stdout))

    return int(match.group(1), 16)


def demangle(mangled):
    """
    Demangle C++ symbol name.
    """

    child = safe_popen("c++filt", mangled)
    if child is None:
        return None

    result = child.stdout.strip()
    if result != mangled:
        log.debug("Demangled: '{0}' ~> '{1}'".format(mangled, result))

    return result


def usrmove(path):
    """
    Adds or cuts off /usr prefix from the path.
    http://fedoraproject.org/wiki/Features/UsrMove
    """

    if path.startswith("/usr"):
        return path[4:]

    return "/usr{0}".format(path)


def ssource2funcname(db_ssource):
    """
    Returns the symbol.name property of symbolsource of '??' if symbol is None
    """

    if db_ssource.symbol is None:
        return "??"

    return db_ssource.symbol.name


def get_function_offset_map(files):
    result = {}

    for filename in files:
        modulename = filename.rsplit("/", 1)[1].replace("-", "_")
        if modulename.endswith(".ko.debug"):
            modulename = str(modulename[:-9])

        if not modulename in result:
            result[modulename] = {}

        child = safe_popen("eu-readelf", "-s", filename)
        if child is None:
            continue

        for line in child.stdout.splitlines():
            if not "FUNC" in line and not "NOTYPE" in line:
                continue

            spl = line.split()
            try:
                result[modulename][spl[7].lstrip("_")] = int(spl[1], 16)
            except IndexError:
                continue

    return result
