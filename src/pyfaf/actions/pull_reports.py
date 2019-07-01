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

import json
import os
import pickle
import urllib.error
import urllib.request
import uuid

from pyfaf.actions import Action
from pyfaf.common import ensure_dirs, FafError


class PullReports(Action):
    name = "pull-reports"

    KNOWN_FILE_NAME = "pull.pickle"

    def __init__(self):
        super(PullReports, self).__init__()

        self.master = None
        self.basedir = None
        self.load_config_to_self("master", ["pullreports.master"],
                                 "https://retrace.fedoraproject.org/faf")
        self.load_config_to_self("basedir", ["ureport.directory"],
                                 "/var/spool/faf")

        self.known_file = os.path.join(self.basedir, "reports",
                                       PullReports.KNOWN_FILE_NAME)
        self.incoming_dir = os.path.join(self.basedir, "reports", "incoming")
        try:
            ensure_dirs([self.incoming_dir])
        except FafError:
            self.log_error("Required directories can't be created")
            raise

    def _load_known(self):
        if not os.path.isfile(self.known_file):
            self.known = set()
            self._full_pickle = {}
            return

        with open(self.known_file, "rb") as f:
            self._full_pickle = pickle.load(f)

        self.known = self._full_pickle.get(self.master, set())

    def _save_known(self):
        self._full_pickle[self.master] = self.known
        tmpfilename = "{0}.tmp".format(self.known_file)
        with open(tmpfilename, "wb") as f:
            pickle.dump(self._full_pickle, f)

        os.rename(tmpfilename, self.known_file)

    def _list_reports(self):
        url = "{0}/reports".format(self.master)

        try:
            response = urllib.request.urlopen(url)
        except urllib.error.URLError as ex:
            self.log_warn("Unable to open URL '{0}': {1}".format(url, str(ex)))
            return []

        if response.getcode() != 200:
            self.log_warn("Unable to get reports: Unexpected HTTP response code {0}"
                            .format(response.getcode()))
            return []

        try:
            return json.load(response)
        except Exception as ex: # pylint: disable=broad-except
            self.log_warn("Unable to load report list: {0}".format(str(ex)))
            return []
        finally:
            response.close()

    def _get_report(self, report_id):
        url = "{0}/report/{1}".format(self.master, report_id)

        try:
            response = urllib.request.urlopen(url)
        except urllib.error.URLError as ex:
            self.log_warn("Unable to open URL '{0}': {1}".format(url, str(ex)))
            return None

        if response.getcode() != 200:
            self.log_warn("Unable to get report #{0}: Unexpected HTTP response code {1}"
                            .format(report_id, response.getcode()))
            return None

        try:
            return response.read()
        except Exception as ex: # pylint: disable=broad-except
            self.log_warn("Unable to get report #{0}: {1}"
                          .format(report_id, str(ex)))
            return None
        finally:
            response.close()

    def run(self, cmdline, db):
        if cmdline.master is not None:
            self.master = cmdline.master

        # Load set of reports we have already downloaded from this master
        self._load_known()

        self.log_info("Pulling reports from {0}".format(self.master))

        reports = set(self._list_reports()) - self.known
        if not reports:
            self.log_info("No reports found")
            return 0

        pulled = 0
        try:
            for i, report in enumerate(sorted(reports)):
                self.log_debug("[{0} / {1}] Pulling {2}"
                               .format(i, len(reports), report))
                ureport = self._get_report(report)
                if ureport is None:
                    continue

                # We prefer that the incoming report be named the same as on the master
                filename = os.path.join(self.incoming_dir, report)
                # If a report with the same name already exists directory, keep
                # generating a name at random until one that is available is found
                while os.path.isfile(filename):
                    filename = os.path.join(self.incoming_dir, uuid.uuid4().hex)

                with open(filename, "wb") as f:
                    f.write(ureport)

                self.log_debug("Saved to {0}".format(filename))
                self.known.add(report)
                pulled += 1
        finally:
            self._save_known()
            self.log_info("Successfully pulled {0} new reports".format(pulled))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("-m", "--master", default=None,
                            help="Master server to sync")
