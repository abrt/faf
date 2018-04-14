import sys

if sys.version_info.major == 2:
#Python 2
    from StringIO import StringIO
else:
#Python 3+
    from io import StringIO

from contextlib import contextmanager


@contextmanager
def captured_output():
    """
    Capture stdout and stderr output of the executed block

    Example:

    with captured_output() as (out, err):
        foo()
    """

    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@contextmanager
def captured_output_combined():
    """
    Capture stdout and stderr combined output of the executed block

    Example:

    with captured_output_combined() as out:
        foo()
    """

    new_out = StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_out
        yield sys.stdout
    finally:
        sys.stdout, sys.stderr = old_out, old_err
