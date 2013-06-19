import datetime

import pyfaf
from pyfaf import queries

from django.template import RequestContext
from django.shortcuts import render_to_response


def by_daterange(request, since, to,
                 template_name='stats/by_date.html',
                 extra_context={}):
    '''
    Render date-based report statistics including reports `since` date
    until `to` date.

    View accepts `template_name` to be used and `extra_context` to pass
    to it.
    '''
    db = pyfaf.storage.getDatabase()
    since = min(since, to)
    to = max(since, to)

    history = 'daily'
    day_count = (to - since).days
    if day_count > 30:
        history = 'weekly'
    if day_count > 360:
        history = 'monthly'

    def date_filter(query):
        return query.filter(hist_field >= since).filter(hist_field < to)

    hist_table, hist_field = queries.get_history_target(history)
    total_query = queries.get_history_sum(db, history=history)
    total = date_filter(total_query).one()[0]

    release_data = []

    for release in queries.get_releases(db):
        release_sum = queries.get_history_sum(
            db, release.opsys.name, release.version, history=history)

        release_sum = date_filter(release_sum).one()[0]
        if not release_sum:
            continue

        percentage = int(release_sum * 100.0 / total)

        comps = queries.get_report_count_per_component(
            db, release.opsys.name, release.version, history=history)

        comp_data = []
        for comp, count in date_filter(comps).all():
            comp_percentage = int(count * 100.0 / release_sum)
            comp_data.append((comp, count, comp_percentage))

        release_data.append({
            'release': release,
            'sum': release_sum,
            'comps': comp_data,
            'percentage': percentage,
        })

    data = {
        'since': since,
        'to': to,
        'total': total,
        'releases': sorted(release_data, key=lambda x: x['sum'], reverse=True),
    }
    data.update(extra_context)

    return render_to_response(template_name,
                              data,
                              context_instance=RequestContext(request))


def by_date(request, year, month=None, day=None,
            template_name='stats/by_date.html',
            extra_context={}):
    '''
    Render date-based report statistics including reports for passed
    `year`, optionaly narrowed to specific `month` and `day`.

    View accepts `template_name` to be used and `extra_context` to pass
    to it.
    '''

    year = int(year)
    if month:
        month = int(month)
    if day:
        day = int(day)

    since = datetime.date(year, 1, 1)
    add = 365

    if month and month in range(1, 12):
        since = since.replace(month=month)
        add = 30

    if day and day in range(1, 32):
        try:
            since = since.replace(day=day)
            add = 1
        except ValueError:
            pass

    to = since + datetime.timedelta(days=add)
    return by_daterange(request, since=since, to=to,
                        template_name=template_name,
                        extra_context=extra_context)
