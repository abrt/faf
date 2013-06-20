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

import os
import json
import datetime

from pyfaf.action import Action
from pyfaf.common import FafError, ensure_dirs
from pyfaf.ureport import validate, save


class SaveReports(Action):
    name = "save-reports"

    dirname_reports = "reports"
    dirname_attachments = "attachments"
    dirname_incoming = "incoming"
    dirname_saved = "saved"
    dirname_deferred = "deferred"

    def __init__(self):
        super(SaveReports, self).__init__()

        basedir_keys = ["ureport.directory", "report.spooldirectory"]
        self.load_config_to_self("basedir", basedir_keys, "/var/spool/faf/")

        # Instance of 'SaveReports' has no 'basedir' member
        # pylint: disable-msg=E1101

        self.dir_report = os.path.join(self.basedir,
                                       SaveReports.dirname_reports)
        self.dir_report_incoming = os.path.join(self.dir_report,
                                                SaveReports.dirname_incoming)
        self.dir_report_saved = os.path.join(self.dir_report,
                                             SaveReports.dirname_saved)
        self.dir_report_deferred = os.path.join(self.dir_report,
                                                SaveReports.dirname_deferred)

        self.dir_attach = os.path.join(self.basedir,
                                       SaveReports.dirname_attachments)
        self.dir_attach_incoming = os.path.join(self.dir_attach,
                                                SaveReports.dirname_incoming)
        self.dir_attach_saved = os.path.join(self.dir_attach,
                                             SaveReports.dirname_saved)
        self.dir_attach_deferred = os.path.join(self.dir_attach,
                                                SaveReports.dirname_deferred)

        try:
            ensure_dirs([self.dir_report_incoming, self.dir_report_saved,
                         self.dir_report_deferred, self.dir_attach_incoming,
                         self.dir_attach_saved, self.dir_attach_deferred])
        except FafError as ex:
            self.log_error("Required directories can't be created: {0}"
                           .format(str(ex)))
            raise

    def _move_report_to_saved(self, filename):
        path_from = os.path.join(self.dir_report_incoming, filename)
        path_to = os.path.join(self.dir_report_saved, filename)

        self.log_debug("Moving file '{0}' to saved".format(path_from))

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to saved: {1}"
                          .format(path_from, str(ex)))

    def _move_report_to_deferred(self, filename):
        path_from = os.path.join(self.dir_report_incoming, filename)
        path_to = os.path.join(self.dir_report_deferred, filename)

        self.log_debug("Moving file '{0}' to deferred".format(path_from))

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to deferred: {1}"
                          .format(path_from, str(ex)))

    def _move_attachment_to_saved(self, filename):
        path_from = os.path.join(self.dir_attach_incoming, filename)
        path_to = os.path.join(self.dir_attach_saved, filename)

        self.log_debug("Moving file '{0}' to saved".format(path_from))

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to saved: {1}"
                          .format(path_from, str(ex)))

    def _move_attachment_to_deferred(self, filename):
        path_from = os.path.join(self.dir_attach_incoming, filename)
        path_to = os.path.join(self.dir_attach_deferred, filename)

        self.log_debug("Moving file '{0}' to deferred".format(path_from))

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to deferred: {1}"
                          .format(path_from, str(ex)))

    def _save_reports(self, db):
        self.log_info("Saving reports")

        report_filenames = os.listdir(self.dir_report_incoming)

        i = 0
        for fname in sorted(report_filenames):
            i += 1

            filename = os.path.join(self.dir_report_incoming, fname)
            self.log_info("[{0} / {1}] Processing file '{2}'"
                          .format(i, len(report_filenames), filename))

            try:
                with open(filename, "r") as fil:
                    ureport = json.load(fil)
            except (OSError, ValueError) as ex:
                self.log_warn("Failed to load uReport: {0}".format(str(ex)))
                self._move_report_to_deferred(fname)
                continue

            try:
                validate(ureport)
            except FafError as ex:
                self.log_warn("uReport is invalid: {0}".format(str(ex)))
                self._move_report_to_deferred(fname)
                continue

            mtime = os.path.getmtime(filename)
            timestamp = datetime.datetime.fromtimestamp(mtime)

            try:
                save(db, ureport, timestamp=timestamp)
            except FafError as ex:
                self.log_warn("Failed to save uReport: {0}".format(str(ex)))
                self._move_report_to_deferred(fname)
                continue

            self._move_report_to_saved(fname)

    def _save_attachments(self, db):
        self.log_info("Saving attachments")

        attachment_filenames = os.listdir(self.dir_attach_incoming)

        i = 0
        for fname in sorted(attachment_filenames):
            i += 1

            filename = os.path.join(self.dir_attach_incoming, fname)
            self.log_info("[{0} / {1}] Processing file '{2}'"
                          .format(i, len(attachment_filenames), filename))

            try:
                with open(filename, "r") as fil:
                    attachment = json.load(fil)
            except (OSError, ValueError) as ex:
                self.log_warn("Failed to load attachment: {0}".format(str(ex)))
                self._move_attachment_to_deferred(fname)
                continue

            # ToDo: implement validating & saving attachments

            self._move_attachment_to_saved(fname)

    def run(self, cmdline, db):
        if not cmdline.no_reports:
            self._save_reports(db)

        if not cmdline.no_attachments:
            self._save_attachments(db)

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--no-reports", action="store_true", default=False,
                            help="do not process reports")
        parser.add_argument("--no-attachments", action="store_true",
                            default=False, help="do not process attachments")
