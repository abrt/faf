# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
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

from pyfaf.actions import Action
from pyfaf.storage import Build


class PackageGC(Action):
    """
    Garbage collect packages belonging to some release tag
    """

    name = "packagegc"

    def run(self, cmdline, db):
        print("Searching for builds with tag ending '{}'".format(cmdline.rt))
        likestr = "%{}".format(cmdline.rt)

        q = db.session.query(Build).filter(Build.release.like(likestr))

        print("Matched {} builds".format(q.count()))

        c = 0

        for build in q.yield_per(1000):
            for pkg in build.packages:
                if pkg.has_lob("package"):
                    pkg.del_lob("package")
                    c += 1

        print("Deleted {} packages".format(c))

        db.session.flush()

    def tweak_cmdline_parser(self, parser):
        parser.add_argument("--rt", required=True,
                            help="Release tag (e.g. fc22)")
