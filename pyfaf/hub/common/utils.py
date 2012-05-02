from django.core.paginator import Paginator, EmptyPage, InvalidPage

def paginate(objects, request):
    '''
    Pagination short hand function
    '''
    paginator = Paginator(objects, 200)
    try:
        page = int(request.GET.get('page'))
    except (ValueError, TypeError):
        page = 1

    try:
        objs = paginator.page(page)
    except (EmptyPage, InvalidPage):
        objs = paginator.page(paginator.num_pages)

    return objs
