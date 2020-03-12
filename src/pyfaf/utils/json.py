# Copyright © 2020  Red Hat, Inc.
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

from json import JSONEncoder

from pyfaf.solutionfinders import Solution

class FAFJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Solution):
            solution = o.__dict__.copy()
            solution['since'] = str(solution['since'])

            return solution

        return super().default(o)
