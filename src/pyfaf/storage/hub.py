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

from . import Boolean
from . import Column
from . import DateTime
from . import Enum
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import Text
from . import relationship

class HubUser(GenericTable):
    __tablename__ = "auth_user"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, index=True, unique=True)
    first_name = Column(String(30), nullable=False)
    last_name = Column(String(30), nullable=False)
    email = Column(String(75), nullable=False)
    password = Column(String(128), nullable=False)
    is_staff = Column(Boolean, nullable=False)
    is_active = Column(Boolean, nullable=False)
    is_superuser = Column(Boolean, nullable=False)
    last_login = Column(DateTime, nullable=False)
    date_joined = Column(DateTime, nullable=False)

class HubArch(GenericTable):
    __tablename__ = "hub_arch"

    id = Column(Integer, primary_key=True)
    name = Column(String(16), nullable=False, index=True, unique=True)
    pretty_name = Column(String(64), nullable=False, index=True, unique=True)

class HubChannel(GenericTable):
    __tablename__ = "hub_channel"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)

class HubWorker(GenericTable):
    __tablename__ = "hub_worker"

    id = Column(Integer, primary_key=True)
    worker_key = Column(String(255), nullable=False, index=True, unique=True)
    name = Column(String(128), nullable=False, index=True, unique=True)
    enabled = Column(Boolean, nullable=False)
    max_load = Column(Integer, nullable=False)
    max_tasks = Column(Integer, nullable=False)
    ready = Column(Boolean, nullable=False)
    task_count = Column(Integer, nullable=False)
    current_load = Column(Integer, nullable=False)

class HubTask(GenericTable):
    __tablename__ = "hub_task"

    id = Column(Integer, primary_key=True)
    archive = Column(Boolean, nullable=False)
    owner_id = Column(Integer, ForeignKey("{0}.id".format(HubUser.__tablename__)), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("{0}.id".format(HubWorker.__tablename__)), nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey("{0}.id".format(__tablename__)), nullable=True, index=True)
    state = Column(Integer, nullable=False)
    label = Column(String(255), nullable=False)
    exclusive = Column(Boolean, nullable=False)
    method = Column(String(255), nullable=False)
    args = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    comment = Column(Text, nullable=True)
    arch_id = Column(Integer, ForeignKey("{0}.id".format(HubArch.__tablename__)), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("{0}.id".format(HubChannel.__tablename__)), nullable=False, index=True)
    timeout = Column(Integer, nullable=True)
    waiting = Column(Boolean, nullable=False)
    awaited = Column(Boolean, nullable=False)
    dt_created = Column(DateTime, nullable=False)
    dt_started = Column(DateTime, nullable=True)
    dt_finished = Column(DateTime, nullable=True)
    priority = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=False)
    resubmitted_by_id = Column(Integer, ForeignKey("{0}.id".format(HubUser.__tablename__)), nullable=True, index=True)
    resubmitted_from_id = Column(Integer, ForeignKey("{0}.id".format(__tablename__)), nullable=True, index=True)
    subtask_count = Column(Integer, nullable=False)

class PeriodicTask(GenericTable):
    __tablename__ = "periodictasks"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    args = Column(Text, nullable=False)
    tasktype = Column(Integer, nullable=False)
    time = Column(String(16), nullable=False)
    enabled = Column(Boolean, nullable=True)
