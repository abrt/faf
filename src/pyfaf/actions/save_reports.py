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
import time
import glob
import hashlib
import signal
import sys

from pyfaf.actions import Action
from pyfaf.common import FafError, ensure_dirs
from pyfaf.opsys import systems
from pyfaf.queries import get_unknown_opsys
from pyfaf.storage import UnknownOpSys
from pyfaf.ureport import save, save_attachment, validate, validate_attachment
from pyfaf.utils.parse import str2bool
from pyfaf.config import paths


class SaveReports(Action):
    name = "save-reports"

    def __init__(self):
        super(SaveReports, self).__init__()

        basedir_keys = ["ureport.directory", "report.spooldirectory"]
        self.basedir = None
        self.create_components = None
        self.load_config_to_self("basedir", basedir_keys, "/var/spool/faf/")

        self.load_config_to_self("create_components",
                                 ["ureport.createcomponents"],
                                 False, callback=str2bool)

        # Instance of 'SaveReports' has no 'basedir' member
        # pylint: disable-msg=E1101

        self.dir_report = paths["reports"]
        self.dir_report_incoming = paths["reports_incoming"]
        self.dir_report_saved = paths["reports_saved"]
        self.dir_report_deferred = paths["reports_deferred"]

        self.dir_attach = paths["attachments"]
        self.dir_attach_incoming = paths["attachments_incoming"]
        self.dir_attach_saved = paths["attachments_saved"]
        self.dir_attach_deferred = paths["attachments_deferred"]

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

        self.log_debug("Moving file '%s' to saved", path_from)

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to saved: {1}"
                          .format(path_from, str(ex)))

    def _move_reports_to_saved(self, filenames):
        for filename in filenames:
            self._move_report_to_saved(filename)

    def _move_report_to_deferred(self, filename):
        path_from = os.path.join(self.dir_report_incoming, filename)
        path_to = os.path.join(self.dir_report_deferred, filename)

        self.log_debug("Moving file '%s' to deferred", path_from)

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to deferred: {1}"
                          .format(path_from, str(ex)))

    def _move_reports_to_deferred(self, filenames):
        for filename in filenames:
            self._move_report_to_deferred(filename)

    def _move_attachment_to_saved(self, filename):
        path_from = os.path.join(self.dir_attach_incoming, filename)
        path_to = os.path.join(self.dir_attach_saved, filename)

        self.log_debug("Moving file '%s' to saved", path_from)

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to saved: {1}"
                          .format(path_from, str(ex)))

    def _move_attachment_to_deferred(self, filename):
        path_from = os.path.join(self.dir_attach_incoming, filename)
        path_to = os.path.join(self.dir_attach_deferred, filename)

        self.log_debug("Moving file '%s' to deferred", path_from)

        try:
            os.rename(path_from, path_to)
        except OSError as ex:
            self.log_warn("Can't move file '{0}' to deferred: {1}"
                          .format(path_from, str(ex)))

    def _save_unknown_opsys(self, db, opsys):
        name = opsys.get("name")
        version = opsys.get("version")

        self.log_warn("Unknown operating system: '{0} {1}'"
                      .format(name, version))

        db_unknown_opsys = get_unknown_opsys(db, name, version)
        if db_unknown_opsys is None:
            db_unknown_opsys = UnknownOpSys()
            db_unknown_opsys.name = name
            db_unknown_opsys.version = version
            db_unknown_opsys.count = 0
            db.session.add(db_unknown_opsys)

        db_unknown_opsys.count += 1
        db.session.flush()

    def _save_reports(self, db, pattern="*"):
        self.log_info("Saving reports")

        report_filenames = glob.glob(os.path.join(self.dir_report_incoming, pattern))

        for i, filename in enumerate(sorted(report_filenames), start=1):
            fname = os.path.basename(filename)
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

                if ("os" in ureport and
                        "name" in ureport["os"] and
                        ureport["os"]["name"] not in systems and
                        ureport["os"]["name"].lower() not in systems):
                    self._save_unknown_opsys(db, ureport["os"])

                self._move_report_to_deferred(fname)
                continue

            mtime = os.path.getmtime(filename)
            timestamp = datetime.datetime.fromtimestamp(mtime)

            try:
                save(db, ureport, create_component=self.create_components,
                     timestamp=timestamp)
            except FafError as ex:
                self.log_warn("Failed to save uReport: {0}".format(str(ex)))
                self._move_report_to_deferred(fname)
                continue

            self._move_report_to_saved(fname)

    def _save_reports_speedup(self, db):
        self.log_info("Saving reports (--speedup)")

        # This creates a lock file and only works on file modified between the
        # last lock file and this new lock file. This way a new process can
        # be run while the older is still running.

        now = time.time()
        lock_name = ".sr-speedup-{0}-{1}.lock".format(os.getpid(),
                                                      int(now))

        self.lock_filename = os.path.join(self.dir_report_incoming, lock_name)
        open(self.lock_filename, "w").close()
        os.utime(self.lock_filename, (int(now), int(now)))
        self.log_debug("Created lock %s", self.lock_filename)

        # Remove lock on SIGTERM and Ctrl-C
        def handle_term(_, __):
            self.log_debug("Signal caught, removing lock %s", self.lock_filename)
            os.remove(self.lock_filename)
            sys.exit(0)
        signal.signal(signal.SIGTERM, handle_term)
        signal.signal(signal.SIGINT, handle_term)

        locks = glob.glob(os.path.join(self.dir_report_incoming,
                                       ".sr-speedup-*.lock"))
        newest_older_ctime = 0
        for lock in locks:
            stat = os.stat(lock)
            if int(stat.st_ctime) > int(now) and not lock.endswith(lock_name):
                self.log_info("Newer lock found. Exiting.")
                os.remove(self.lock_filename)
                return
            if stat.st_ctime > newest_older_ctime and int(stat.st_ctime) < int(now):
                newest_older_ctime = stat.st_ctime

        report_filenames = []
        for fname in os.listdir(self.dir_report_incoming):
            stat = os.stat(os.path.join(self.dir_report_incoming, fname))
            if fname[0] != "." and stat.st_mtime > newest_older_ctime and stat.st_mtime <= now:
                report_filenames.append(fname)

        # We create a dict of SHA1 unique reports and then treat them as one
        # with appropriate count.

        reports = {}
        for i, fname in enumerate(sorted(report_filenames), start=1):
            filename = os.path.join(self.dir_report_incoming, fname)
            self.log_info("[{0} / {1}] Loading file '{2}'"
                          .format(i, len(report_filenames), filename))

            try:
                with open(filename, "rb") as fil:
                    stat = os.stat(filename)
                    contents = fil.read()
                    h = hashlib.sha1()
                    h.update(contents)
                    h.update(datetime.date.fromtimestamp(stat.st_mtime)
                             .isoformat().encode("utf-8"))
                    digest = h.digest()
                    if digest in reports:
                        reports[digest]["filenames"].append(fname)
                        if reports[digest]["mtime"] < stat.st_mtime:
                            reports[digest]["mtime"] = stat.st_mtime
                        self.log_debug("Duplicate")
                    else:
                        reports[digest] = {
                            "ureport": json.loads(contents),
                            "filenames": [fname],
                            "mtime": stat.st_mtime,
                        }
                        self.log_debug("Original")

            except (OSError, ValueError) as ex:
                self.log_warn("Failed to load uReport: {0}".format(str(ex)))
                self._move_report_to_deferred(fname)
                continue

        for i, unique in enumerate(reports.values(), start=1):
            self.log_info("[{0} / {1}] Processing unique file '{2}'"
                          .format(i, len(reports), unique["filenames"][0]))
            ureport = unique["ureport"]
            try:
                validate(ureport)
            except FafError as ex:
                self.log_warn("uReport is invalid: {0}".format(str(ex)))

                if ("os" in ureport and
                        "name" in ureport["os"] and
                        ureport["os"]["name"] not in systems and
                        ureport["os"]["name"].lower() not in systems):
                    self._save_unknown_opsys(db, ureport["os"])

                self._move_reports_to_deferred(unique["filenames"])
                continue

            mtime = unique["mtime"]
            timestamp = datetime.datetime.fromtimestamp(mtime)

            try:
                save(db, ureport, create_component=self.create_components,
                     timestamp=timestamp, count=len(unique["filenames"]))
            except FafError as ex:
                self.log_warn("Failed to save uReport: {0}".format(str(ex)))
                self._move_reports_to_deferred(unique["filenames"])
                continue

            self._move_reports_to_saved(unique["filenames"])

        self.log_debug("Removing lock %s", self.lock_filename)
        os.remove(self.lock_filename)

    def _save_attachments(self, db):
        self.log_info("Saving attachments")

        attachment_filenames = os.listdir(self.dir_attach_incoming)

        for i, fname in enumerate(sorted(attachment_filenames), start=1):
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

            try:
                validate_attachment(attachment)
            except FafError as ex:
                self.log_warn("Attachment is invalid: {0}".format(str(ex)))
                self._move_attachment_to_deferred(fname)
                continue

            try:
                save_attachment(db, attachment)
            except FafError as ex:
                self.log_warn("Failed to save attachment: {0}".format(str(ex)))
                self._move_attachment_to_deferred(fname)
                continue

            self._move_attachment_to_saved(fname)

    def run(self, cmdline, db):

        if cmdline.pattern and cmdline.speedup:
            self.log_error("Argument --pattern not allowed with --speedup.")
            return 1

        if not cmdline.no_reports:
            if cmdline.speedup:
                try:
                    self._save_reports_speedup(db)
                except:
                    self.log_debug("Uncaught exception. Removing lock %s", self.lock_filename)
                    os.remove(self.lock_filename)
                    raise
            elif cmdline.pattern:
                self._save_reports(db, cmdline.pattern)
            else:
                self._save_reports(db)

        if not cmdline.no_attachments:
            self._save_attachments(db)

        return 0

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--no-reports", action="store_true", default=False,
                            help="do not process reports")
        parser.add_argument("--no-attachments", action="store_true",
                            default=False, help="do not process attachments")
        group = parser.add_argument_group()
        group.add_argument("--speedup", action="store_true",
                           default=False, help="Speedup the processing. "
                           "May be less accurate.")
        group.add_argument("--pattern", help="Save reports matched with pattern. "
                           "Does not work with speedup. E.g. --pattern \"123*\"")
