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

import sys
if sys.version_info.major == 2:
#Python 2
    import Queue as queue
else:
#Python 3+
    import queue

import collections
import multiprocessing

from pyfaf.actions import Action
from pyfaf.common import FafError
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import update_frame_ssource
from pyfaf.retrace import (IncompleteTask,
                           RetraceTask,
                           RetraceWorker,
                           ssource2funcname)
from six.moves import range

class Retrace(Action):
    name = "retrace"

    def __init__(self):
        super(Retrace, self).__init__()

    def _get_pkgmap(self, db, problemplugin, db_ssources):
        """
        Return the mapping {db_debug_pkg: (db_src_pkg, binpkgmap), ...} where
        binpkgmap is mapping {db_bin_pkg: [db_ssource1, db_ssource2, ...], ...}
        """

        result = {}

        i = 0
        for db_ssource in db_ssources:
            i += 1
            self.log_debug(u"[{0} / {1}] Processing '{2}' @ '{3}'"
                           .format(i, len(db_ssources),
                                   ssource2funcname(db_ssource),
                                   db_ssource.path))

            try:
                pkgs = problemplugin.find_packages_for_ssource(db, db_ssource)
            except FafError as ex:
                self.log_warn(str(ex))
                continue

            db_ssource_valid_path, (db_debug_pkg, db_bin_pkg, db_src_pkg) = pkgs

            if db_ssource_valid_path != db_ssource:
                update_frame_ssource(db, db_ssource, db_ssource_valid_path)

            if db_debug_pkg is not None:
                if db_debug_pkg not in result:
                    result[db_debug_pkg] = (db_src_pkg, {})

                if db_bin_pkg is not None:
                    binpkgmap = result[db_debug_pkg][1]
                    if db_bin_pkg not in binpkgmap:
                        binpkgmap[db_bin_pkg] = set()

                    binpkgmap[db_bin_pkg].add(db_ssource_valid_path)

        return result

    def run(self, cmdline, db):
        if cmdline.workers < 1:
            self.log_error("At least 1 worker is required")
            return 1

        if len(cmdline.problemtype) < 1:
            ptypes = list(problemtypes.keys())
        else:
            ptypes = cmdline.problemtype

        for ptype in ptypes:
            if not ptype in problemtypes:
                self.log_warn("Problem type '{0}' is not supported"
                              .format(ptype))
                continue

            problemplugin = problemtypes[ptype]

            self.log_info("Processing '{0}' problem type"
                          .format(problemplugin.nice_name))

            db_ssources = problemplugin.get_ssources_for_retrace(
                db, cmdline.max_fail_count, yield_per=cmdline.batch)
            if len(db_ssources) < 1:
                continue

            pkgmap = self._get_pkgmap(db, problemplugin, db_ssources)

            # self._get_pkgmap may change paths, flush the changes
            db.session.flush()

            tasks = []

            i = 0
            for db_debug_pkg, (db_src_pkg, binpkgmap) in pkgmap.items():
                i += 1

                self.log_debug("[{0} / {1}] Creating task for '{2}'"
                               .format(i, len(pkgmap), db_debug_pkg.nvra()))

                try:
                    tasks.append(RetraceTask(db_debug_pkg, db_src_pkg,
                                             binpkgmap, db=db))
                except IncompleteTask as ex:
                    self.log_debug(str(ex))

            inqueue = collections.deque(tasks)
            outqueue = queue.Queue(cmdline.workers)
            total = len(tasks)

            workers = [RetraceWorker(i, inqueue, outqueue)
                       for i in range(cmdline.workers)]

            for worker in workers:
                self.log_debug("Spawning {0}".format(worker.name))
                worker.start()

            i = 0
            try:
                while True:
                    wait = any(w.is_alive() for w in workers)
                    try:
                        task = outqueue.get(wait, 1)
                    except queue.Empty:
                        if any(w.is_alive() for w in workers):
                            continue

                        self.log_info("All done")
                        break

                    i += 1
                    self.log_info("[{0} / {1}] Retracing {2}"
                                  .format(i, total, task.debuginfo.nvra))
                    problemplugin.retrace(db, task)
                    db.session.flush()
                    outqueue.task_done()
            except:
                for worker in workers:
                    worker.stop = True

                raise

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
        parser.add_argument("--workers", type=int,
                            default=multiprocessing.cpu_count(),
                            help="Number of threads unpacking RPMs")
        parser.add_argument("--max-fail-count", type=int,
                            default=-1,
                            help="Only retrace symbols which failed at most this"
                                 " number of times")
        parser.add_argument("--batch", type=int,
                            default=1000,
                            help="Process symbols source in batches. "
                            "0 turns batch processing off.")
