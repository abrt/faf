from pyfaf.storage.opsys import (OpSys,
                                 OpSysRelease,
                                 OpSysReleaseComponent,
                                 OpSysComponent)

from pyfaf.storage.report import (Report,
                                  ReportHistoryDaily, ReportHistoryWeekly,
                                  ReportHistoryMonthly)

from sqlalchemy import func, desc


def get_history_target(target='daily'):
    '''
    Return tuple of `ReportHistory(Daily|Weekly|Monthly)` and
    proper date field `ReportHistory(Daily.day|Weekly.week|Monthly.month)`
    according to `target` parameter which should be one of
    `daily|weekly|monthly` or shortened version `d|w|m`.
    '''
    if target == 'd' or target == 'daily':
        return (ReportHistoryDaily, ReportHistoryDaily.day)

    if target == 'w' or target == 'weekly':
        return (ReportHistoryWeekly, ReportHistoryWeekly.week)

    return (ReportHistoryMonthly, ReportHistoryMonthly.month)


def query_releases(db, opsys_name=None, opsys_version=None):
    '''
    Return query of `OpSysRelease` records optionaly filtered
    by `opsys_name` and `opsys_version`.
    '''
    opsysquery = (
        db.session.query(OpSysRelease)
        .join(OpSys))

    if opsys_name:
        opsysquery = opsysquery.filter(OpSys.name == opsys_name)

    if opsys_version:
        opsysquery = opsysquery.filter(OpSysRelease.version == opsys_version)

    return opsysquery


def query_release_ids(db, opsys_name=None, opsys_version=None):
    '''
    Return list of `OpSysRelease` ids optionaly filtered
    by `opsys_name` and `opsys_version`.
    '''
    return [opsysrelease.id for opsysrelease in
            query_releases(db, opsys_name, opsys_version).all()]


def query_history_sum(db, opsys_name=None, opsys_version=None,
                      history='daily'):
    '''
    Return query summing ReportHistory(Daily|Weekly|Monthly)
    records optinaly filtered by `opsys_name` and `opsys_version`.
    '''

    opsysrelease_ids = query_release_ids(db, opsys_name, opsys_version)
    hist_table, hist_field = get_history_target(history)
    hist_sum = db.session.query(func.sum(hist_table.count).label('cnt'))
    if opsysrelease_ids:
        hist_sum = hist_sum.filter(
            hist_table.opsysrelease_id.in_(opsysrelease_ids))

    return hist_sum


def query_report_count_per_component(db, opsys_name=None, opsys_version=None,
                                     history='daily'):
    '''
    Return query for `OpSysComponent` and number of reports this
    component received.

    It's possible to filter the results by `opsys_name` and
    `opsys_version`.
    '''

    opsysrelease_ids = query_release_ids(db, opsys_name, opsys_version)
    hist_table, hist_field = get_history_target(history)

    comps = (
        db.session.query(OpSysComponent,
                         func.sum(hist_table.count).label('cnt'))
        .join(Report)
        .join(hist_table)
        .group_by(OpSysComponent)
        .order_by(desc('cnt')))

    if opsysrelease_ids:
        comps = comps.filter(hist_table.opsysrelease_id.in_(opsysrelease_ids))

    return comps


def query_report_stats_per_component(db, component, history='daily'):
    '''
    Return query with reports for `component` along with
    summed counts from `history` table (one of daily/weekly/monthly).
    '''
    hist_table, hist_field = get_history_target(history)

    return (db.session.query(Report,
                             func.sum(hist_table.count).label('cnt'))
            .join(hist_table)
            .join(OpSysComponent)
            .filter(OpSysComponent.id == component.id)
            .group_by(Report)
            .order_by(desc('cnt')))
