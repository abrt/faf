import datetime

from sqlalchemy import func
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql.expression import distinct

from pyfaf.storage import (Report,
                           ReportHistoryDaily,
                           ReportHistoryWeekly,
                           ReportHistoryMonthly,
                           OpSys,
                           OpSysRelease,
                           OpSysComponent,
                           OpSysReleaseComponent,
                           OpSysReleaseComponentAssociate,
                           AssociatePeople)

from pyfaf.storage.problem import Problem, ProblemComponent
from pyfaf.hub.common.utils import date_iterator

class ReportHistoryCounts(object):
    def __init__(self, db, osrelease_ids, component_ids, duration_opt):
        self.db = db
        self.osrelease_ids = osrelease_ids
        self.component_ids = component_ids
        self.duration_opt = duration_opt
        self.last_date = datetime.date.today()

        if self.duration_opt == "d":
            self.hist_column = ReportHistoryDaily.day
            self.hist_table = ReportHistoryDaily
        elif self.duration_opt == "w":
            self.hist_column = ReportHistoryWeekly.week
            self.hist_table = ReportHistoryWeekly
        elif self.duration_opt == "m" or self.duration_opt == "*":
            self.hist_column = ReportHistoryMonthly.month
            self.hist_table = ReportHistoryMonthly
        else:
            raise ValueError("Unknown duration option : '%s'" % duration_opt)

    def generate_default_report(self, date):
        '''
        Generates date's report for missing database data
        '''
        pass

    def decorate_report_entry(self, report):
        '''
        Preprocesses database report
        '''
        pass

    def get_min_date(self):
        pass

    def query_all(self, query_obj):
        pass

    def generate_chart_data(self, chart_data, dates):
        '''
        Reports list normalization.

        Add reports for missing dates.
        '''
        reports = iter(chart_data)
        report = next(reports)

        for date in dates:
            if date < report[0]:
                yield self.generate_default_report(date)
            else:
                yield self.decorate_report_entry(report)
                try:
                    report = next(reports)
                except StopIteration:
                    # reports are finished now
                    break

        # generate default reports for remaining dates
        for date in dates:
            yield self.generate_default_report(date)

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
                                                        self.last_date))

        if history_records_set:
            return (report for report in self.generate_chart_data(
                                                                history_records_set,
                                                                displayed_dates_set))

        #else:
        return ((date,0) for date in displayed_dates_set)

def components_list(db, opsysrelease_ids, associate_ids=None):
    '''
    Returns a list of tuples consisting from component's id
    and component's name
    '''
    sub = db.session.query(distinct(Report.component_id)).subquery()
    components_query = (db.session.query(OpSysComponent.id,
                        OpSysComponent.name)
                    .filter(OpSysComponent.id.in_(sub))
                    .order_by(OpSysComponent.name))

    if opsysrelease_ids:
        fsub = (db.session.query(
                distinct(OpSysReleaseComponent.components_id))
                .filter(OpSysReleaseComponent.opsysreleases_id.in_(
                    opsysrelease_ids)))

        components_query = (components_query
            .filter(OpSysComponent.id.in_(fsub)))

    if associate_ids:
        fsub = (db.session.query(
                distinct(OpSysReleaseComponent.components_id))
                .filter(OpSysReleaseComponent.id.in_(
                    db.session.query(OpSysReleaseComponentAssociate.opsysreleasecompoents_id)
                    .filter(OpSysReleaseComponentAssociate.associatepeople_id.in_(associate_ids)))))

        components_query = (components_query
            .filter(OpSysComponent.id.in_(fsub)))

    return components_query.all()

def distro_release_id(db, distro, release):
    '''
    Returns ID of release based on distro name and release name.

    Returns -1 if distro is equal to release meaning all releases.
    '''
    if release == distro.lower():
        return -1

    query = (db.session.query(OpSysRelease.id)
        .join(OpSys)
        .filter(OpSys.name.ilike(distro) &
            (OpSysRelease.version == release))
        .first())

    if query is not None:
        return query[0]

    return None

def all_distros_with_all_releases(db):
    '''
    Return list of tuples of distro name and list of distro release name and release id.
    '''
    return ((distro, [release for release in (db.session.query(OpSysRelease.id, OpSysRelease.version)
                       .join(OpSys)
                       .filter(OpSys.name == distro.name)
                       .filter(OpSysRelease.status != "EOL")
                       .all())])
            for distro in db.session.query(OpSys.name).all())

def associates_list(db, opsysrelease_ids=None):
    '''
    Return a list of user names having any associated component.
    '''
    q = db.session.query(AssociatePeople)

    if opsysrelease_ids:
        q = (q.join(OpSysReleaseComponentAssociate)
              .join(OpSysReleaseComponent)
              .filter(OpSysReleaseComponent.opsysreleases_id.in_(opsysrelease_ids)))

    return q.all()

def query_problems(db, hist_table, hist_column, opsysrelease_ids, component_ids,
                   rank_filter_fn=None, post_process_fn=None):

    rank_query = (db.session.query(Problem.id.label('id'),
                       func.sum(hist_table.count).label('rank'))
                    .join(Report)
                    .join(hist_table)
                    .filter(hist_table.opsysrelease_id.in_(opsysrelease_ids)))

    if rank_filter_fn:
        rank_query = rank_filter_fn(rank_query)

    rank_query = (rank_query.group_by(Problem.id).subquery())

    final_query = (db.session.query(Problem,
                        rank_query.c.rank.label('count'),
                        rank_query.c.rank)
            .filter(rank_query.c.id==Problem.id)
            .order_by(desc(rank_query.c.rank)))

    if len(component_ids) > 0:
        final_query = (final_query.join(ProblemComponent)
            .filter(ProblemComponent.component_id.in_(component_ids)))

    problem_tuples = final_query.all()

    if post_process_fn:
        problems = post_process_fn(problem_tuples);

    for problem, count, rank in problem_tuples:
        problem.count = count

    return [x[0] for x in problem_tuples]
