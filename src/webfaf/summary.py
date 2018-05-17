from operator import itemgetter
from pyfaf.storage import (Report,
                           OpSysRelease)
from pyfaf.queries import get_history_target
from flask import Blueprint, render_template, request
from sqlalchemy import func


summary = Blueprint("summary", __name__)

from webfaf.webfaf_main import db, flask_cache
from webfaf.forms import SummaryForm, component_names_to_ids
from webfaf.utils import date_iterator


def index_plot_data_cache(summary_form):
    key = summary_form.caching_key()

    cached = flask_cache.get(key)
    if cached is not None:
        return cached

    reports = []

    hist_table, hist_field = get_history_target(
        summary_form.resolution.data)

    component_ids = component_names_to_ids(summary_form.component_names.data)

    (since_date, to_date) = summary_form.daterange.data

    if summary_form.opsysreleases.data:
        opsysreleases = summary_form.opsysreleases.data
    else:
        opsysreleases = (
            db.session.query(OpSysRelease)
            .filter(OpSysRelease.status != "EOL")
            .order_by(OpSysRelease.releasedate)
            .all())

    for osr in opsysreleases:
        counts = (
            db.session.query(hist_field.label("time"),
                             func.sum(hist_table.count).label("count"))
            .group_by(hist_field)
            .order_by(hist_field))

        counts = counts.filter(hist_table.opsysrelease_id == osr.id)

        if component_ids:
            counts = (counts.join(Report)
                      .filter(Report.component_id.in_(component_ids)))

        counts = (counts.filter(hist_field >= since_date)
                  .filter(hist_field <= to_date))

        counts = counts.all()

        dates = set(date_iterator(since_date,
                                  summary_form.resolution.data,
                                  to_date))

        for time, count in counts:
            dates.remove(time)
        for date in dates:
            counts.append((date, 0))
        counts = sorted(counts, key=itemgetter(0))
        reports.append((str(osr), counts))

    cached = render_template("summary/index_plot_data.html",
                             reports=reports,
                             resolution=summary_form.resolution.data[0])

    flask_cache.set(key, cached, timeout=60*60)
    return cached


@summary.route("/")
def index():
    summary_form = SummaryForm(request.args)
    reports = []
    if summary_form.validate():

        index_plot_data = index_plot_data_cache(summary_form)
        return render_template("summary/index.html",
                               summary_form=summary_form,
                               index_plot_data=index_plot_data)

    return render_template("summary/index.html",
                           summary_form=summary_form,
                           reports=reports,
                           resolution=summary_form.resolution.data[0])
