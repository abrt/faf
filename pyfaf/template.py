import os

import pyfaf

from django.template import Context, Template


def render(template_name, data, strip=True):
    '''
    Render template with `template_name` using `data` dictionary.

    Will strip whitespaces from the beggining and the end of
    rendered result. Disable with `strip=False`.

    Template directory is configured with `Main.TemplatesDir` variable.

    Additional data (configuration values) passed to templates:
        `Hub.ServerUrl`
        `Hub.ServerEmail`
    '''
    templates_dir = pyfaf.config.get('main.templatesdir')
    template_path = os.path.join(templates_dir, template_name)
    with open(template_path, 'r') as template_file:
        template_str = template_file.read()

    template = Template(template_str)

    defaults = dict(server_url=pyfaf.config.get('hub.serverurl'),
                    server_email=pyfaf.config.get('hub.serveremail'))
    defaults.update(data)

    rendered = template.render(Context(defaults))
    if strip:
        rendered = rendered.strip()

    return rendered
