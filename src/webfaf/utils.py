import datetime
import itertools
import urllib
from functools import wraps
from collections import namedtuple

from flask import abort, g, url_for, request, redirect, make_response
from flask.json import JSONEncoder

from pyfaf.storage import GenericTable
from pyfaf.storage.problem import Problem
from pyfaf.storage.report import (Report,
                                  ReportBtFrame,
                                  ReportComment,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly)
from pyfaf.storage.bugzilla import BzUser
from pyfaf import queries
from webfaf.webfaf_main import app


class Pagination(object):

    def __init__(self, r, default_limit=40):
        # copies ImmutableMultiDict to MultiDict
        self.get_args = r.args.copy()
        self.limit = max(int(self.get_args.get("limit", default_limit)), 0)
        self.offset = max(int(self.get_args.get("offset", 0)), 0)
        self.request = r

    def url_next_page(self, query_count=None):
        if query_count == self.limit or query_count is None:
            self.get_args["offset"] = self.offset + self.limit
            return (url_for(self.request.endpoint,
                            **dict(list(self.request.view_args.items()))) +
                    "?"+urllib.parse.urlencode(self.get_args.items(multi=True)))

        return None

    def url_prev_page(self):
        if self.offset > 0:
            self.get_args["offset"] = max(self.offset - self.limit, 0)
            return (url_for(self.request.endpoint,
                            **dict(list(self.request.view_args.items()))) +
                    "?"+urllib.parse.urlencode(self.get_args.items(multi=True)))

        return None


def diff(lhs_seq, rhs_seq, eq=None):
    '''
    Computes a diff of two sequences.

    Algorithm is based on Longest Common Subsequence problem.

    Returns a list of pairs. Each pair consists from either a value from the
    first sequence and None or from None and a value from the second sequence
    or values from both sequences.

    >>> diff(banana, ananas)
    [('b', None), ('a', 'a'), ('n', 'n'), ('a', 'a'),
     ('n', 'n'), ('a', 'a'), (None, 's')]
    '''
    if not eq:
        eq = lambda x, y: x == y

    result = list()
    l = 0
    l_e = len(lhs_seq) - 1
    r = 0
    r_e = len(rhs_seq) - 1
    # handle common prefix
    while l <= l_e and r <= r_e and eq(lhs_seq[l], rhs_seq[r]):
        result.append((lhs_seq[l], rhs_seq[r]))
        l += 1
        r += 1

    end_result = list()
    # handle common suffix
    while l <= l_e and r <= r_e and eq(lhs_seq[l_e], rhs_seq[r_e]):
        end_result.append((lhs_seq[l_e], rhs_seq[r_e]))
        l_e -= 1
        r_e -= 1

    matrix_row_len = (r_e - r) + 2
    # build matrix which has one more column and line than rhs x lhs
    m = list(itertools.repeat(0, ((l_e - l) + 2) * matrix_row_len))

    # skip first row because it contains only 0
    pos = matrix_row_len

    # in case where strings are the same l has value len(left) == l_e + 1
    i = l_e
    # in case where strings are the same r has value len(right) == r_e + 1
    j = r_e

    for i in range(l, l_e + 1):
        pos += 1  # skip first column which is always 0
        for j in range(r, r_e + 1):
            if eq(lhs_seq[i], rhs_seq[j]):
                res = m[pos - matrix_row_len - 1] + 1
            else:
                res = max(m[pos - matrix_row_len], m[pos - 1])
            m[pos] = res
            pos += 1

    pos -= 1  # current value is len(m)
    i += 1   # current value is last of xrange(l, l_e + 1)
    j += 1   # current value is last of xrange(r, r_e + 1)
    while i != l and j != r:
        if m[pos] == m[pos - 1]:
            pos -= 1
            j -= 1
            end_result.append((None, rhs_seq[j]))
        elif m[pos] == m[pos - matrix_row_len]:
            pos -= matrix_row_len
            i -= 1
            end_result.append((lhs_seq[i], None))
        else:
            pos -= matrix_row_len
            pos -= 1
            i -= 1
            j -= 1
            end_result.append((lhs_seq[i], rhs_seq[j]))

    while i != l:
        i -= 1
        end_result.append((lhs_seq[i], None))

    while j != r:
        j -= 1
        end_result.append((None, rhs_seq[j]))

    end_result.reverse()
    return result + end_result


def date_iterator(first_date, time_unit='d', end_date=None):
    '''
    Iterates from date until reaches end date or never finishes
    '''
    if time_unit == 'd':
        next_date_fn = lambda x: x + datetime.timedelta(days=1)
    elif time_unit == 'w':
        first_date -= datetime.timedelta(days=first_date.weekday())
        next_date_fn = lambda x: x + datetime.timedelta(weeks=1)
    elif time_unit in ['m', '*']:
        first_date = first_date.replace(day=1)
        next_date_fn = lambda x: (x.replace(day=25) +
                                  datetime.timedelta(days=7)).replace(day=1)
    else:
        raise ValueError('Unknown time unit type : "%s"' % time_unit)

    toreturn = first_date
    yield toreturn
    while True:
        toreturn = next_date_fn(toreturn)
        if end_date is not None and toreturn > end_date:
            break

        yield toreturn


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']

metric_tuple = namedtuple('Metric', ['name', 'count'])


def metric(objects):
    """
    Convert list of KeyedTuple(s) returned by SQLAlchemy to
    list of namedtuple('Metric', ['name', 'count'])

    When converted with this function JSON output
    is rendered correctly:

        "arches": [
            {
            "count": 101,
            "name": "x86_64"
            }
        ],

    instead of

        "arches": [
            {
            "ReportArch": "x86_64",
            "count": 101
            }
        ],
    """

    result = []

    for obj in objects:
        result.append(metric_tuple(*obj))

    return result


class WebfafJSONEncoder(JSONEncoder):
    def default(self, o): #pylint: disable=method-hidden
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, datetime.date):
            return o.isoformat()
        if isinstance(o, Problem):
            d = {"id": o.id,
                 "components": o.unique_component_names,
                 "crash_function": o.crash_function,
                 "bugs": [bug.url for bug in o.bugs],
                 "status": o.status,
                 "type": o.type,
                 "reports": o.reports,
                }
            if hasattr(o, "count"):
                d["count"] = o.count
            return d
        if isinstance(o, Report):
            d = {"id": o.id,
                 "bugs": [bug.url for bug in o.bugs],
                 "component": o.component,
                 "count": o.count,
                 "first_occurrence": o.first_occurrence,
                 "last_occurrence": o.last_occurrence,
                 "problem_id": o.problem_id,
                 "comments": o.comments,
                }

            return d
        if isinstance(o, ReportBtFrame):
            if o.symbolsource.symbol is None:
                name = " "
            else:
                if o.symbolsource.symbol.nice_name:
                    name = o.symbolsource.symbol.nice_name
                else:
                    name = o.symbolsource.symbol.name

            d = {"frame": o.order,
                 "name": name,
                 "binary_path": o.symbolsource.path,
                 "source_path": o.symbolsource.source_path,
                 "line_numer": o.symbolsource.line_number,
                }
            return d
        if isinstance(o, ReportComment):
            d = {"saved": o.saved,
                 "text": o.text,
                }
            return d
        if isinstance(o, ReportHistoryDaily):
            return dict(date=o.day, count=o.count)
        if isinstance(o, ReportHistoryWeekly):
            return dict(date=o.week, count=o.count)
        if isinstance(o, ReportHistoryMonthly):
            return dict(date=o.month, count=o.count)
        if isinstance(o, GenericTable):
            return str(o)
        if isinstance(o, set):
            return list(o)

        return JSONEncoder.default(self, o)


def fed_raw_name(oidname):
    """
    Get FAS username from OpenID URL
    """

    return oidname.replace(".id.fedoraproject.org/", "") \
                  .replace("http://", "") \
                  .replace("https://", "")


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login.do_login', next=request.url))

        return func(*args, **kwargs)
    return decorated_view


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login.do_login', next=request.url))

        if not g.user.admin:
            abort(403)

        return func(*args, **kwargs)
    return decorated_view


def is_component_maintainer(db, user, component):
    is_maintainer = app.config["EVERYONE_IS_MAINTAINER"]
    if not is_maintainer and user is not None:
        if (user.admin
                or user.privileged
                or queries.user_is_maintainer(db, user.username, component.id)):
            is_maintainer = True
    return is_maintainer


def is_problem_maintainer(db, user, problem):
    is_maintainer = app.config["EVERYONE_IS_MAINTAINER"]
    if not is_maintainer and user is not None:
        if user.admin or user.privileged:
            is_maintainer = True
        else:
            component_ids = set(c.id for c in problem.components)
            if any(queries.user_is_maintainer(db, user.username, component_id)
                   for component_id in component_ids):
                is_maintainer = True
    return is_maintainer


def cache(hours=0, minutes=0, seconds=0, logged_in_disable=False):
    """
    Add Cache-Control headers

    Usage:

    @app.route('/map')
    @cache(hours=1)
    def index():
      return render_template('index.html')

    """
    def cache_decorator(view):
        @wraps(view)
        def cache_func(*args, **kwargs):
            if logged_in_disable and g.user is not None:
                return make_response(view(*args, **kwargs))

            total = seconds + minutes * 60 + hours * 3600

            response = make_response(view(*args, **kwargs))
            response.headers['Cache-Control'] = 'max-age={0}'.format(total)

            return response
        return cache_func
    return cache_decorator


def create_anonymous_bzuser(db, uid=-1):
    """
    Create an anonymous BzUser in the database. If the user exists, return him.
    """
    bzuser = db.session.query(BzUser).filter(BzUser.id == uid).first()

    if bzuser is None:
        bzuser = BzUser(id=uid,
                        email='anonymous',
                        name='anonymous',
                        real_name='anonymous',
                        can_login=False)

        db.session.add(bzuser)
        db.session.flush()

    return bzuser


def delete_bugzilla_user(db, user_id, alt_id):
    """
    For given user_id delete BzUser and his comments, attachments, ccs from the database.
    And replace 'user_id' in related bugzillas and bugzilla history with 'alt_id'.
    """
    bzcomments = queries.get_bzcomments_by_uid(db, user_id)
    for bzcomm in bzcomments.all():
        if bzcomm.has_lob("content"):
            bzcomm.del_lob("content")
    bzcomments.delete(False)

    bzattachments = queries.get_bzattachments_by_uid(db, user_id)
    for attach in bzattachments.all():
        if attach.has_lob("content"):
            attach.del_lob("content")
    bzattachments.delete(False)

    queries.get_bzbugccs_by_uid(db, user_id).delete(False)

    bzbughistory = queries.get_bzbughistory_by_uid(db, user_id).all()
    for hist in bzbughistory:
        hist.user_id = alt_id

    bz_bugs = queries.get_bugzillas_by_uid(db, user_id).all()
    for bug in bz_bugs:
        bug.creator_id = alt_id
