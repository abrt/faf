from django import template

register = template.Library()

class PageRangeNode(template.Node):
    def __init__(self, current_var, num_pages_var, adjacent_var):
        self.current_var = current_var
        self.adjacent_var = adjacent_var
        self.num_pages_var = num_pages_var

    def render(self, context):
        current = self.current_var.resolve(context)
        adjacent_pages = self.adjacent_var.resolve(context)
        num_pages = self.num_pages_var.resolve(context)

        start = max(current - adjacent_pages, 1)
        if start <= 3:
             start = 1

        end = current + adjacent_pages + 1
        if end > num_pages:
            end = num_pages + 1

        page_numbers = [n for n in range(start, end)]

        context['range'] = page_numbers
        return ''

@register.tag
def get_page_range(parser, token):
    bits = token.split_contents()[1:]

    if len(bits) != 3:
        raise template.TemplateSyntaxError(
            "'get_page_range' tag takes exactly 3 arguments")

    return PageRangeNode(*map(template.Variable, bits))
