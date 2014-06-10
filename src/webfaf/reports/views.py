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
from pyfaf.config import config
from pyfaf.kb import find_solution
from pyfaf.local import var
from pyfaf.problemtypes import problemtypes
from pyfaf.storage.opsys import (OpSys,
                                 OpSysRelease,
                                 OpSysComponent,
                                 Package,
                                 Build)
from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportBtHash,
                                  ReportOpSysRelease,
                                  ReportSelinuxMode,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly,
                                  ReportPackage,
                                  ReportBz,
                                  ReportUnknownPackage)
from pyfaf.storage.debug import InvalidUReport
from pyfaf.ureport import ureport2

from pyfaf.common import FafError
from webfaf.common.utils import paginate, diff
from webfaf.common.forms import OsComponentFilterForm

from webfaf.reports.forms import (NewReportForm,
                                  NewAttachmentForm,
                                  ReportFilterForm)

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

    filters = { 'new'       : (lambda q: q.filter(Report.problem_id==None)),
                'processed' : (lambda q: q.filter(Report.problem_id!=None)) }

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
            states.c.status, Report.first_occurrence.label('created'),
            Report.last_occurrence.label('last_change'),
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
    result = (db.session.query(Report, OpSysComponent)
        .join(OpSysComponent)
        .filter(Report.id==report_id)
        .first())

    if result is None:
        raise Http404

    report, component = result

    releases = (db.session.query(ReportOpSysRelease, ReportOpSysRelease.count)
        .filter(ReportOpSysRelease.report_id==report_id)
        .order_by(desc(ReportOpSysRelease.count))
        .all())

    arches = (db.session.query(ReportArch, ReportArch.count)
        .filter(ReportArch.report_id==report_id)
        .order_by(desc(ReportArch.count))
        .all())

    modes = (db.session.query(ReportSelinuxMode, ReportSelinuxMode.count)
        .filter(ReportSelinuxMode.report_id==report_id)
        .order_by(desc(ReportSelinuxMode.count))
        .all())

    history_select = lambda table : (db.session.query(table).
        filter(table.report_id==report_id)
        .all())

    daily_history = history_select(ReportHistoryDaily)
    weekly_history = history_select(ReportHistoryWeekly)
    monthly_history = history_select(ReportHistoryMonthly)

    packages = load_packages(db, report_id, "CRASHED")
    related_packages = load_packages(db, report_id, "RELATED")

    try:
        backtrace = report.backtraces[0].frames
    except:
        backtrace = []

    fid = 0
    for frame in backtrace:
        fid += 1
        frame.nice_order = fid

    return render_to_response('reports/item.html',
                                {'report': report,
                                 'component': component,
                                 'releases': releases,
                                 'arches': arches,
                                 'modes': modes,
                                 'daily_history': daily_history,
                                 'weekly_history': weekly_history,
                                 'monthly_history': monthly_history,
                                 'crashed_packages': packages,
                                 'related_packages': related_packages,
                                 'backtrace': backtrace},
                                context_instance=RequestContext(request))

def diff(request, lhs_id, rhs_id):
    db = pyfaf.storage.getDatabase()
    lhs = (db.session.query(Report)
        .filter(Report.id==lhs_id)
        .first())

    rhs = (db.session.query(Report)
        .filter(Report.id==rhs_id)
        .first())

    if lhs is None or rhs is None:
        raise Http404

    frames_diff = diff(lhs.backtraces[0].frames,
                       rhs.backtraces[0].frames,
                       lambda lhs, rhs:
                       lhs.symbolsource.symbol == rhs.symbolsource.symbol)

    return render_to_response('reports/diff.html',
                                {'diff': frames_diff,
                                 'lhs': {'id': lhs_id, 'type': lhs.type},
                                 'rhs': {'id': rhs_id, 'type': rhs.type}},
                                 context_instance=RequestContext(request))


def get_spool_dir(subdir):
    if "ureport.directory" in config:
        basedir = config["ureport.directory"]
    elif "report.spooldirectory" in config:
        basedir = config["report.spooldirectory"]
    else:
        basedir = os.path.join(var, "spool", "faf")

    return os.path.join(basedir, subdir)


# This function gets notification responses according to specification on
# http://json-rpc.org/wiki/specification
@csrf_exempt
def new(request):
    if request.method == 'POST':
        form = NewReportForm(request.POST, request.FILES)
        if form.is_valid():
            db = pyfaf.storage.getDatabase()
            report = form.cleaned_data['file']['converted']

            # maybe determine it better?
            max_ureport_length = InvalidUReport.__lobs__["ureport"]

            if len(str(report)) > max_ureport_length:
                err = "uReport may only be {0} bytes long".format(max_ureport_length)
                if "application/json" in request.META.get("HTTP_ACCEPT"):
                    return HttpResponse(json.dumps({"error": err}),
                                        status=413, mimetype="application/json")

                return HttpResponse(err, status=413, mimetype="application/json")

            try:
                dbreport = ureport.is_known(report, db, return_report=True)
            except:
                dbreport = None

            known = bool(dbreport)
            spool_dir = get_spool_dir("reports")
            fname = str(uuid.uuid4())
            with open(os.path.join(spool_dir, 'incoming', fname), 'w') as fil:
                fil.write(form.cleaned_data['file']['json'])

            if 'application/json' in request.META.get('HTTP_ACCEPT'):
                response = {'result': known }

                opsys_id = None
                opsys = db.session.query(OpSys).filter(OpSys.name == report["os"]["name"]).first()
                if opsys:
                    opsys_id = opsys.id

                try:
                    report2 = ureport2(report)
                except FafError:
                    report2 = None

                if report2 is not None:
                    solution = find_solution(report2, db=db)
                    if solution is not None:
                        response['message'] = ("Your problem seems to be caused by {0}\n\n"
                                               "{1}".format(solution.cause, solution.note_text))
                        if solution.url:
                            response['message'] += ("\n\nYou can get more information at {0}"
                                                    .format(solution.url))

                        response['solutions'] = [{'cause': solution.cause,
                                                  'note':  solution.note_text,
                                                  'url':   solution.url}]
                        response['result'] = True

                    try:
                        problemplugin = problemtypes[report2["problem"]["type"]]
                        response["bthash"] = problemplugin.hash_ureport(report2["problem"])
                    except:
                        # ToDo - log the exception somehow
                        pass

                if known:
                    site = RequestSite(request)
                    url = reverse('webfaf.reports.views.item', args=[dbreport.id])
                    parts = [{"reporter": "ABRT Server",
                              "value": "https://{0}{1}".format(site.domain, url),
                              "type": "url"}]

                    bugs = db.session.query(ReportBz).filter(ReportBz.report_id == dbreport.id).all()
                    for bug in bugs:
                        parts.append({"reporter": "Bugzilla",
                                      "value": bug.url,
                                      "type": "url"})

                    if not 'message' in response:
                        response['message'] = ''
                    else:
                        response['message'] += '\n\n'

                    response['message'] += "\n".join(p["value"] for p in parts if p["type"].lower() == "url")
                    response['reported_to'] = parts

                return HttpResponse(json.dumps(response),
                    status=202,
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

@csrf_exempt
def attach(request):
    if request.method == 'POST':
        form = NewAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.cleaned_data['file']['json']

            # determine it better
            max_attachment_length = 2048

            if len(str(attachment)) > max_attachment_length:
                err = "uReport attachment may only be {0} bytes long" \
                      .format(max_attachment_length)

                if "application/json" in request.META.get("HTTP_ACCEPT"):
                    return HttpResponse(json.dumps({"error": err}),
                                        status=413, mimetype="application/json")

                return HttpResponse(err, status=413, mimetype="application/json")

            spool_dir = get_spool_dir("attachments")

            fname = str(uuid.uuid4())

            with open(os.path.join(spool_dir, "incoming", fname), "w") as fil:
                fil.write(attachment)

            if 'application/json' in request.META.get('HTTP_ACCEPT'):

                return HttpResponse(json.dumps({"result": True}),
                    status=202, mimetype='application/json')

            return render_to_response('reports/attach_success.html',
                {},
                context_instance=RequestContext(request))
        else:
            err = form.errors['file'][0]
            if 'application/json' in request.META.get('HTTP_ACCEPT'):
                response = {'error' : err}
                return HttpResponse(json.dumps(response),
                status=400, mimetype='application/json')

            return render_to_response('reports/attach.html', {'form': form},
                context_instance=RequestContext(request))
    else:
        form = NewAttachmentForm()

    return render_to_response('reports/attach.html', {'form': form},
        context_instance=RequestContext(request))

def bthash_forward(request, bthash):
    db = pyfaf.storage.getDatabase()
    reportbt = db.session.query(ReportBtHash).filter(ReportBtHash.hash == bthash).first()
    if reportbt is None:
        raise Http404

    if (reportbt.backtrace is None or
        reportbt.backtrace.report is None):
        return render_to_response("reports/waitforit.html")

    response = HttpResponse(status=302)
    response["Location"] = reverse('webfaf.reports.views.item',
                                   args=[reportbt.backtrace.report.id])

    return response

def invalid(request):
    if not request.user.is_staff:
        raise Http404

    db = pyfaf.storage.getDatabase()
    reports = (db.session.query(InvalidUReport)
                         .order_by(desc(InvalidUReport.date))
                         .all())

    return render_to_response("reports/invalid.html",
        {"reports": paginate(reports, request)},
        context_instance=RequestContext(request))

def invalid_item(request, report_id):
    if not request.user.is_staff:
        raise Http404

    db = pyfaf.storage.getDatabase()
    report = (db.session.query(InvalidUReport)
                        .filter(InvalidUReport.id == report_id)
                        .first())

    if report is None:
        raise Http404

    return render_to_response("reports/invalid_item.html",
        {"report": report, "report_data": report.get_lob("ureport")},
        context_instance=RequestContext(request))
