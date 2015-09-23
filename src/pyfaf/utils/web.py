import os
import logging
from pyfaf.config import config


def webfaf_installed():
    """
    Return True if webfaf is installed
    """

    try:
        import webfaf
        return True
    except:
        return False


def server_url():
    """
    Return web server root URL if applicable
    """

    if webfaf_installed():
        return config.get("hub.url", None)
    else:
        logging.warn("Unable to get web server URL, webfaf not available")
        return None


def server_name():
    """
    Return web server root URL if applicable
    """

    if webfaf_installed():
        return config.get("hub.server_name", None)
    else:
        logging.warn("Unable to get web server name, webfaf not available")
        return None


def reverse(view, **kwargs):
    """
    Return full URL to pointing to `view`
    Wrapper around django"s own reverse.
    """

    if webfaf_installed():
        from flask import url_for
        from webfaf.webfaf_main import app
        app.config["SERVER_NAME"] = server_name()
        with app.app_context():
            kwargs["_external"] = True
            return url_for(view, **kwargs)
    else:
        logging.warn("Unable to get web server URL, webfaf not available")
        return None
