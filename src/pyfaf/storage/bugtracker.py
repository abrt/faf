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

from sqlalchemy.sql.schema import Column
from sqlalchemy.types import Integer, String

from pyfaf.config import config

from .generic_table import GenericTable


class Bugtracker(GenericTable):
    __tablename__ = "bugtrackers"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)

    def __str__(self):
        return self.name

    @property
    def web_url(self):
        cfgstr = "{0}.web_url".format(self.name)
        if cfgstr in config:
            return config[cfgstr]
        return None

    @property
    def api_url(self):
        cfgstr = "{0}.api_url".format(self.name)
        if cfgstr in config:
            return config[cfgstr]
        return None

    @property
    def abbr(self):
        cfgstr = "{0}.abbr".format(self.name)
        if cfgstr in config:
            return config[cfgstr]
        return ""
