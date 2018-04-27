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

import subprocess
from pyfaf.common import log

log = log.getChildLogger(__name__)

__all__ = ["popen", "safe_popen"]


def popen(cmd, *args):
    """
    Execute `proc` process, wait until
    the execution is over, return
    Popen object.
    """
    args = list(map(str, args))

    proc = subprocess.Popen([cmd] + args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            close_fds=True)

    (stdout, stderr) = proc.communicate()
    # replace closed file descriptors with their contents
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def safe_popen(cmd, *args):
    """
    Execute `proc` process and check
    its return code. In case of zero function
    returns Popen object just like `popen`.

    If the return code is non-zero, function
    logs an error and returns None.
    """

    proc = popen(cmd, *args)
    # Instance of 'Popen' has no 'returncode' member
    # pylint: disable-msg=E1101
    if proc.returncode != 0:
        log.error("Failed to execute {0} with arguments {1}".format(
            cmd, " ".join(args)))
        log.error("return code: {0}".format(proc.returncode))

        if proc.stdout:
            log.error("stdout: {0}".format(proc.stdout))

        if proc.stderr:
            log.error("stderr: {0}".format(proc.stderr))

        return None
    # pylint: enable-msg=E1101

    return proc
