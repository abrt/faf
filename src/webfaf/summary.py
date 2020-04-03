from datetime import date, timedelta
from itertools import groupby
from flask import Blueprint, render_template, request
from sqlalchemy import func

from pyfaf.storage import (OpSys,
                           OpSysRelease,
                           Report)
from pyfaf.queries import get_history_target
from webfaf.webfaf_main import db, flask_cache
from webfaf.forms import SummaryForm, component_names_to_ids

summary = Blueprint("summary", __name__)


def interval_delta(from_date, to_date, resolution):
    if resolution == 'm':
        # Set boundary dates to the first of their corresponding months.
        from_date = date(from_date.year, from_date.month, 1)
        to_date = date(to_date.year, to_date.month, 1)
        delta = func.cast('1 month', INTERVAL)
    elif resolution == 'w':
        # Set boundary dates to Mondays of their corresponding weeks.
        from_date = from_date - timedelta(days=from_date.weekday())
        to_date = to_date - timedelta(days=to_date.weekday())
        delta = timedelta(weeks=1)
    else:
        delta = timedelta(days=1)
    return from_date, to_date, delta


def compute_totals(summary_form):
    component_ids = component_names_to_ids(summary_form.component_names.data)
    from_date, to_date = summary_form.daterange.data
    resolution = summary_form.resolution.data
    table, date_column = get_history_target(summary_form.resolution.data)

    # Generate sequence of days/weeks/months in the specified range.
    from_date, to_date, delta = interval_delta(from_date, to_date, resolution)
    dates = (db.session.query(func.generate_series(from_date, to_date, delta)
                              .label('date'))
             .subquery())

    if summary_form.opsysreleases.data:
        # Query only requested opsys releases.
        releases = (db.session.query(OpSysRelease)
                    .filter(OpSysRelease.id.in_(
                        [osr.id for osr in summary_form.opsysreleases.data]))
                    .subquery())
    else:
        # Query all active opsys releases.
        releases = (db.session.query(OpSysRelease)
                    .filter(OpSysRelease.status != 'EOL')
                    .subquery())

    # Sum daily counts for each date in the range and each opsys release.
    history = (db.session.query(date_column.label('date'),
                                func.sum(table.count).label('count'),
                                table.opsysrelease_id)
               .filter(from_date <= date_column)
               .filter(date_column <= to_date)
               .group_by(table.opsysrelease_id, date_column))

    if component_ids:
        history = history.join(Report).filter(Report.component_id.in_(component_ids))

    history = history.subquery()

    q = (db.session.query(dates.c.date,
                          func.coalesce(history.c.count, 0).label('count'),
                          OpSys.name,
                          releases.c.version)
         .outerjoin(releases, dates.c.date == dates.c.date)
         .outerjoin(history, (history.c.date == dates.c.date) &
                    (history.c.opsysrelease_id == releases.c.id))
         .join(OpSys, OpSys.id == releases.c.opsys_id)
         .order_by(OpSys.id, releases.c.version, dates.c.date))

    for osr, rows in groupby(q.all(), lambda r: f'{r.name} {r.version}'):
        counts = [(r.date, r.count) for r in rows]
        yield osr, counts


def index_plot_data_cache(summary_form):
    key = summary_form.caching_key()

    cached = flask_cache.get(key)
    if cached is not None:
        return cached

    reports = compute_totals(summary_form)

    cached = render_template("summary/index_plot_data.html",
                             reports=reports,
                             resolution=summary_form.resolution.data[0])

    flask_cache.set(key, cached, timeout=60 * 60)
    return cached


@summary.route("/")
def index():
    summary_form = SummaryForm(request.args)

    if summary_form.validate():
        cached_plot = index_plot_data_cache(summary_form)
        return render_template("summary/index.html",
                               summary_form=summary_form,
                               cached_plot=cached_plot)

    return render_template("summary/index.html",
                           summary_form=summary_form,
                           reports=[],
                           resolution=summary_form.resolution.data[0])
