import datetime
import itertools
from functools import wraps
from collections import namedtuple

from flask import abort, g, url_for, request, redirect, make_response
from flask.json import JSONEncoder
from urllib import urlencode

from pyfaf.storage import GenericTable
from pyfaf.storage.problem import Problem
from pyfaf.storage.report import (Report,
                                  ReportBtFrame,
                                  ReportComment,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly)
from pyfaf.queries import user_is_maintainer
from webfaf.webfaf_main import app
from six.moves import range


class Pagination(object):

    def __init__(self, request, default_limit=40):
        # copies ImmutableMultiDict to MultiDict
        self.get_args = request.args.copy()
        self.limit = max(int(self.get_args.get("limit", default_limit)), 0)
        self.offset = max(int(self.get_args.get("offset", 0)), 0)
        self.request = request

    def url_next_page(self, query_count=None):
        if query_count == self.limit or query_count is None:
            self.get_args["offset"] = self.offset + self.limit
            return (url_for(self.request.endpoint,
                            **dict(list(self.request.view_args.items()))) +
                    "?"+urlencode(self.get_args.items(multi=True)))
        else:
            return None

    def url_prev_page(self):
        if self.offset > 0:
            self.get_args["offset"] = max(self.offset - self.limit, 0)
            return (url_for(self.request.endpoint,
                            **dict(list(self.request.view_args.items()))) +
                    "?"+urlencode(self.get_args.items(multi=True)))
        else:
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
    elif time_unit == 'm' or time_unit == '*':
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
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, Problem):
            d = {"id": obj.id,
                 "components": obj.unique_component_names,
                 "crash_function": obj.crash_function,
                 "bugs": [bug.url for bug in obj.bugs],
                 "status": obj.status,
                 "type": obj.type,
                 "reports": obj.reports,
                }
            if hasattr(obj, "count"):
                d["count"] = obj.count
            return d
        elif isinstance(obj, Report):
            d = {"id": obj.id,
                 "bugs": [bug.url for bug in obj.bugs],
                 "component": obj.component,
                 "count": obj.count,
                 "first_occurrence": obj.first_occurrence,
                 "last_occurrence": obj.last_occurrence,
                 "problem_id": obj.problem_id,
                 "comments": obj.comments,
                }

            return d
        elif isinstance(obj, ReportBtFrame):
            if obj.symbolsource.symbol is None:
                name = " "
            else:
                if obj.symbolsource.symbol.nice_name:
                    name = obj.symbolsource.symbol.nice_name
                else:
                    name = obj.symbolsource.symbol.name

            d = {"frame": obj.order,
                 "name": name,
                 "binary_path": obj.symbolsource.path,
                 "source_path": obj.symbolsource.source_path,
                 "line_numer": obj.symbolsource.line_number,
                }
            return d
        elif isinstance(obj, ReportComment):
            d = {"saved": obj.saved,
                 "text": obj.text,
                }
            return d
        elif isinstance(obj, ReportHistoryDaily):
            return dict(date=obj.day, count=obj.count)
        elif isinstance(obj, ReportHistoryWeekly):
            return dict(date=obj.week, count=obj.count)
        elif isinstance(obj, ReportHistoryMonthly):
            return dict(date=obj.month, count=obj.count)
        elif isinstance(obj, GenericTable):
            return str(obj)
        elif isinstance(obj, set):
            return list(obj)
        else:
            return JSONEncoder.default(self, obj)


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
        if user.admin or user.privileged or user_is_maintainer(db, user.username, component.id):
            is_maintainer = True
    return is_maintainer


def is_problem_maintainer(db, user, problem):
    is_maintainer = app.config["EVERYONE_IS_MAINTAINER"]
    if not is_maintainer and user is not None:
        if user.admin or user.privileged:
            is_maintainer = True
        else:
            component_ids = set(c.id for c in problem.components)
            if any(user_is_maintainer(db, user.username, component_id)
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


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(2)
    return rv
