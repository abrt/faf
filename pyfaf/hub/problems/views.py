from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from sqlalchemy import func
from sqlalchemy.sql.expression import desc
import pyfaf
from pyfaf.storage.problem import *
from pyfaf.storage.report import *

def query_problems(time_table):
    db = pyfaf.storage.getDatabase()
    rank_query = db.session.query(Problem.id.label("id"),\
                            func.sum(time_table.count).label("rank"))\
            .join(Report)\
            .join(time_table)\
            .group_by(Problem.id).subquery()

    count_query = db.session.query(Problem.id.label("id"),\
                            func.sum(ReportArch.count).label("count"))\
            .join(Report)\
            .join(ReportArch)\
            .group_by(Problem.id).subquery()

    return db.session.query(Problem.id, Problem.first_occurence.label("first_appearance"), count_query.c.count, rank_query.c.rank)\
            .filter(count_query.c.id==Problem.id)\
            .filter(rank_query.c.id==Problem.id)\
            .order_by(desc(rank_query.c.rank)).all()

def hot(request):
    return render_to_response('problems/hot.html', {"problems":query_problems(ReportHistoryDaily)}, context_instance=RequestContext(request))

def longterm(request):
    return render_to_response('problems/hot.html', {"problems":query_problems(ReportHistoryMonthly)}, context_instance=RequestContext(request))

def summary(request, problem_id):
    return render_to_response('problems/summary.html', {}, context_instance=RequestContext(request))

def backtraces(request):
    return render_to_response('problems/backtraces.html', {}, context_instance=RequestContext(request))

def cluster(request):
    return render_to_response('problems/cluster.html', {}, context_instance=RequestContext(request))
