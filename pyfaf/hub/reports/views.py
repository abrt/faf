import os
import uuid
import json
import pyfaf

from django.core.urlresolvers import reverse
from django.contrib.sites.models import RequestSite
from django.http import HttpResponse, Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt

from sqlalchemy import func
from sqlalchemy.sql.expression import desc, literal

from pyfaf import ureport
from pyfaf.storage.opsys import (OpSys,
                                 OpSysRelease,
                                 OpSysComponent,
                                 Package,
                                 Build)
from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportOpSysRelease,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly,
                                  ReportPackage,
                                  ReportUnknownPackage)
from pyfaf.hub.common.utils import paginate
from pyfaf.hub.common.forms import OsComponentFilterForm

from pyfaf.hub.reports.forms import (NewReportForm, ReportFilterForm)

def index(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)

    form = OsComponentFilterForm(db, params)

    release_ids = map(lambda x: x[0], form.get_release_selection())
    # flatten
    release_ids = [item for sublist in release_ids for item in sublist]


    counts_query = (db.session.query(
            func.sum(ReportHistoryMonthly.count),
            OpSysRelease)
        .join(OpSysRelease)
        .filter(OpSysRelease.id.in_(release_ids))
        .group_by(OpSysRelease))

    component_ids = form.get_component_selection()

    if component_ids:
        counts_query = (counts_query
            .join(Report)
            .filter(Report.component_id.in_(component_ids)))

    forward = {'releases' : counts_query.all(), 'form': form}

    return render_to_response('reports/index.html',
            forward, context_instance=RequestContext(request))

def listing(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = ReportFilterForm(db, params)

    filters = { 'new'   : (lambda q: q.filter(Report.problem_id==None)),
                'fixed' : (lambda q: q.filter(Report.problem_id!=None)) }

    states = None
    for s in form.get_status_selection():
        # if 's' isn't in filters exceptions is thrown
        # it is intended behaviour - someone has to take care about it
        subquery = filters[s](db.session.query(
                                Report.id.label('id'),
                                literal(s.upper()).label('status')))
        states = states.union_all(subquery) if states else subquery

    # if list of statuses is empty the states variable is None
    # it means that no reports are to be selected
    # hope that there will never be a Report with id equal to -1
    if not states:
        states = (db.session.query(literal(-1).label('id'),
                                   literal('').label('status')))

    states = states.subquery()

    opsysrelease_id = form.os_release_id
    reports = (db.session.query(Report.id, literal(0).label('rank'),
            states.c.status, Report.first_occurence.label('created'),
            Report.last_occurence.label('last_change'),
            OpSysComponent.name.label('component'), Report.type)
        .join(ReportOpSysRelease)
        .join(OpSysComponent)
        .filter(states.c.id==Report.id)
        .filter((ReportOpSysRelease.opsysrelease_id==opsysrelease_id) |
            (opsysrelease_id==-1))
        .order_by(desc('last_change')))

    component_ids = form.get_component_selection()
    if component_ids:
        reports = reports.filter(Report.component_id.in_(component_ids))

    reports = reports.all()

    i = 1
    for rep in reports:
        rep.rank = i
        i += 1

    reports = paginate(reports, request)
    forward = {'reports' : reports,
               'form'  : form}

    return render_to_response('reports/list.html',
        forward, context_instance=RequestContext(request))

def load_packages(db, report_id, package_type):
    build_fn = lambda prefix, column : (db.session.query(ReportPackage.id.label('%sid' % (prefix)),
                                                           Package.id.label('%spackage_id' % (prefix)),
                                                           Package.name.label('%sname' % (prefix)),
                                                           Build.version.label('%sversion' % (prefix)),
                                                           Build.release.label('%srelease' % (prefix)),
                                                           Build.epoch.label('%sepoch' % (prefix)))
                            .filter(Build.id==Package.build_id)
                            .filter(ReportPackage.report_id==report_id)
                            .filter(Package.id==column)
                            .filter(ReportPackage.type==package_type)
                            .subquery())

    installed_packages = build_fn("i", ReportPackage.installed_package_id)
    running_packages = build_fn("r", ReportPackage.running_package_id)

    known_packages = (db.session.query( ReportPackage.id,
                              installed_packages.c.ipackage_id, running_packages.c.rpackage_id,
                              installed_packages.c.iname,       running_packages.c.rname,
                              installed_packages.c.iversion,    running_packages.c.rversion,
                              installed_packages.c.irelease,    running_packages.c.rrelease,
                              installed_packages.c.iepoch,      running_packages.c.repoch,
                              ReportPackage.count)
        .outerjoin(installed_packages, ReportPackage.id==installed_packages.c.iid)
        .outerjoin(running_packages, ReportPackage.id==running_packages.c.rid)
        .filter(ReportPackage.report_id==report_id)
        .filter((installed_packages.c.iid!=None) | (running_packages.c.rid!=None)))
    unknown_packages = (db.session.query(ReportUnknownPackage.id,
                              literal(None).label("ipackage_id"), literal(None).label("rpackage_id"),
                              ReportUnknownPackage.name.label("iname"), ReportUnknownPackage.name.label("rname"),
                              ReportUnknownPackage.installed_version.label("iversion"), ReportUnknownPackage.running_version.label("rversion"),
                              ReportUnknownPackage.installed_release.label("irelease"), ReportUnknownPackage.running_release.label("rrelease"),
                              ReportUnknownPackage.installed_epoch.label("iepoch"), ReportUnknownPackage.running_epoch.label("repoch"),

                              ReportUnknownPackage.count)
        .filter(ReportUnknownPackage.type==package_type)
        .filter(ReportUnknownPackage.report_id==report_id))

    return known_packages.union(unknown_packages).all()

def item(request, report_id):
    db = pyfaf.storage.getDatabase()
    report, component = (db.session.query(Report, OpSysComponent)
        .join(OpSysComponent)
        .filter(Report.id==report_id)
        .first())

    releases = (db.session.query(ReportOpSysRelease, OpSysRelease, OpSys)
        .join(OpSysRelease)
        .join(OpSys)
        .filter(ReportOpSysRelease.report_id==report_id)
        .all())

    arches = (db.session.query(ReportArch)
        .filter(ReportArch.report_id==report_id)
        .all())

    if report is None:
        raise Http404

    history_select = lambda table : (db.session.query(table).
        filter(table.report_id==report_id)
        .all())

    daily_history = history_select(ReportHistoryDaily)
    weekly_history = history_select(ReportHistoryWeekly)
    monthly_history = history_select(ReportHistoryMonthly)

    packages = load_packages(db, report_id, "CRASHED")
    related_packages = load_packages(db, report_id, "RELATED")

    return render_to_response('reports/item.html',
                                {'report': report,
                                 'component': component,
                                 'releases': releases,
                                 'arches': arches,
                                 'daily_history': daily_history,
                                 'weekly_history': weekly_history,
                                 'monthly_history': monthly_history,
                                 'crashed_packages': packages,
                                 'related_packages': related_packages,
                                 'backtrace': report.backtraces[0].frames},
                                context_instance=RequestContext(request))

# This function gets notification responses according to specification on
# http://json-rpc.org/wiki/specification
@csrf_exempt
def new(request):
    if request.method == 'POST':
        form = NewReportForm(request.POST, request.FILES)
        if form.is_valid():
            db = pyfaf.storage.getDatabase()
            report = form.cleaned_data['file']['converted']
            try:
                dbreport = ureport.is_known(report, db, return_report=True)
            except:
                dbreport = None

            known = bool(dbreport)
            spool_dir = pyfaf.config.get('Report.SpoolDirectory')
            fname = str(uuid.uuid4())
            with open(os.path.join(spool_dir, 'incoming', fname), 'w') as fil:
                fil.write(form.cleaned_data['file']['json'])

            if 'application/json' in request.META.get('HTTP_ACCEPT'):
                response = {'result': known }

                try:
                    if "component" in report:
                        component = ureport.get_component(report['component'], report['os'], db)
                    else:
                        component = ureport.guess_component(report['installed_package'], report['os'], db)

                    if component:
                        response['bthash'] = ureport.get_report_hash(report, component.name)[1]
                except:
                    # ToDo - log the exception somehow
                    pass

                if known:
                    site = RequestSite(request)
                    url = reverse('pyfaf.hub.reports.views.item', args=[dbreport.id])
                    response['message'] = "https://{0}{1}".format(site.domain, url)

                return HttpResponse(json.dumps(response),
                    mimetype='application/json')

            return render_to_response('reports/success.html',
                {'report': report, 'known': known},
                context_instance=RequestContext(request))
        else:
            err = form.errors['file'][0]
            if 'application/json' in request.META.get('HTTP_ACCEPT'):
                response = {'error' : err}
                return HttpResponse(json.dumps(response),
                status=400, mimetype='application/json')

            return render_to_response('reports/new.html', {'form': form},
                context_instance=RequestContext(request))
    else:
        form = NewReportForm()

    return render_to_response('reports/new.html', {'form': form},
        context_instance=RequestContext(request))
