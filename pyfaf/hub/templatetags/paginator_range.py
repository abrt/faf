from django import template

register = template.Library()

@register.assignment_tag
def get_page_range(current, num_pages, adjacent_pages=2):
    start = max(current - adjacent_pages, 1)
    if start <= 3:
         start = 1

    end = current + adjacent_pages + 1
    if end > num_pages:
        end = num_pages + 1

    page_numbers = [n for n in range(start, end)]
    return page_numbers
