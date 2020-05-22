import re
from concurrent import futures

from typing import Any, Dict, List, Tuple, Union

from pyfaf.common import FafError, log, thread_logger
from pyfaf.queries import get_debug_files
from pyfaf.faf_rpm import unpack_rpm_to_tmp
from pyfaf.utils.proc import safe_popen

# Instance of 'RootLogger' has no 'getChild' member
# Invalid name "log" for type constant
# pylint: disable-msg=C0103,E1103
log = log.getChild(__name__)
# pylint: enable-msg=C0103

RE_ADDR2LINE_LINE1 = re.compile(r"^([_0-9a-zA-Z\.~<>@:\*&,\)"
                                r"\( \[\]=]+|operator[^ ]+|\?\?)"
                                r"(\+0x[0-9a-f]+)?"
                                r"( inlined at ([^:]+):([0-9]+) in (.*))?$")

RE_UNSTRIP_BASE_OFFSET = re.compile(r"^((0x)?[0-9a-f]+)")

__all__ = ["IncompleteTask", "RetraceTaskPackage", "RetraceTask",
           "RetracePool", "addr2line", "demangle", "get_base_address",
           "ssource2funcname", "usrmove"]


class IncompleteTask(FafError):
    pass


class RetraceTaskPackage(object):
    """
    A "buffer" representing pyfaf.storage.Package. SQL Alchemy objects are
    not threadsafe and this object is used to query and buffer all
    the necessary information so that DB calls are not required from workers.
    """

    def __init__(self, db_package) -> None:
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
    def unpack_to_tmp(self, *args, **kwargs) -> None:
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

    def __init__(self, db_debug_package, db_src_package, bin_pkg_map, db=None) -> None:
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


class RetracePool:
    """
    A class representing a pool of workers that run the retracing job for given tasks.
    """

    def __init__(self, db, tasks, problemplugin, workers) -> None:

        self.name = "RetracePool"
        self.log = thread_logger.getChild(self.name)
        self.db = db
        self.plugin = problemplugin
        self.tasks = tasks
        self.total = len(tasks)
        self.workers = workers

    def run(self) -> None:
        """
        Starts the executors job and schedules tasks for workers when they are available.
        """
        taskid = 0
        name = "Worker"

        with futures.ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix=name) as executor:
            while self.tasks:
                taskid += 1
                task = self.tasks.popleft()
                try:
                    future = executor.submit(self._process_task, task, taskid)
                    future.add_done_callback(self._future_done_callback)
                except RuntimeError as ex:
                    self.log.error("Failed to submit retracing task: {0}".format(str(ex)))

    def _process_task(self, task, num) -> None:
        """
        Helper method for processing future tasks.
        """
        self.log.info("[{0} / {1}] Retracing {2}".format(num, self.total, task.debuginfo.nvra))
        self._unpack_task_pkg(task)
        self.plugin.retrace(self.db, task)

    def _future_done_callback(self, future) -> None:
        """
        Helper callback for completed futures.

        Flushes the data to db when the task ends successfully.
        """
        if future.cancelled():
            self.log.warn("Retracing task cancelled: {0}".format(str(future.cancelled())))
        elif future.done():
            exception = future.exception()
            if exception is not None:
                self.log.warn("Retracing task encountered an exception: {0}".format(str(exception)))
            else:
                self.db.session.flush()

    def _unpack_task_pkg(self, task) -> None:
        """
        Helper for unpacking a set of packages (debuginfo, source, binary)
        """

        self.log.debug("Unpacking '%s'", task.debuginfo.nvra)
        task.debuginfo.unpacked_path = \
            task.debuginfo.unpack_to_tmp(task.debuginfo.path,
                                         prefix=task.debuginfo.nvra)

        if task.source is not None:
            self.log.debug("Unpacking '%s'", task.source.nvra)
            task.source.unpacked_path = \
                task.source.unpack_to_tmp(task.source.path,
                                          prefix=task.source.nvra)

        for bin_pkg in task.binary_packages.keys():
            self.log.debug("Unpacking '%s'", bin_pkg.nvra)
            if bin_pkg.path == task.debuginfo.path:
                self.log.debug("Already unpacked")
                continue

            bin_pkg.unpacked_path = bin_pkg.unpack_to_tmp(bin_pkg.path,
                                                          prefix=bin_pkg.nvra)


def addr2line(binary_path, address, debuginfo_dir) -> List[Tuple[str, Any, int]]:
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
                           "--functions", addr,
                           encoding="utf-8")

        if child is None:
            raise FafError("eu-add2line failed")

        line1, line2 = child.stdout.splitlines()
        # format of the line2 is filename:lineno[:columnno]
        line2_parts = line2.split(":")
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
        if match.group(3) is None:
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


def get_base_address(binary_path) -> int:
    """
    Runs eu-unstrip on a binary to get the address used
    as base for calculating relative offsets.
    """

    child = safe_popen("eu-unstrip", "-n", "-e", binary_path, encoding="utf-8")

    if child is None:
        raise FafError("eu-unstrip failed")

    match = RE_UNSTRIP_BASE_OFFSET.match(child.stdout)
    if match is None:
        raise FafError("Unexpected output from eu-unstrip: '{0}'"
                       .format(child.stdout))

    return int(match.group(1), 16)


def demangle(mangled) -> Union[None, str]:
    """
    Demangle C++ symbol name.
    """

    child = safe_popen("c++filt", mangled, encoding="utf-8")
    if child is None:
        return None

    result = child.stdout.strip()
    if result != mangled:
        log.debug("Demangled: '%s' ~> '%s'", mangled, result)

    return result


def usrmove(path: str) -> str:
    """
    Adds or cuts off /usr prefix from the path.
    http://fedoraproject.org/wiki/Features/UsrMove
    """

    if path.startswith("/usr"):
        return path[4:]

    return "/usr{0}".format(path)


def ssource2funcname(db_ssource) -> str:
    """
    Returns the symbol.name property of symbolsource of '??' if symbol is None
    """

    if db_ssource.symbol is None:
        return "??"

    return db_ssource.symbol.name


def get_function_offset_map(files) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}

    for filename in files:
        modulename = filename.rsplit("/", 1)[1].replace("-", "_")
        if modulename.endswith(".ko.debug"):
            modulename = str(modulename[:-9])

        if modulename not in result:
            result[modulename] = {}

        child = safe_popen("eu-readelf", "-s", filename, encoding="utf-8")
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
