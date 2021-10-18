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
from argparse import _SubParsersAction, ArgumentParser, HelpFormatter, Namespace
from pyfaf.actions import actions
from pyfaf.common import log
from pyfaf.bugtrackers import bugtrackers
from pyfaf.solutionfinders import solution_finders


class FafHelpFormatter(HelpFormatter):
    """
    FAF-tweaked argparse.HelpFormatter that shows action list nicely.
    Assuming `action` is the only argument handled by subparsers.

    Even though this works fine, it is not nice - it overrides internals.
    """

    def _format_action_invocation(self, action) -> str:
        if isinstance(action, _SubParsersAction):
            # the longest action name
            longest = max([len(act) for act in actions])

            # Let's assume standard 80 characters long terminal and
            # - 2 spaces as padding at the beginning of each line (78 left)
            # - 2 spaces between columns (longest + 2).
            # Enforce at least one column to be displayed.
            columns = max(1, 78 // (longest + 2))

            i = 0
            line = []
            lines = []
            for act in sorted(actions.keys()):
                if i == columns:
                    i = 0
                    lines.append("  ".join(line))
                    line = []

                line.append(act.ljust(longest, " "))
                i += 1

            if line:
                lines.append("  ".join(line))

            return "\n  ".join(lines)

        sup = super()
        return sup._format_action_invocation(action) #pylint: disable=protected-access

    def _format_args(self, action, default_metavar) -> str:
        if isinstance(action, _SubParsersAction):
            return "action"

        sup = super()
        return sup._format_args(action, default_metavar) #pylint: disable=protected-access


class CmdlineParser(ArgumentParser):
    """
    Command line argument parser extended with project-specific options.
    """

    def __init__(self, desc=None, prog=sys.argv[0], usage=None,
                 add_help=True, argument_default=None, prefix_chars="-",
                 toplevel=False) -> None:

        super().__init__(description=desc, prog=prog,
                         usage=usage, add_help=add_help,
                         argument_default=argument_default,
                         prefix_chars=prefix_chars,
                         formatter_class=FafHelpFormatter)

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
            for action_name, action_object in actions.items():
                action_parser = action_parsers.add_parser(action_name)
                action_object.tweak_cmdline_parser(action_parser)
                action_parser.set_defaults(func=action_object.run)

    def add_argument(self, *args, **kwargs) -> None:
        """
        Override add_argument to allow passing of validators to ActionFormArgparser
        for use in the web UI
        """

        if "validators" in kwargs:
            del(kwargs["validators"])

        super().add_argument(*args, **kwargs)

    def parse_args(self, args=None, namespace=None) -> Namespace:
        """
        Parse command line arguments and set loglevel accordingly.
        """

        result = ArgumentParser.parse_args(self, args=args, namespace=namespace)
        log.setLevel(result.verbose)
        return result

    def _add_plugin_arg(self, *args, **kwargs) -> None:
        if kwargs.pop("multiple", False):
            kwargs["action"] = "append"
            kwargs["default"] = []

        self.add_argument(*args, **kwargs)

    def add_bugtracker(self, **kwargs) -> None:
        """
        Add the `-b` argument for specifying bug tracker.
        """

        defaults = dict(
            help="bug tracker",
            choices=bugtrackers,
            multiple=False,
        )
        defaults.update(kwargs)

        self._add_plugin_arg("-b", "--bugtracker", **defaults)

    def add_opsys(self, multiple=False, required=False, positional=False, with_rel=False, helpstr=None) -> None: # pylint: disable=unused-argument
        """
        Add an argument for specifying operating system.
        """

        if positional:
            nargs = None if required else "?"
            if multiple:
                nargs = "+" if required else "*"

            self.add_argument("OPSYS", nargs=nargs, help=helpstr)
        else:
            self._add_plugin_arg("-o", "--opsys", multiple=multiple, required=required,
                                 help=helpstr)

    def add_opsys_rel_status(self, required=False) -> None:
        """
        Add a positional argument for operating system(s) with release
        """

        self.add_argument("-s", "--status",
                          choices=["ACTIVE", "UNDER_DEVELOPMENT", "EOL"],
                          required=required,
                          help="release status")

    def add_opsys_release(self, multiple=False, required=False, positional=None, helpstr=None) -> None:
        """
        Add the argument for specifying operating system release.
        """

        if positional:
            nargs = None if required else "?"
            if multiple:
                nargs = "+" if required else "*"

            self.add_argument("RELEASE", nargs=nargs, help=helpstr)
        else:
            self._add_plugin_arg("--opsys-release", required=required,
                                 help=helpstr, multiple=multiple)

    def add_arch(self, multiple=False, required=False, positional=False, helpstr=None) -> None: # pylint: disable=unused-argument
        """
        Add an argument for architecture(s)
        """

        nargs = "*" if multiple else None

        if positional:
            self.add_argument("ARCH", nargs=nargs, help=helpstr)
        else:
            self._add_plugin_arg("-a", "--arch",
                                 help=helpstr, multiple=multiple)

    def add_problemtype(self, multiple=False) -> None:
        """
        Add the `-p` argument for specifying problem type.
        """

        self._add_plugin_arg("-p", "--problemtype",
                             help="problem type", multiple=multiple)

    def add_repo(self, multiple=False, helpstr=None) -> None:
        """
        Add a positional argument for repository/-ies
        """

        nargs = "*" if multiple else None

        self.add_argument("REPO", nargs=nargs, help=helpstr)

    def add_repo_type(self, choices=None, required=False, positional=False, helpstr=None) -> None:
        """
        Add the argument for the type of the repository.
        """
        if positional:
            self.add_argument("TYPE", choices=choices, help=helpstr)
        else:
            self.add_argument("--type", choices=choices, required=required, help=helpstr)

    def add_ext_instance(self, multiple=False, helpstr=None) -> None:
        """
        Add the `INSTANCE_ID` positional argument for an external FAF instance.
        """
        nargs = "*" if multiple else None

        self.add_argument("INSTANCE_ID", nargs=nargs, help=helpstr)

    def add_file(self, required=False, helpstr=None) -> None:
        """
        Add the `FILE` positional argument for repository file.
        """
        nargs = 1 if required else None

        self.add_argument("FILE", nargs=nargs, help=helpstr)

    def add_solutionfinder(self, **kwargs) -> None:
        """
        Add the `-s` argument for specifying solution finders.
        """
        defaults = dict(
            help="solution finder",
            choices=solution_finders,
            multiple=True,
        )
        defaults.update(kwargs)

        self._add_plugin_arg("-s", "--solution-finder", **defaults)

    def add_gpgcheck_toggle(self, required=False, helpstr=None) -> None:
        """
        Add an argument for changing the GPG requirement property
        """

        self.add_argument("--gpgcheck",
                          choices=["enable", "disable"],
                          required=required,
                          help=helpstr)
