import munch
import datetime
import logging

from celery import Celery
from celery.signals import task_postrun
from pyfaf.actions import actions
from pyfaf.config import config
from pyfaf.storage import DatabaseFactory, TaskResult
from pyfaf.utils.contextmanager import captured_output_combined


celery_app = Celery("pyfaf_tasks",
                    broker=config.get("celery_tasks.broker", ""),
                    backend=config.get("celery_tasks.backend", ""))

db_factory = DatabaseFactory(autocommit=True)


class ActionError(Exception):
    def __init__(self, output):
        self.output = output
        Exception.__init__(self, output)

    def __str__(self):
        return self.output


@task_postrun.connect
def task_postrun_handler(signal, sender, **named):
    db = db_factory.get_database()
    tr = TaskResult()
    tr.id = named["task_id"]
    tr.task = named["task"].name
    tr.finished_time = datetime.datetime.now()
    tr.state = named["state"]
    tr.retval = named["retval"]
    tr.args = named["args"]
    tr.kwargs = named["kwargs"]
    db.session.add(tr)
    db.session.flush()


@celery_app.task()
def run_action(name, params={}, log_level=logging.DEBUG, output_length=1000):
    db = db_factory.get_database()
    action = actions[name]
    cmdline = munch.Munch(params)

    with captured_output_combined() as cap_stdout:
        # Logger and fake stdout to capture the output of the action
        root = logging.getLogger()
        ch = logging.StreamHandler(cap_stdout)
        ch.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        root.addHandler(ch)
        try:
            action.run(cmdline, db)
        except Exception as e:
            logging.exception(e)
            db.session.rollback()
            output = cap_stdout.getvalue()
            # There seems to be no way to pass a FAILURE status other than raising
            # an exception. self.update_status(status="FAILURE") didn't work.
            raise ActionError(output[-output_length:])

        db.session.rollback()
        output = cap_stdout.getvalue()
        return output[-output_length:]
