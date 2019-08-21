# Copyright (C) 2019  ABRT Team
# Copyright (C) 2019  Red Hat, Inc.
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
from pyfaf.opsys import systems
import pyfaf.storage as st
from pyfaf.queries import (get_opsys_by_name,
                           get_osrelease,
                           get_empty_problems,
                           get_builds_by_opsysrelease_id,
                           delete_mantis_bugzilla,
                           delete_bugzilla)


class ReleaseDelete(Action):
    name = "releasedel"

    def run(self, cmdline, db):
        if cmdline.opsys is None:
            self.log_error("You must specify the operating system.")
            return 1

        if cmdline.opsys_release is None:
            self.log_error("You must specify the operating system release.")
            return 1

        if cmdline.opsys not in systems:
            self.log_error("Operating system '%s' does not exist", cmdline.opsys)
            return 1

        opsys = systems[cmdline.opsys]
        db_opsys = get_opsys_by_name(db, opsys.nice_name)
        if db_opsys is None:
            self.log_error("Operating system '%s' is not installed", opsys.nice_name)
            return 1

        db_release = get_osrelease(db, opsys.nice_name, cmdline.opsys_release)
        if db_release is None:
            self.log_info("Release '%s %s' is not defined", opsys.nice_name, cmdline.opsys_release)
            return 1

        self.log_info("Deleting release '{0} {1}'"
                      .format(opsys.nice_name, cmdline.opsys_release))

        db_release_id = db_release.id

        self._delete_mantis_bugs(db, db_release_id)
        self._delete_bugzilla_bugs(db, db_release_id)
        self._delete_release_builds(db, db_release_id)
        self._delete_release_repos(db, db_release_id)
        self._delete_release_reports(db, db_release_id)
        self._delete_release_problems(db, db_release_id)

        (db.session.query(st.OpSysReleaseComponent)
         .filter(st.OpSysReleaseComponent.opsysreleases_id == db_release_id)
         .delete(False))

        db.session.delete(db_release)
        db.session.flush()

        self.log_info("Done")
        return 0

    def _delete_mantis_bugs(self, db, opsysrelease_id):
        self.log_info("Removing Mantis Bugzillas")
        all_mantis = (db.session.query(st.MantisBug)
                      .filter(st.MantisBug.opsysrelease_id == opsysrelease_id)
                      .all())
        self.log_info("Mantis Bugzillas found: {0}".format(len(all_mantis)))

        for mgz in all_mantis:
            mgz_id = mgz.id
            self.log_debug("Deleting mantis bugzilla #%d", mgz_id)
            delete_mantis_bugzilla(db, mgz_id)

    def _delete_bugzilla_bugs(self, db, opsysrelease_id):
        self.log_info("Removing Bugzillas")
        all_bugzillas = (db.session.query(st.BzBug)
                         .filter(st.BzBug.opsysrelease_id == opsysrelease_id)
                         .all())
        self.log_info("Bugzillas found: {0}".format(len(all_bugzillas)))

        for bgz in all_bugzillas:
            bgz_id = bgz.id
            self.log_debug("Deleting bugzilla #%d", bgz_id)
            delete_bugzilla(db, bgz_id)

    def _delete_release_builds(self, db, opsysrelease_id):
        self.log_info("Removing builds")
        # find all builds, that are assigned to this opsysrelease but none other
        # architecture is missed out intentionally
        all_builds = get_builds_by_opsysrelease_id(db, opsysrelease_id)

        # delete all records, where the opsysrelease.id is present
        query = (db.session.query(st.BuildOpSysReleaseArch)
                 .filter(st.BuildOpSysReleaseArch.opsysrelease_id == opsysrelease_id))

        links_deleted = query.delete(False)
        self.log_info("Links to be removed: {0}".format(links_deleted))

        # delete all builds and packages from them
        for build in all_builds:
            for pkg in (db.session.query(st.Package)
                        .filter(st.Package.build_id == build.build_id)
                        .all()):
                self.delete_package(pkg)

    def _delete_release_repos(self, db, opsysrelease_id):
        self.log_info("Removing repositories")
        all_oprelrepos = (db.session.query(st.OpSysReleaseRepo)
                          .filter(st.OpSysReleaseRepo.opsysrelease_id == opsysrelease_id)
                          .all())
        self.log_info("Repositories found: {0}".format(len(all_oprelrepos)))

        for oprelrepo in all_oprelrepos:
            repo = (db.session.query(st.Repo)
                    .filter(st.Repo.id == oprelrepo.repo_id)
                    .first())

            if not repo:
                continue

            self.log_debug("Removing repository '%s'", repo.name)

            for url in repo.url_list:
                db.session.delete(url)

            db.session.delete(repo)

        db.session.flush()

    def _delete_release_reports(self, db, opsysrelease_id):
        self.log_info("Removing reports")
        (db.session.query(st.ReportReleaseDesktop)
         .filter(st.ReportReleaseDesktop.release_id == opsysrelease_id)
         .delete(False))

        (db.session.query(st.ReportHistoryDaily)
         .filter(st.ReportHistoryDaily.opsysrelease_id == opsysrelease_id)
         .delete(False))

        (db.session.query(st.ReportHistoryWeekly)
         .filter(st.ReportHistoryWeekly.opsysrelease_id == opsysrelease_id)
         .delete(False))

        (db.session.query(st.ReportHistoryMonthly)
         .filter(st.ReportHistoryMonthly.opsysrelease_id == opsysrelease_id)
         .delete(False))

        (db.session.query(st.ReportOpSysRelease)
         .filter(st.ReportOpSysRelease.opsysrelease_id == opsysrelease_id)
         .delete(False))

        # find and delete all reports, that are not assigned to any opsysreleases
        report_query = (db.session.query(st.Report)
                        .filter(~db.session.query()
                                .exists()
                                .where(st.ReportOpSysRelease.report_id == st.Report.id)))

        reports_deleted = report_query.delete(False)
        self.log_info("Reports found: {0}".format(reports_deleted))

        # expire session objects - needed after ON DELETE deletion from report and related tables
        db.session.expire_all()

    def _delete_release_problems(self, db, opsysrelease_id):
        self.log_info("Removing problems")
        (db.session.query(st.ProblemOpSysRelease)
         .filter(st.ProblemOpSysRelease.opsysrelease_id == opsysrelease_id)
         .delete(False))

        yield_num = 1000
        problems_found = 0

        empty_problems = get_empty_problems(db, yield_num)

        count = 0
        for problem in empty_problems:
            count += 1
            self.log_debug("Removing empty problem #%d", problem.id)
            db.session.delete(problem)

            if count > yield_num:
                problems_found += count
                db.session.flush()
                count = 0

        if count != 0:
            problems_found += count
            db.session.flush()

        self.log_info("Empty problems found: {0}".format(problems_found))

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys(helpstr="operating system")
        parser.add_opsys_release(helpstr="operating system release")
