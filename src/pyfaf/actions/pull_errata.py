# -*- encoding: utf-8 -*-
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
import requests
from requests_kerberos import HTTPKerberosAuth
import json
from pyfaf.storage.errata import Erratum, ErratumBug
from pyfaf.utils.parse import str2bool
from pyfaf.utils.kerberos import kinit
from pyfaf.queries import get_erratum_bugs_for_erratum


class PullErrata(Action):
    name = "pull-errata"

    def __init__(self):
        super(PullErrata, self).__init__()

    def run(self, cmdline, db):
        if not cmdline.no_kinit:
            self.load_config_to_self("principal_name",
                                     ["kerberos.principalname"])
            self.load_config_to_self("keytab_filename",
                                     ["kerberos.keytabfilename"])
            kinit(self.principal_name, self.keytab_filename)

        self.load_config_to_self("verify_ssl",
                                 ["kerberos.verifyssl"],
                                 False, callback=str2bool)
        self.load_config_to_self("errata_url",
                                 ["errata.erratatoolurl"])
        self.load_config_to_self("errata_bugs_url",
                                 ["errata.erratatooladvisorybugsurl"])
        self.errata_url = self.errata_url+"?page={0}"
        self.log_info("Querying Errata Tool...")
        page = 1
        data = []
        while page == 1 or len(data) > 0:
            url = self.errata_url.format(page)
            response = requests.get(url, auth=HTTPKerberosAuth(),
                                    verify=self.verify_ssl)

            data = json.loads(response.content)
            for erratum in data:
                self.log_info(u"{0} {1} {2}".format(erratum[u"id"],
                                                    erratum[u"advisory_name"],
                                                    erratum[u"synopsis"]))
                db_erratum = Erratum()
                db_erratum.id = int(erratum[u"id"])
                db_erratum.advisory_name = erratum[u"advisory_name"]
                db_erratum.synopsis = erratum[u"synopsis"]
                db_erratum = db.session.merge(db_erratum)

                bugs_url = self.errata_bugs_url.format(db_erratum.id)
                response_bug = requests.get(bugs_url, auth=HTTPKerberosAuth(),
                                            verify=self.verify_ssl)

                data_bug = json.loads(response_bug.content)
                erratum_bug_ids = set([err.bug_id for err in db_erratum.bugs])
                for bug in data_bug:
                    # TODO: only add [abrt] bugs?
                    bug_id = int(bug[u"id"])
                    if bug_id in erratum_bug_ids:
                        erratum_bug_ids.remove(bug_id)
                        self.log_info("Skipping existing bug {0} in erratum {1}"
                                      .format(bug_id, erratum[u"id"]))
                    else:
                        self.log_info("Adding bug {0} to erratum {1}"
                                      .format(bug_id, erratum[u"id"]))
                        db_erratum_bug = ErratumBug()
                        db_erratum_bug.erratum = db_erratum
                        db_erratum_bug.bug_id = bug_id
                        db.session.add(db_erratum_bug)

                if len(erratum_bug_ids) > 0:
                    self.log_info("Deleting {0} extra bugs for erratum {1}"
                                  .format(len(erratum_bug_ids), erratum[u"id"]))
                    (get_erratum_bugs_for_erratum(db, db_erratum.id,
                                                  erratum_bug_ids)
                        .delete(synchronize_session='fetch'))

            db.session.flush()

            self.log_info("Page {0} done: {1} errata processed"
                          .format(page, len(data)))
            page += 1

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--no-kinit", action="store_true", default=False,
                            help="do not use internal kinit")
