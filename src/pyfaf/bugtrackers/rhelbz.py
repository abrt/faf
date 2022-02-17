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

from typing import Any, Dict, Generator, Optional

from pyfaf.bugtrackers import bugzilla

__all__ = ["RhelBugzilla"]


class RhelBugzilla(bugzilla.Bugzilla):
    name = "rhel-bugzilla"

    def list_bugs(self, *args, **kwargs) -> Generator[int, None, None]:

        abrt_specific = dict(
            status_whiteboard="abrt_hash",
            status_whiteboard_type="allwordssubstr",
            product=["Red Hat Enterprise Linux 6",
                     "Red Hat Enterprise Linux 7",
                     "Red Hat Enterprise Linux 8"],
        )

        if "custom_fields" in kwargs:
            kwargs["custom_fields"].update(abrt_specific)
        else:
            kwargs["custom_fields"] = abrt_specific

        return super().list_bugs(*args, **kwargs)

    def preprocess_bug(self, bug) -> Optional[Dict[str, Any]]:
        bug_dict = super().preprocess_bug(bug)

        # handle "Red Hat Enterprise Linux \d" product naming
        # by stripping the number which is redundant for our purposes
        # as we also have bug_dict["version"] from bugzilla

        if "Red Hat Enterprise Linux" in bug_dict["product"]:
            bug_dict["product"] = " ".join(bug_dict["product"].split()[:-1])

        return bug_dict
