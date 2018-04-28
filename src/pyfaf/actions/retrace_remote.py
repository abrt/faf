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

import requests
import json

from pyfaf.actions import Action
from pyfaf.problemtypes import problemtypes
from pyfaf.storage import Symbol
from pyfaf.queries import get_symbol_by_name_path
from six.moves import range


class RetraceRemote(Action):
    name = "retrace-remote"

    def __init__(self):
        super(RetraceRemote, self).__init__()
        self.load_config_to_self("remote_url", ["retrace_remote.remote_url"],
                                 "http://localhost/faf/symbol_transfer/get_symbol/")
        self.load_config_to_self("auth_key", ["retrace_remote.auth_key"], "")

    def run(self, cmdline, db):
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
                db, yield_per=cmdline.batch)
            if len(db_ssources) < 1:
                continue

            i = 0
            batch = []
            db_batch = []
            for db_ssource in db_ssources:
                i += 1
                self.log_info("Processing symbol {0}/{1}"
                              .format(i, len(db_ssources)))
                req_data = {
                    "build_id": db_ssource.build_id,
                    "path": db_ssource.path,
                    "offset": db_ssource.offset,
                    "type": ptype,
                }
                batch.append(req_data)
                db_batch.append(db_ssource)

                if len(batch) >= cmdline.batch or i == len(db_ssources):
                    self.log_info("Sending request...")
                    r = requests.post(
                        self.remote_url,
                        data=json.dumps(batch),
                        params={"create_symbol_auth": self.auth_key},
                        headers={"content-type": "application/json"}
                    )

                    if r.status_code == requests.codes.ok:
                        res_data = r.json()
                        if len(res_data) != len(batch):
                            self.log_warn("Response length mismatch.")
                            batch = []
                            db_batch = []
                            continue

                        new_db_symbols = {}
                        for j in range(len(res_data)):
                            data = res_data[j]
                            if data.get("error", False):
                                self.log_info(data["error"])
                                continue
                            db_ssource = db_batch[j]
                            ssource = data["SymbolSource"]
                            symbol = data["Symbol"]
                            db_ssource.build_id = ssource["build_id"]
                            db_ssource.path = ssource["path"]
                            db_ssource.offset = ssource["offset"]
                            db_ssource.func_offset = ssource["func_offset"]
                            db_ssource.hash = ssource["hash"]
                            db_ssource.source_path = ssource["source_path"]
                            db_ssource.line_number = ssource["line_number"]

                            db_symbol = get_symbol_by_name_path(db, symbol["name"],
                                                                symbol["normalized_path"])
                            if db_symbol is None:
                                db_symbol = new_db_symbols.get((symbol["name"],
                                                                symbol["normalized_path"]),
                                                               None)
                            if db_symbol is None:
                                db_symbol = Symbol()
                                db.session.add(db_symbol)
                                new_db_symbols[(symbol["name"],
                                                symbol["normalized_path"])] = db_symbol

                            db_symbol.name = symbol["name"]
                            db_symbol.nice_name = symbol["nice_name"]
                            db_symbol.normalized_path = symbol["normalized_path"]

                            db_ssource.symbol = db_symbol
                            self.log_info("Symbol saved.")

                        db.session.flush()

                    batch = []
                    db_batch = []

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
        parser.add_argument("--batch", type=int,
                            default=1,
                            help="Batch request.")
