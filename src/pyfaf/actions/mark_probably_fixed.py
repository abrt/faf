# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

from __future__ import division
from datetime import datetime
from pyfaf.actions import Action
from pyfaf.common import FafError
from pyfaf.queries import (get_build_by_nevr,
                           get_crashed_unknown_package_nevr_for_report,
                           get_crashed_package_for_report,
                           get_problems,
                           get_problem_opsysrelease,
                           get_reports_for_opsysrelease,
                           get_opsys_by_name,
                           get_osrelease)
from pyfaf.storage import ProblemOpSysRelease, Build
from pyfaf.opsys import systems
from pyfaf.utils.parse import cmp_evr


class MarkProbablyFixed(Action):
    name = "mark-probably-fixed"

    def __init__(self):
        super(MarkProbablyFixed, self).__init__()

    def _get_tasks(self, cmdline, db):
        result = set()

        # no arguments - pull everything for non-EOL releases
        if len(cmdline.opsys) < 1:
            for osplugin in systems.values():
                db_opsys = get_opsys_by_name(db, osplugin.nice_name)
                if db_opsys is None:
                    raise FafError("Operating system '{0}' is not defined in "
                                   "storage".format(osplugin.nice_name))

                for db_release in db_opsys.releases:
                    if db_release.status != "EOL":
                        result.add((osplugin, db_release))

        # a single opsys - respect opsysrelease
        elif len(cmdline.opsys) == 1:
            if cmdline.opsys[0] not in systems:
                raise FafError("Operating system '{0}' is not supported"
                               .format(cmdline.opsys[0]))

            osplugin = systems[cmdline.opsys[0]]
            db_opsys = get_opsys_by_name(db, osplugin.nice_name)
            if db_opsys is None:
                raise FafError("Operating system '{0}' is not defined in "
                               "storage".format(osplugin.nice_name))

            if len(cmdline.opsys_release) < 1:
                for db_release in db_opsys.releases:
                    result.add((osplugin, db_release))
            else:
                for release in cmdline.opsys_release:
                    db_release = get_osrelease(db, osplugin.nice_name, release)
                    if db_release is None:
                        self.log_warn("Operating system '{0} {1}' is not "
                                      "supported".format(osplugin.nice_name,
                                                         release))
                        continue

                    result.add((osplugin, db_release))

        # multiple opsys - pull all of their releases
        else:
            for opsys_name in cmdline.opsys:
                if not opsys_name in systems:
                    self.log_warn("Operating system '{0}' is not supported"
                                  .format(opsys_name))
                    continue

                osplugin = systems[opsys_name]
                db_opsys = get_opsys_by_name(db, osplugin.nice_name)
                if db_opsys is None:
                    self.log_warn("Operating system '{0}' is not defined in "
                                  "storage".format(osplugin.nice_name))
                    continue

                for db_release in db_opsys.releases:
                    result.add((osplugin, db_release))

        return sorted(result, key=lambda p_r: (p_r[1].opsys.name, p_r[1].version))

    def _save_probable_fix(self, db, problem, db_release, probable_fix,
                           probably_fixed_since=None):
        problem_release = get_problem_opsysrelease(db, problem.id,
                                                   db_release.id)

        if not problem_release:
            problem_release = ProblemOpSysRelease()
            problem_release.problem_id = problem.id
            problem_release.opsysrelease_id = db_release.id
        if not probable_fix:
            problem_release.probable_fix_build_id = None
        else:
            build = get_build_by_nevr(db, probable_fix[0], probable_fix[1],
                                      probable_fix[2], probable_fix[3])
            if build is None:
                build = Build()
                build.base_package_name = probable_fix[0]
                build.epoch = probable_fix[1]
                build.version = probable_fix[2]
                build.release = probable_fix[3]
                db.session.add(build)

            problem_release.probable_fix_build = build

        problem_release.probably_fixed_since = probably_fixed_since
        db.session.add(problem_release)

    def run(self, cmdline, db):
        """
        Mark a problem probably fixed if there is a new build of the problem's
        affected package, for which no crash reports have come in.
        """

        try:
            tasks = self._get_tasks(cmdline, db)
        except FafError as ex:
            self.log_error("Unable to process command line arguments: {0}"
                           .format(str(ex)))
            return 1

        problems = get_problems(db)

        task_i = 0
        for osplugin, db_release in tasks:
            task_i += 1

            self.log_info("[{0} / {1}] Processing '{2} {3}'"
                          .format(task_i, len(tasks), osplugin.nice_name,
                                  db_release.version))

            self.log_debug("Getting builds...")
            opsys_builds = osplugin.get_released_builds(db_release.version)

            newest_builds = {}
            all_builds = {}
            now = datetime.now()
            for build in opsys_builds:
                age = now - build["completion_time"]
                # If a hot new build comes out, we need to wait a certain
                # period of time for people to use it before we can make
                # conclusions about it being a probable fix.
                if age.days >= osplugin.build_aging_days:
                    if build["name"] not in newest_builds:
                        newest_builds[build["name"]] = build

                    if build["name"] not in all_builds:
                        all_builds[build["name"]] = [build, ]
                    else:
                        all_builds[build["name"]].append(build)

            probably_fixed_total = 0
            problems_in_release = 0
            problem_counter = 0
            for problem in problems:
                problem_counter += 1
                self.log_debug("Processing problem ID:{0} {1}/{2}:"
                               .format(problem.id, problem_counter, len(problems)))
                affected_newest = {}
                affected_not_found = False

                reports_for_release =  \
                    get_reports_for_opsysrelease(db, problem.id, db_release.id)

                # For all the reports, we need the affected packages and their
                # newest versions.
                if len(reports_for_release) > 0:
                    problems_in_release += 1
                else:
                    self.log_debug(" This problem doesn't appear in this release.")
                    self._save_probable_fix(db, problem, db_release, None)
                    # Next problem
                    continue

                for report in reports_for_release:
                    # First we try to find the affected package among the known
                    # packages.
                    affected_known = [
                        (affected.build.base_package_name,
                         affected.build.epoch,
                         affected.build.version,
                         affected.build.release) for affected in
                        get_crashed_package_for_report(db, report.id)]

                    # Then among the unknown packages.
                    affected_unknown = \
                        get_crashed_unknown_package_nevr_for_report(db, report.id)
                    # We get the base package name directly from the report
                    affected_unknown = [(report.component.name,
                                         affected[1],
                                         affected[2],
                                         affected[3]) for affected in affected_unknown]

                    affected_all = affected_known + affected_unknown
                    if len(affected_all) == 0:
                        affected_not_found = True
                        break

                    for affected in affected_all:
                        if affected[0] in affected_newest:
                            # If a problem contains multiple reports with the same
                            # affected package, we only want the newest version of
                            # it.
                            affected_newest[affected[0]]['reports'].append(report)
                            if cmp_evr(affected[1:],
                                       affected_newest[affected[0]]['nevr'][1:]) > 0:
                                affected_newest[affected[0]]['nevr'] = affected
                        else:
                            affected_newest[affected[0]] = {
                                'reports': [report, ],
                                'nevr': affected
                            }

                if affected_not_found or len(affected_newest) == 0:
                    # Affected package of one of the reports was not found.
                    # We can't make any conclusions.
                    self.log_debug(" Affected package not found.")
                    self._save_probable_fix(db, problem, db_release, None)
                    # Next problem
                    continue

                if len(affected_newest) > 1:
                    # Multiple different affected packages => cannot be fixed
                    # by a single package update
                    self.log_debug(" Multiple affected packages. No simple fix.")
                    self._save_probable_fix(db, problem, db_release, None)
                    # Next problem
                    continue

                probably_fixed_since = datetime.fromtimestamp(0)

                pkg = list(affected_newest.values())[0]

                name = pkg['nevr'][0]
                newest_build = newest_builds.get(name, False)
                if newest_build:
                    newest_evr = (newest_build["epoch"] or 0,
                                  newest_build["version"],
                                  newest_build["release"])
                if newest_build and cmp_evr(newest_evr, pkg['nevr'][1:]) > 0:
                    # Newest available build is newer than the newest version
                    # of the affected package. Now find the oldest such
                    # probable fix.
                    i = 0
                    while i < len(all_builds[name]) and cmp_evr(
                            (all_builds[name][i]["epoch"] or 0,
                             all_builds[name][i]["version"],
                             all_builds[name][i]["release"]), pkg['nevr'][1:]) > 0:
                        i += 1
                    completion_time = all_builds[name][i-1]["completion_time"]
                    probably_fixed_since = max(completion_time,
                                               probably_fixed_since)
                    pkg["probable_fix"] = (name,
                                           all_builds[name][i-1]["epoch"] or 0,
                                           all_builds[name][i-1]["version"],
                                           all_builds[name][i-1]["release"])

                    self._save_probable_fix(db, problem, db_release,
                                            pkg["probable_fix"],
                                            probably_fixed_since)
                    self.log_debug("  Probably fixed for {0} days.".format(
                        (datetime.now() - probably_fixed_since).days))
                    probably_fixed_total += 1
                else:
                    self._save_probable_fix(db, problem, db_release, None)
                    self.log_debug("  Not fixed.")

            db.session.flush()
            if problems_in_release > 0:
                self.log_info("{0}% of problems in this release probably fixed.".format(
                    (probably_fixed_total * 100) // problems_in_release))
            else:
                self.log_info("No problems found in this release.")

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys(multiple=True)
        parser.add_opsys_release(multiple=True)
