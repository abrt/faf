import os
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webfaf.settings")


def webfaf_installed():
    """
    Return True if webfaf is installed
    """

    try:
        from django.contrib.sites.models import Site
        Site.objects.get_current()
        return True
    except:
        return False


def server_url():
    """
    Return web server root URL if applicable
    """

    if webfaf_installed():
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        return "http://" + site.domain
    else:
        logging.warn("Unable to get web server URL, webfaf not available")
        return None


def reverse(view, *args, **kwargs):
    """
    Return full URL to pointing to `view`
    Wrapper around django"s own reverse.
    """

    if webfaf_installed():
        mainurl = server_url()
        from django.core.urlresolvers import reverse

        return mainurl + reverse(view, *args, **kwargs)
    else:
        logging.warn("Unable to get web server URL, webfaf not available")
        return None
