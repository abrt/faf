import datetime
import types
import itertools

from django.core.paginator import Paginator, EmptyPage, InvalidPage
from json import JSONEncoder
from pyfaf.storage import GenericTable
from pyfaf.storage.problem import Problem

def split_distro_release(inp):
    '''
    Returns decomposed distro, release names.

    fedora results in (fedora, fedora) meaning all releases,
    fedora-17 results in (fedora, 17).
    '''
    distro = release = inp
    if '-' in inp and inp[-1].isdigit():
        distro, release = inp.rsplit("-", 1)

    return (distro, release)

def paginate(objects, request):
    '''
    Pagination short hand function
    '''
    paginator = Paginator(objects, 200)
    try:
        page = int(request.GET.get('page'))
    except (ValueError, TypeError):
        page = 1

    try:
        objs = paginator.page(page)
    except (EmptyPage, InvalidPage):
        objs = paginator.page(paginator.num_pages)

    return objs

def date_iterator(first_date, time_unit='d', end_date=None):
    '''
    Iterates from date until reaches end date or never finishes
    '''
    if time_unit == 'd':
        next_date_fn = lambda x : x + datetime.timedelta(days=1)
    elif time_unit == 'w':
        first_date -= datetime.timedelta(days=first_date.weekday())
        next_date_fn = lambda x : x + datetime.timedelta(weeks=1)
    elif time_unit == 'm' or time_unit == '*':
        first_date = first_date.replace(day=1)
        next_date_fn = lambda x : (x.replace(day=25) +
            datetime.timedelta(days=7)).replace(day=1)
    else:
        raise ValueError('Unknown time unit type : "%s"' % time_unit)

    toreturn = first_date
    yield toreturn
    while True:
        toreturn = next_date_fn(toreturn)
        if not end_date is None and toreturn > end_date:
            break

        yield toreturn

def unique(seq, idfun=None):
    '''
    Return unique values of `seq` with preserved order.

    idfun can be used to specify unique part of the item (useful for tuples).
    '''
    if idfun is None:
        idfun = lambda x: x[0]
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result

def flatten(l, ltypes=(list, tuple)):
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    if ltype == types.GeneratorType:
        return l
    return ltype(l)

def diff(lhs_seq, rhs_seq, eq = None):
    '''
    Computes a diff of two sequences.

    Algorithm is based on Longest Common Subsequence problem.

    Returns a list of pairs. Each pair consists from either a value from the
    first sequence and None or from None and a value from the second sequence
    or values from both sequences.

    >>> diff(banana, ananas)
    [('b', None), ('a', 'a'), ('n', 'n'), ('a', 'a'), ('n', 'n'), ('a', 'a'), (None, 's')]
    '''
    if not eq:
        eq = lambda x,y: x == y

    result = list()
    l = 0
    l_e = len(lhs_seq) - 1
    r = 0
    r_e = len(rhs_seq) - 1
    # handle common prefix
    while l <= l_e and r <= r_e and eq(lhs_seq[l], rhs_seq[r]):
        result.append((lhs_seq[l], rhs_seq[r]))
        l +=1
        r +=1

    end_result = list()
    # handle common suffix
    while l <= l_e and r <= r_e and eq(lhs_seq[l_e], rhs_seq[r_e]):
        end_result.append((lhs_seq[l_e], rhs_seq[r_e]))
        l_e -=1
        r_e -=1

    matrix_row_len = (r_e - r) + 2
    # build matrix which has one more column and line than rhs x lhs
    m = list(itertools.repeat(0, ((l_e - l) + 2) * matrix_row_len))

    # skip first row because it contains only 0
    pos = matrix_row_len

    # in case where strings are the same l has value len(left) == l_e + 1
    i = l_e
    # in case where strings are the same r has value len(right) == r_e + 1
    j = r_e

    for i in xrange(l, l_e + 1):
        pos += 1 # skip first column which is always 0
        for j in xrange(r, r_e + 1):
            if eq(lhs_seq[i], rhs_seq[j]):
                res = m[pos - matrix_row_len - 1] + 1
            else:
                res = max(m[pos - matrix_row_len], m[pos - 1])
            m[pos] = res
            pos += 1

    pos -= 1 # current value is len(m)
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
                 "bugs": [bug.url for bug in obj.bugs]}
            if hasattr(obj, "count"):
                d["count"] = obj.count
            return d
        elif isinstance(obj, GenericTable):
            return str(obj)
        elif isinstance(obj, set):
            return list(obj)
        else:
            return JSONEncoder.default(self, obj)
