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

import errno
import datetime
import os
import shutil
import tempfile

from pyfaf.actions import Action
from pyfaf.common import FafError, ensure_dirs, get_temp_dir
from pyfaf.utils.proc import safe_popen


class ArchiveReports(Action):
    name = "archive-reports"

    dirname_reports = "reports"
    dirname_attachments = "attachments"
    dirname_incoming = "incoming"
    dirname_saved = "saved"
    dirname_deferred = "deferred"
    dirname_archive = "archive"

    def __init__(self):
        super(ArchiveReports, self).__init__()

        basedir_keys = ["ureport.directory", "report.spooldirectory"]
        self.load_config_to_self("basedir", basedir_keys, "/var/spool/faf/")

        # Instance of 'ArchiveReports' has no 'basedir' member
        # pylint: disable-msg=E1101

        self.dir_report = os.path.join(self.basedir,
                                       ArchiveReports.dirname_reports)
        self.dir_report_incoming = os.path.join(self.dir_report,
                                                ArchiveReports.dirname_incoming)
        self.dir_report_saved = os.path.join(self.dir_report,
                                             ArchiveReports.dirname_saved)
        self.dir_report_deferred = os.path.join(self.dir_report,
                                                ArchiveReports.dirname_deferred)
        self.dir_report_archive = os.path.join(self.dir_report,
                                               ArchiveReports.dirname_archive)

        self.dir_attach = os.path.join(self.basedir,
                                       ArchiveReports.dirname_attachments)
        self.dir_attach_incoming = os.path.join(self.dir_attach,
                                                ArchiveReports.dirname_incoming)
        self.dir_attach_saved = os.path.join(self.dir_attach,
                                             ArchiveReports.dirname_saved)
        self.dir_attach_deferred = os.path.join(self.dir_attach,
                                                ArchiveReports.dirname_deferred)
        self.dir_attach_archive = os.path.join(self.dir_attach,
                                               ArchiveReports.dirname_archive)

        try:
            ensure_dirs([self.dir_report_incoming, self.dir_report_saved,
                         self.dir_report_deferred, self.dir_report_archive,
                         self.dir_attach_incoming, self.dir_attach_saved,
                         self.dir_attach_deferred, self.dir_attach_archive])
        except FafError as ex:
            self.log_error("Required directories can't be created: {0}"
                           .format(str(ex)))
            raise

    def _tar_xz(self, archive_name, archive_dir, filepaths, unlink=True):
        archive_path = os.path.join(archive_dir, archive_name)
        archive_path_tmp = os.path.join(archive_dir,
                                        "{0}.tmp".format(archive_name))
        tmpdir = get_temp_dir()
        tmpsubdir = os.path.join(tmpdir, "archive")
        unlink_paths = list(filepaths)

        try:
            os.makedirs(tmpsubdir)
        except OSError as ex:
            if ex.errno == errno.EEXIST:
                raise FafError("The directory '{0}' already exists"
                               .format(tmpsubdir))
            raise

        untar = None
        if os.path.isfile(archive_path):
            self.log_info("An existing archive found, will merge the contents")
            untar = self._untar_xz(archive_path)
            for filename in [os.path.join(untar, f) for f in os.listdir(untar)]:
                if os.path.isdir(filename) and filename.endswith("archive"):
                    filepaths = [os.path.join(filename, f)
                                 for f in os.listdir(filename)] + filepaths
                    break

        self.log_info("Creating symlinks")
        for filepath in filepaths:
            linkpath = os.path.join(tmpsubdir, os.path.basename(filepath))
            # merge - do not overwrite already archived data
            try:
                self.log_debug("{0} ~> {1}".format(filepath, linkpath))
                os.symlink(filepath, linkpath)
            except OSError as ex:
                if ex.errno != errno.EEXIST:
                    raise

                self.log_debug("Already exists")

        self.log_info("Running tar")
        safe_popen("tar", "chJf", archive_path_tmp, "-C", tmpdir, "archive")
        os.rename(archive_path_tmp, archive_path)

        self.log_info("Cleaning up")

        if untar is not None:
            shutil.rmtree(untar, ignore_errors=True)

        if unlink:
            for path in unlink_paths:
                os.unlink(path)

        shutil.rmtree(tmpsubdir)

    def _untar_xz(self, archive):
        tmpdir = tempfile.mkdtemp(dir=get_temp_dir(),
                                  prefix=os.path.basename(archive))
        safe_popen("tar", "xJf", archive, "-C", tmpdir)
        return tmpdir

    def _create_archive_map(self, dirnames):
        fnames = set()
        for dirname in dirnames:
            fnames |= set(os.path.join(dirname, f) for f in os.listdir(dirname))

        result = {}
        for filename in fnames:
            mtime = os.path.getmtime(filename)
            date = str(datetime.datetime.utcfromtimestamp(mtime).date())
            if date not in result:
                result[date] = []

            result[date].append(filename)

        return result

    def _archive_reports(self, dates, unlink=True):
        self.log_info("Archiving reports")

        dirs = [self.dir_report_saved, self.dir_report_deferred]
        archive_map = self._create_archive_map(dirs)

        if dates is None:
            dates = list(archive_map.keys())

        i = 0
        for date in sorted(dates):
            i += 1
            self.log_info("[{0} / {1}] Archiving reports from {2}"
                          .format(i, len(dates), date))

            if date not in archive_map:
                self.log_warn("No reports found")
                continue

            archive_fname = "reports-{0}.tar.xz".format(date)
            self._tar_xz(archive_fname,
                         self.dir_report_archive,
                         archive_map[date],
                         unlink=unlink)

    def _archive_attachments(self, dates, unlink=True):
        self.log_info("Archiving attachments")

        dirs = [self.dir_attach_saved, self.dir_attach_deferred]
        archive_map = self._create_archive_map(dirs)

        if dates is None:
            dates = list(archive_map.keys())

        i = 0
        for date in sorted(dates):
            i += 1
            self.log_info("[{0} / {1}] Archiving reports from {2}"
                          .format(i, len(dates), date))

            if date not in archive_map:
                self.log_warn("No reports found")
                continue

            archive_fname = "attachments-{0}.tar.xz".format(date)
            self._tar_xz(archive_fname,
                         self.dir_attach_archive,
                         archive_map[date],
                         unlink=unlink)

    def run(self, cmdline, db):
        try:
            if not cmdline.no_reports:
                self._archive_reports(cmdline.date,
                                      unlink=(not cmdline.no_unlink))
        except FafError as ex:
            self.log_error(str(ex))

        try:
            if not cmdline.no_attachments:
                self._archive_attachments(cmdline.date,
                                          unlink=(not cmdline.no_unlink))
        except FafError as ex:
            self.log_error(str(ex))

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--date", action="append", default=None,
                            help="which day to archive (YYYY-MM-DD)")
        parser.add_argument("--no-unlink", action="store_true", default=False,
                            help="do not remove archived files")
        parser.add_argument("--no-reports", action="store_true", default=False,
                            help="do not process reports")
        parser.add_argument("--no-attachments", action="store_true",
                            default=False, help="do not process attachments")
