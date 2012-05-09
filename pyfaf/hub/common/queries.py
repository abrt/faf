import datetime

from sqlalchemy import func
from sqlalchemy.sql.expression import distinct

from pyfaf.storage import (Report,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           OpSysComponent,
                           OpSysReleaseComponent)
from pyfaf.hub.common.utils import date_iterator

class ReportHistoryCounts(object):

    def __init__(self, db, osrelease_ids, component_ids, duration_opt):
        self.db = db
        self.osrelease_ids = osrelease_ids
        self.component_ids = component_ids
        self.duration_opt = duration_opt

        if self.duration_opt == "d":
            self.hist_column = ReportHistoryDaily.day
            self.hist_table = ReportHistoryDaily
        elif self.duration_opt == "w":
            self.hist_column = ReportHistoryWeekly.week
            self.hist_table = ReportHistoryWeekly
        elif self.duration_opt == "m":
            self.hist_column = ReportHistoryMonthly.month
            self.hist_table = ReportHistoryMonthly
        else:
            raise ValueError("Unknown duration option : '%s'" % duration_opt)

    def generate_chart_data(self, chart_data, dates):
        pass

    def get_min_date(self):
        pass

    def query_all(self, query_obj):
        pass

    def report_counts(self):
        """
        Builds a per day report counts query.
        Returns a tuple (query, hist_table, hist_column)
        """
        counts_per_date = (
            self.db.session.query(self.hist_column.label("time"),
                             func.sum(self.hist_table.count).label("count"))
                      .group_by(self.hist_column)
                      .order_by(self.hist_column))

        if self.osrelease_ids:
            counts_per_date = counts_per_date.filter(
                                self.hist_table.opsysrelease_id.in_(self.osrelease_ids))

        if self.component_ids:
            counts_per_date = (counts_per_date
                               .join(Report)
                               .filter(Report.component_id.in_(self.component_ids)))

        history_records_set = self.query_all(counts_per_date)

        displayed_dates_set = (d for d in date_iterator(self.get_min_date(),
                                                        self.duration_opt,
                                                        datetime.date.today()))

        if history_records_set:
            return (report for report in self.generate_chart_data(
                                                                history_records_set,
                                                                displayed_dates_set))

        #else:
        return ((date,0) for date in displayed_dates)

def components_list(db, opsysrelease_ids):
    '''
    Returns a list with tuples consisting from compoent's id and component's name
    '''
    components_query = (db.session.query(OpSysComponent.id, OpSysComponent.name).
                    filter(OpSysComponent.id.in_(
                        db.session.query(distinct(Report.component_id)).subquery())).
                    order_by(OpSysComponent.name))

    if opsysrelease_ids:
            components_query = (components_query.filter(OpSysComponent.id.in_(
                db.session.query(distinct(OpSysReleaseComponent.components_id))
                    .filter(OpSysReleaseComponent.opsysreleases_id.in_(opsysrelease_ids)))))

    return components_query.all()
