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
from pyfaf.storage.errata import Erratum
from pyfaf.utils.parse import str2bool
from pyfaf.utils.kerberos import kinit

ERRATA_URL = "https://errata.devel.redhat.com/filter/5.json?page={0}"


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
            print(self.principal_name)
            print(self.keytab_filename)
            kinit(self.principal_name, self.keytab_filename)

        self.load_config_to_self("verify_ssl",
                                 ["kerberos.verifyssl"],
                                 False, callback=str2bool)
        self.log_info("Querying Red Hat Errata Tool...")
        page = 1
        data = []
        while page == 1 or len(data) > 0:
            url = ERRATA_URL.format(page)
            response = requests.get(url, auth=HTTPKerberosAuth(),
                                    verify=self.verify_ssl)

            data = json.loads(response.content)
            for erratum in data:
                self.log_info(u"{0} {1} {2}".format(erratum[u'id'],
                                                    erratum[u'advisory_name'],
                                                    erratum[u'synopsis']))
                db_erratum = Erratum()
                db_erratum.id = int(erratum[u'id'])
                db_erratum.advisory_name = erratum[u'advisory_name']
                db_erratum.synopsis = erratum[u'synopsis']
                db.session.merge(db_erratum)

            db.session.flush()

            self.log_info("Page {0}: {1} errata". format(page, len(data)))
            page += 1

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--no-kinit", action="store_true", default=False,
                            help="do not use internal kinit")