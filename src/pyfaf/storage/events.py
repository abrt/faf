from sqlalchemy import event
from sqlalchemy.orm import mapper


@event.listens_for(mapper, 'before_delete')
def before_delete(mapper, connection, target):
    """
    Remove lobs associated with target to be deleted.
    """

    for lobname, size in target.__lobs__.items():
        if target.has_lob(lobname):
            target.del_lob(lobname)
