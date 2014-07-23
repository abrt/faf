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


import koji
import json
from datetime import datetime
from pyfaf.actions import Action
from pyfaf.queries import (get_crashed_unknown_package_nevr_for_report,
                           get_crashed_package_for_report, get_problems)


class MarkProbablyFixed(Action):
    name = "mark-probably-fixed"

    def __init__(self):
        super(MarkProbablyFixed, self).__init__()
        self.load_config_to_self("build_aging_days",
                                 ["mark-probably-fixed.build-aging-days"],
                                 7, callback=int)
        self.load_config_to_self("koji_url",
                                 ["mark-probably-fixed.koji-url"], None)
        self.load_config_to_self("koji_tag",
                                 ["mark-probably-fixed.koji-tag"], None)

    def run(self, cmdline, db):
        """
        Mark a problem probably fixed if there is a new build of the problem's
        affected package, for which no crash reports have come in.
        """

        if cmdline.koji_json:
            self.log_info("Loading newest builds from file...")
            with open(cmdline.koji_json) as json_file:
                koji_builds = json.load(json_file)
        else:
            self.log_info("Getting newest builds from Koji...")
            session = koji.ClientSession(self.koji_url)
            koji_builds = session.listTagged(tag=self.koji_tag, inherit=True)

        newest_builds = {}
        all_builds = {}
        now = datetime.now()
        for build in koji_builds:
            age = now - datetime.strptime(build["completion_time"],
                                          "%Y-%m-%d %H:%M:%S.%f")
            # If a hot new build comes out, we need to wait a certain period of
            # time for people to use it before we can make conclusions about it
            # being a probable fix.
            if age.days >= self.build_aging_days:
                if build["name"] not in newest_builds:
                    newest_builds[build["name"]] = build

                if build["name"] not in all_builds:
                    all_builds[build["name"]] = [build, ]
                else:
                    all_builds[build["name"]].append(build)

        probably_fixed_total = 0
        problem_counter = 0
        problems = get_problems(db)
        for problem in problems:
            problem_counter += 1
            self.log_info("Processing problem {0}/{1}:"
                          .format(problem_counter, len(problems)))
            affected_newest = {}
            affected_not_found = False
            # For all the reports, we need the affected packages and their
            # newest versions.
            for report in problem.reports:
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
                        if affected[1:] > affected_newest[affected[0]]['nevr'][1:]:
                            affected_newest[affected[0]]['nevr'] = affected
                    else:
                        affected_newest[affected[0]] = {
                            'reports': [report, ],
                            'nevr': affected
                        }

            if affected_not_found:
                # Affected package of one of the reports was not found.
                # We can't make any conclusions.
                self.log_info(" Affected package not found.")
                problem.probably_fixed_since = None
                db.session.add(problem)
                for report in problem.reports:
                    report.probable_fix = None
                    db.session.add(report)
                continue

            probably_fixed_since = datetime.fromtimestamp(0)
            probably_fixed = True
            for pkg in affected_newest.values():
                # We need all the affected packages to have probable fixes in
                # order to mark the problem fixed.
                name = pkg['nevr'][0]
                newest_build = newest_builds.get(name, False)
                if newest_build:
                    newest_evr = (newest_build["epoch"] or 0,
                                  newest_build["version"],
                                  newest_build["release"])
                if newest_build and newest_evr > pkg['nevr'][1:]:
                    # Newest available build is newer than the newest version
                    # of the affected package. Now find the oldest such
                    # probable fix.
                    i = 0
                    while i < len(all_builds[name]) and \
                        (all_builds[name][i]["epoch"] or 0,
                            all_builds[name][i]["version"],
                            all_builds[name][i]["release"]) > pkg['nevr'][1:]:
                        i += 1
                    completion_time = datetime.strptime(
                        all_builds[name][i-1]["completion_time"],
                        "%Y-%m-%d %H:%M:%S.%f")
                    probably_fixed_since = max(completion_time,
                                               probably_fixed_since)
                    pkg['probable_fix'] = all_builds[name][i-1]['nvr']
                else:
                    probably_fixed = False
                    break

            if probably_fixed:
                problem.probably_fixed_since = probably_fixed_since
                probably_fixed_total += 1
                db.session.add(problem)
                for pkg in affected_newest.values():
                    for report in pkg['reports']:
                        report.probable_fix = pkg['probable_fix']
                        db.session.add(report)
                self.log_info("  Probably fixed for {0} days.".format(
                    (datetime.now() - problem.probably_fixed_since).days))
            else:
                problem.probably_fixed_since = None
                for report in problem.reports:
                    report.probable_fix = None
                    db.session.add(report)
                db.session.add(problem)
                self.log_info("  Not fixed.")

        db.session.flush()
        self.log_info("{0}% of problems probably fixed.".format(
            (probably_fixed_total * 100) / len(problems)))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--koji-json",
                            help="Get builds from specified file instead of Koji")
