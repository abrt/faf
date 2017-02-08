#!/usr/bin/env python2

import os
import sys

from flask_script import Manager, Shell

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from webfaf_main import app, db
from webfaf_main import import_blueprint_plugins


import_blueprint_plugins(app)
manager = Manager(app)


def make_shell_context():
    return dict(app=app, db=db)

manager.add_command('shell', Shell(make_context=make_shell_context))

if __name__ == '__main__':
    manager.run()
