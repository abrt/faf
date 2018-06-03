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

from . import Boolean
from . import Column
from . import GenericTable
from . import String
from . import Text
from . import Integer
from . import DateTime
from pyfaf.storage.jsontype import JSONType
import json


class PeriodicTask(GenericTable):
    __tablename__ = "periodictasks"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    task = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    crontab_minute = Column(String(20), nullable=False, default="*")
    crontab_hour = Column(String(20), nullable=False, default="*")
    crontab_day_of_week = Column(String(20), nullable=False, default="*")
    crontab_day_of_month = Column(String(20), nullable=False, default="*")
    crontab_month_of_year = Column(String(20), nullable=False, default="*")
    last_run_at = Column(DateTime, nullable=True)
    args = Column(JSONType, nullable=False, default=[])
    kwargs = Column(JSONType, nullable=False, default={})

    @property
    def is_run_action(self):
        return self.task == "pyfaf.celery_tasks.run_action"

    @property
    def args_parsed(self):

        return self._foo

    @property
    def nice_name(self):
        return self.name

    @property
    def nice_task(self):
        if self.is_run_action and self.args:
            return "Action {0}".format(self.args[0])
        return self.task


class TaskResult(GenericTable):
    __tablename__ = "taskresult"
    id = Column(String(50), primary_key=True)
    task = Column(String(100), nullable=False)
    finished_time = Column(DateTime, nullable=True)
    state = Column(String(20), nullable=False)
    retval = Column(Text, nullable=False, default="")
    args = Column(JSONType, nullable=False, default=[])
    kwargs = Column(JSONType, nullable=False, default={})

    @property
    def is_run_action(self):
        return self.task == "pyfaf.celery_tasks.run_action"

    @property
    def nice_task(self):
        if self.is_run_action and self.args:
            return "Action {0}".format(self.args[0])
        return self.task

    @property
    def nice_args(self):
        return json.dumps(self.args, indent=4)
