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

from pyfaf.actions import Action
from pyfaf.storage.report import ReportPackage, ReportUnknownPackage
from pyfaf.queries import (get_packages_and_their_reports_unknown_packages,
                           get_report_package_for_report_id)


class MatchUnknownPackages(Action):
    name = "match-unknown-packages"

    def __init__(self):
        super(MatchUnknownPackages, self).__init__()

    def run(self, cmdline, db):
        self.log_info("Querying reports with unknown packages...")

        reports_pkgs = get_packages_and_their_reports_unknown_packages(db)
        for (package_unknown_report, report_unknown_package) in reports_pkgs:
            self.log_info("Found package {0} belonging to ReportUnknownPackage"
                          " id {1}".format(str(package_unknown_report),
                                           report_unknown_package.id))

            rid = report_unknown_package.report_id
            existing_report_package = get_report_package_for_report_id(db, rid)
            if existing_report_package is not None:
                # Delete ReportUnknownPackage
                # if corresponding ReportPackage exists
                existing_report_package.count += report_unknown_package.count
                db.session.delete(report_unknown_package)

                db.session.flush()
                self.log_info("Existing ReportPackage found, "
                              "ReportUnknownPackage deleted.")

            else:
                # Corresponding ReportPackage doesn't exist
                report_package = ReportPackage(
                    report_id=report_unknown_package.report_id,
                    type=report_unknown_package.type,
                    installed_package_id=package_unknown_report.id,
                    count=report_unknown_package.count)

                db.session.add(report_package)
                db.session.delete(report_unknown_package)

                db.session.flush()
                self.log_info("Created new ReportPackage, "
                              "ReportUnknownPackage deleted.")
