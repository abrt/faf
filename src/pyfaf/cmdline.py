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

import logging
import sys
from argparse import ArgumentParser
from pyfaf.actions import actions
from pyfaf.common import log

class CmdlineParser(ArgumentParser):
    """
    Command line argument parser extended with project-specific options.
    """

    def __init__(self, desc=None, prog=sys.argv[0], usage=None,
                 add_help=True, argument_default=None, prefix_chars="-",
                 toplevel=False):

        ArgumentParser.__init__(self, description=desc, prog=prog,
                                usage=usage, add_help=add_help,
                                argument_default=argument_default,
                                prefix_chars=prefix_chars)

        self.add_argument("-v", "--verbose", action="store_const",
                          const=logging.DEBUG, default=logging.INFO,
                          help="turn on all verbose output except for SQL")
        self.add_argument("--sql-verbose", action="store_true", default=False,
                          help="show all SQL queries (really verbose)")
        self.add_argument("-d", "--debug", action="store_true", default=False,
                          help="show full traceback for unhandled exceptions")
        self.add_argument("--dry-run", action="store_true", default=False,
                          help="do not flush any changes to the database")

        if toplevel:
            action_parsers = self.add_subparsers(title="action")
            for action in actions:
                action_parser = action_parsers.add_parser(action)
                actions[action].tweak_cmdline_parser(action_parser)
                action_parser.set_defaults(func=actions[action].run)

    def parse_args(self, args=None, namespace=None):
        """
        Parse command line arguments and set loglevel accordingly.
        """

        result = ArgumentParser.parse_args(self, args=args, namespace=namespace)
        log.setLevel(result.verbose)
        return result

    def _add_plugin_arg(self, *args, **kwargs):
        if kwargs.pop("multiple", False):
            kwargs["action"] = "append"
            kwargs["default"] = []

        self.add_argument(*args, **kwargs)

    def add_bugtracker(self, multiple=False):
        """
        Add the `-b` argument for specifying bug tracker.
        """

        self._add_plugin_arg("-b", "--bugtracker",
                             help="bug tracker", multiple=multiple)

    def add_opsys(self, multiple=False):
        """
        Add the `-o` argument for specifying operating system.
        """

        self._add_plugin_arg("-o", "--opsys",
                             help="operating system", multiple=multiple)

    def add_opsys_release(self, multiple=False):
        """
        Add the `--opsys-release` argument for specifying
        operating system release.
        """

        self._add_plugin_arg("--opsys-release",
                             help="operating system release", multiple=multiple)

    def add_problemtype(self, multiple=False):
        """
        Add the `-p` argument for specifying problem type.
        """

        self._add_plugin_arg("-p", "--problemtype",
                             help="problem type", multiple=multiple)

    def add_repo(self, multiple=False):
        """
        Add the `-r` argument for specifying repository.
        """

        self._add_plugin_arg("-r", "--repo",
                             help="repository", multiple=multiple)
