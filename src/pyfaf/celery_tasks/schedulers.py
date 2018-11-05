# Based on code by Kong Luoxing 2014

import datetime

from celery.beat import Scheduler, ScheduleEntry
from celery import current_app
import celery.schedules

from pyfaf.storage.task import PeriodicTask
from pyfaf.storage import DatabaseFactory

db_factory = DatabaseFactory()


class DBScheduleEntry(ScheduleEntry):
    def __init__(self, db_task):
        self.db_task = db_task
        self.app = current_app._get_current_object() #pylint: disable=protected-access
        self.name = db_task.name
        self.task = db_task.task
        self.enabled = db_task.enabled

        self.schedule = celery.schedules.crontab(minute=db_task.crontab_minute,
                                                 hour=db_task.crontab_hour,
                                                 day_of_week=db_task.crontab_day_of_week,
                                                 day_of_month=db_task.crontab_day_of_month,
                                                 month_of_year=db_task.crontab_month_of_year)

        self.args = db_task.args
        self.kwargs = db_task.kwargs

        self.options = {}

        if not self.db_task.last_run_at:
            self.db_task.last_run_at = self._default_now()
        self.last_run_at = self.db_task.last_run_at

    def _default_now(self):
        return self.app.now()

    def next(self):
        self.db_task.last_run_at = self.app.now()
        return self.__class__(self.db_task)

    __next__ = next

    def is_due(self):
        if not self.enabled:
            return False, 60.0  # 60 second delay for re-enable.
        return self.schedule.is_due(self.last_run_at)

    def __repr__(self):
        return '<DBScheduleEntry ({0} {1}(*{2}, **{3}) {{{4}}})>'.format(
            self.name, self.task, self.args,
            self.kwargs, self.schedule,
        )

    def reserve(self, entry):
        new_entry = Scheduler.reserve(self, entry)
        return new_entry

    def save(self):
        if self.last_run_at and self.db_task.last_run_at and self.last_run_at > self.db_task.last_run_at:
            self.db_task.last_run_at = self.last_run_at


class DBScheduler(Scheduler):
    # how often should we sync in schedule information
    # from the backend DB
    UPDATE_INTERVAL = datetime.timedelta(seconds=30)

    Entry = DBScheduleEntry

    def __init__(self, *args, **kwargs):
        self._schedule = {}
        self._last_updated = None
        Scheduler.__init__(self, *args, **kwargs)
        self.max_interval = (kwargs.get('max_interval')
                             or self.app.conf.CELERYBEAT_MAX_LOOP_INTERVAL or 300)
        self.db = db_factory.get_database()

    def setup_schedule(self):
        pass

    def requires_update(self):
        # check whether we should pull an updated schedule from the backend
        # database
        if not self._last_updated:
            return True
        return self._last_updated + self.UPDATE_INTERVAL < datetime.datetime.now()

    def get_from_database(self):
        d = {}
        for task in self.db.session.query(PeriodicTask):
            d[task.name] = DBScheduleEntry(task)
        return d

    @property
    def schedule(self):
        if self.requires_update():
            self._schedule = self.get_from_database()
            self._last_updated = datetime.datetime.now()
        return self._schedule

    def sync(self):
        for entry in self.schedule.values():
            entry.save()
        self.db.session.commit()

    def close(self):
        self.sync()
