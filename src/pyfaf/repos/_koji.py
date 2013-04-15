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

import koji

class Koji(object):
    """
    A common interface to koji instances. All koji repos
    should use the this class and just differ in URL.
    """

    def __init__(self, xmlrpc_url, package_url):
        self._xmlrpc_url = xmlrpc_url
        self._package_url = package_url

        self._koji_client = koji.ClientSession(self._xmlrpc_url)

    def get_builds(self, component):
        pass

    def get_build(self, build_id):
        pass
