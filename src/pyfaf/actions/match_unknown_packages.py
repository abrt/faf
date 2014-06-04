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

import urllib2
import itertools

#from pyfaf.rpm import store_rpm_deps
#from pyfaf.repos import repo_types
from pyfaf.actions import Action
from pyfaf.storage.opsys import Build, Package
from pyfaf.storage.report import ReportPackage, ReportUnknownPackage
from pyfaf.queries import get_packages_and_their_reports_unknown_packages
#from pyfaf.utils.decorators import retry


class MatchUnknownPackages(Action):
    name = "match-unknown-packages"

    def __init__(self):
        super(MatchUnknownPackages, self).__init__()

    def run(self, cmdline, db):
        # import logging
        # logging.basicConfig()
        # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        #db.session.query(ReportUnknownPackage)
        self.log_info("Querying reports with unknown packages...")
        
        for (package_unknown_report, report_unknown_package) in get_packages_and_their_reports_unknown_packages(db):
            self.log_info("Found package {0} belonging to ReportUnknownPackage id {1}".format(str(package_unknown_report), report_unknown_package.id))            
            existing_report_package = db.session.query(ReportPackage).filter(ReportPackage.report_id == report_unknown_package.report_id).first()
            if existing_report_package is not None: # Delete ReportUnknownPackage if corresponding ReportPackage exists                
                existing_report_package.count += report_unknown_package.count
                db.session.delete(report_unknown_package)
            
                db.session.flush()
                self.log_info("Existing ReportPackage found, ReportUnknownPackage deleted.")
            
            else: # Corresponding ReportPackage doesn't exist
                report_package = ReportPackage(
                    report_id = report_unknown_package.report_id,
                    type = report_unknown_package.type,
                    installed_package_id = package_unknown_report.id,
                    count = report_unknown_package.count,
                    )
                db.session.add(report_package)
                db.session.delete(report_unknown_package)

                db.session.flush()
                self.log_info("Created new ReportPackage, ReportUnknownPackage deleted.")
