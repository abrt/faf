from sqlalchemy import event
from sqlalchemy.orm import mapper
from sqlalchemy.orm.session import Session

from . import Build
from . import ReportBacktrace
from . import ReportBtFrame


@event.listens_for(ReportBtFrame, "init")
def init_btframe(target, *args, **kwargs): # pylint: disable=unused-argument
    """
    Set reliable to True so it has default set correctly
    before it's stored in the database
    """
    target.reliable = True


@event.listens_for(Session, "before_flush")
def update_backtrace_quality(session, flush_context, instances): # pylint: disable=unused-argument
    """
    Compute and store backtrace quality information
    """

    objects = session.new.union(session.dirty)
    for obj in [c for c in objects if isinstance(c, ReportBacktrace)]:
        if isinstance(obj, ReportBacktrace):
            obj.quality = obj.compute_quality()


@event.listens_for(mapper, 'before_delete')
def before_delete(mapper, connection, target): # pylint: disable=unused-argument
    """
    Remove lobs associated with target to be deleted.
    """

    for lobname in target.__lobs__:
        if target.has_lob(lobname):
            target.del_lob(lobname)


@event.listens_for(Build.version, "set")
def store_semantic_version_for_build(target, value, oldvalue, initiator): # pylint: disable=unused-argument
    """
    Store semnatic version (Build.semver) converted from text version
    (Build.version)
    """

    target.semver = value


@event.listens_for(Build.release, "set")
def store_semantic_release_for_build(target, value, oldvalue, initiator): # pylint: disable=unused-argument
    """
    Store semnatic release (Build.semrel) converted from text release
    (Build.release)
    """

    target.semrel = value
