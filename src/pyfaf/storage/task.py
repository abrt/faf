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

import json

from sqlalchemy.sql.schema import Column
from sqlalchemy.types import Boolean, DateTime, Integer, String, Text

from .generic_table import GenericTable
from .jsontype import JSONType


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
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    args = Column(JSONType, nullable=False, default=[])
    kwargs = Column(JSONType, nullable=False, default={})

    @property
    def is_run_action(self) -> bool:
        return self.task == "pyfaf.celery_tasks.run_action"

    @property
    def nice_name(self) -> str:
        return str(self.name)

    @property
    def nice_task(self) -> str:
        if self.is_run_action and self.args:
            return "Action {0}".format(self.args[0])
        return self.task


class TaskResult(GenericTable):
    __tablename__ = "taskresult"
    id = Column(String(50), primary_key=True)
    task = Column(String(100), nullable=False)
    finished_time = Column(DateTime(timezone=True), nullable=True)
    state = Column(String(20), nullable=False)
    retval = Column(Text, nullable=False, default="")
    args = Column(JSONType, nullable=False, default=[])
    kwargs = Column(JSONType, nullable=False, default={})

    @property
    def is_run_action(self) -> bool:
        return self.task == "pyfaf.celery_tasks.run_action"

    @property
    def nice_task(self) -> str:
        if self.is_run_action and self.args:
            return "Action {0}".format(self.args[0])
        return self.task

    @property
    def nice_args(self) -> str:
        return json.dumps(self.args, indent=4)
