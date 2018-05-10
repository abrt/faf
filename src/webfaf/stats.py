import datetime

from pyfaf import queries
from webfaf.utils import cache, request_wants_json

from flask import (Blueprint, render_template, abort, redirect,
                   url_for, jsonify)

from webfaf.webfaf_main import db
import six

stats = Blueprint("stats", __name__)


@stats.errorhandler(400)
def bad_request(error):
    return "Wrong date format", 400


@stats.route('/')
def redir():
    return redirect(url_for("stats.today"), code=302)


@stats.route("/today/", endpoint="today",
             defaults={
                 'since': datetime.date.today(),
                 'to': datetime.date.today() + datetime.timedelta(days=1)})
@stats.route("/yesterday/", endpoint="yesterday",
             defaults={
                 'since': datetime.date.today() - datetime.timedelta(days=1),
                 'to': datetime.date.today()})
@stats.route("/last_week/", endpoint="last_week",
             defaults={
                 'since': datetime.date.today() - datetime.timedelta(days=7),
                 'to': datetime.date.today()})
@stats.route("/last_month/", endpoint="last_month",
             defaults={
                 'since': datetime.date.today() - datetime.timedelta(days=30),
                 'to': datetime.date.today()})
@stats.route("/last_year/", endpoint="last_year",
             defaults={
                 'since': datetime.date.today() - datetime.timedelta(days=365),
                 'to': datetime.date.today()})
@stats.route("/daterange/<since>/<to>/", endpoint="daterange")
@cache(hours=1)
def by_daterange(since, to):
    '''
    Render date-based report statistics including reports `since` date
    until `to` date.
    '''

    try:
        if isinstance(since, six.string_types):
            since = datetime.datetime.strptime(since, "%Y-%m-%d").date()

        if isinstance(to, six.string_types):
            to = datetime.datetime.strptime(to, "%Y-%m-%d").date()
    except:
        return abort(400)

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

        comps = queries.get_report_count_by_component(
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

    if request_wants_json():
        return jsonify(data)

    return render_template("stats/by_date.html", **data)


@stats.route("/date/<year>/", endpoint="year_stats")
@stats.route("/date/<year>/<month>/", endpoint="month_stats")
@stats.route("/date/<year>/<month>/<day>/", endpoint="day_stats")
@cache(hours=1)
def by_date(year, month=None, day=None):
    '''
    Render date-based report statistics including reports for passed
    `year`, optionaly narrowed to specific `month` and `day`.
    '''

    year = int(year)
    if month:
        month = int(month)
    if day:
        day = int(day)

    since = datetime.date(year, 1, 1)
    add = 365

    if month and month in range(1, 13):
        since = since.replace(month=month)
        add = 30

    if day and day in range(1, 32):
        try:
            since = since.replace(day=day)
            add = 1
        except ValueError:
            pass

    to = since + datetime.timedelta(days=add)
    return by_daterange(since=since, to=to)
