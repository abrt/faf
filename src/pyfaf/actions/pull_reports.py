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

import sys
if sys.version_info.major == 2:
#Python 2
    import cPickle as pickle
else:
#Python 3+
    import pickle

import json
import os
import urllib2
import uuid
from pyfaf.actions import Action
from pyfaf.common import ensure_dirs, FafError


class PullReports(Action):
    name = "pull-reports"

    KNOWN_FILE_NAME = "pull.pickle"

    def __init__(self):
        super(PullReports, self).__init__()

        self.load_config_to_self("master", ["pullreports.master"],
                                 "https://retrace.fedoraproject.org/faf")
        self.load_config_to_self("basedir", ["ureport.directory"],
                                 "/var/spool/faf")

        self.known_file = os.path.join(self.basedir, "reports",
                                       PullReports.KNOWN_FILE_NAME)
        self._load_known()

        self.incoming_dir = os.path.join(self.basedir, "reports", "incoming")
        try:
            ensure_dirs([self.incoming_dir])
        except FafError as ex:
            self.log_error("Required directories can't be created")
            raise

    def _load_known(self):
        if not os.path.isfile(self.known_file):
            self.known = set()
            self._full_pickle = {}
            return

        with open(self.known_file, "r") as f:
            self._full_pickle = pickle.load(f)

        if self.master not in self._full_pickle:
            self.known = set()
            return

        self.known = self._full_pickle[self.master]

    def _save_known(self):
        self._full_pickle[self.master] = self.known
        tmpfilename = "{0}.tmp".format(self.known_file)
        with open(tmpfilename, "w") as f:
            pickle.dump(self._full_pickle, f)

        os.rename(tmpfilename, self.known_file)

    def _list_reports(self):
        url = "/".join([self.master, "reports"])

        try:
            u = urllib2.urlopen(url)
        except urllib2.URLError as ex:
            self.log_warn("Unable to open URL '{0}': {1}".format(url, str(ex)))
            return []

        try:
            report_list = u.read()

            if u.getcode() != 200:
                self.log_warn("Unable to get reports: Unexpected code {0}"
                              .format(u.getcode()))
                return []

            return json.loads(report_list)
        except Exception as ex:
            self.log_warn("Unable to load report list: {0}".format(str(ex)))
            return []
        finally:
            u.close()

    def _get_report(self, name):
        url = "/".join([self.master, "report", name])

        try:
            u = urllib2.urlopen(url)
        except urllib2.URLError as ex:
            self.log_warn("Unable to open URL '{0}': {1}".format(url, str(ex)))
            return None

        try:
            ureport = u.read()

            if u.getcode() != 200:
                self.log_warn("Unable to get report #{0}: Unexpected code {1}"
                              .format(name, u.getcode()))
                return None

            return ureport
        except:
            self.log_warn("Unable to get report #{0}: {1}"
                          .format(name, str(ex)))
            return None
        finally:
            u.close()

        filename = os.path.join(self.incoming_dir, name)
        while os.path.isfile(filename):
            filename = os.path.join(self.incoming_dir, uuid.uuid4().get_hex())

        with open(filename, "w") as f:
            f.write(ureport)

    def run(self, cmdline, db):
        if cmdline.master is not None:
            self.master = cmdline.master
            self._load_known()

        self.log_info("Pulling reports from {0}".format(self.master))

        reports = set(self._list_reports()) - self.known
        if len(reports) < 1:
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

                filename = os.path.join(self.incoming_dir, report)
                while os.path.isfile(filename):
                    filename = os.path.join(self.incoming_dir, uuid.uuid4().get_hex())

                with open(filename, "w") as f:
                    f.write(ureport)

                self.log_debug("Written to {0}".format(filename))
                self.known.add(report)
                pulled += 1
        finally:
            self._save_known()

        self.log_info("Successfully pulled {0} new reports".format(pulled))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("-m", "--master", default=None,
                            help="Master server to sync")
