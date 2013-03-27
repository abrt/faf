import logging
import re

from pyfaf.storage.kb import (KbBacktracePath,
                              KbPackageName)

def get_kb_btpath_parsers(db, opsys_id=None):
    result = {}
    kbentries = (db.session.query(KbBacktracePath)
                           .filter((KbBacktracePath.opsys_id == opsys_id) |
                                   (KbBacktracePath.opsys_id == None)))

    for kbentry in kbentries:
        try:
            parser = re.compile(kbentry.pattern)
        except Exception as ex:
            logging.warn("Pattern '{0}' can't be compiled as regexp: {1}"
                         .format(kbentry.pattern, str(ex)))

        result[parser] = kbentry.solution

    return result

def get_kb_pkgname_parsers(db, opsys_id=None):
    result = {}
    kbentries = (db.session.query(KbPackageName)
                           .filter((KbPackageName.opsys_id == opsys_id) |
                                   (KbPackageName.opsys_id == None)))

    for kbentry in kbentries:
        try:
            parser = re.compile(kbentry.pattern)
        except Exception as ex:
            logging.warn("Pattern '{0}' can't be compiled as regexp: {1}"
                         .format(kbentry.pattern, str(ex)))

        result[parser] = kbentry.solution

    return result
