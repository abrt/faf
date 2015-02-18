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

from pyfaf.actions import Action
from pyfaf.common import FafError
from pyfaf.problemtypes import problemtypes
from pyfaf.storage import Symbol
from pyfaf.queries import get_symbol_by_name_path


class RetraceRemote(Action):
    name = "retrace-remote"

    def __init__(self):
        super(RetraceRemote, self).__init__()
        self.load_config_to_self("remote_url", ["retrace_remote.remote_url"],
            "http://localhost/faf2/symbol_transfer/get_symbol/")
        self.load_config_to_self("auth_key", ["retrace_remote.auth_key"], "")

    def run(self, cmdline, db):
        if len(cmdline.problemtype) < 1:
            ptypes = problemtypes.keys()
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

            db_ssources = problemplugin.get_ssources_for_retrace(db)
            if len(db_ssources) < 1:
                continue

            i = 0
            for db_ssource in db_ssources:
                i += 1
                self.log_info("Processing symbol {0}/{1}"
                              .format(i, len(db_ssources)))
                params = {
                    "build_id": db_ssource.build_id,
                    "path": db_ssource.path,
                    "offset": db_ssource.offset,
                    "type": ptype,
                    "create_symbol_auth": self.auth_key,
                }
                r = requests.get(self.remote_url, params=params)
                if r.status_code == requests.codes.ok:
                    self.log_info("Symbol found.")
                    data = r.json()
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
                        db_symbol = Symbol()
                        db.session.add(db_symbol)
                    db_symbol.name = symbol["name"]
                    db_symbol.nice_name = symbol["nice_name"]
                    db_symbol.normalized_path = symbol["normalized_path"]

                    db_ssource.symbol = db_symbol

                    db.session.flush()
                    self.log_info("Symbol saved.")

                elif r.status_code == 202:
                    self.log_info("Symbol created for later retracing.")
                else:
                    self.log_info("Symbol not found.")

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
