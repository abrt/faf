import logging
import re

from pyfaf.storage.kb import KbBacktracePath

def get_kb_btpath_parsers(db):
    result = {}
    kbentries = db.session.query(KbBacktracePath).all()
    for kbentry in kbentries:
        try:
            parser = re.compile(kbentry.pattern)
        except Exception as ex:
            logging.warn("Pattern '{0}' can't be compiled as regexp: {1}"
                         .format(kbentry.pattern, str(ex)))

        result[parser] = kbentry.solution

    return result
