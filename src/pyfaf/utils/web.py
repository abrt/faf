import logging
from pyfaf.config import config


def webfaf_installed():
    """
    Return True if webfaf is installed
    """

    try:
        import webfaf # pylint: disable=unused-import, unused-variable
        return True
    except: # pylint: disable=bare-except
        return False


def server_url():
    """
    Return web server root URL if applicable
    """

    if webfaf_installed():
        return config.get("hub.url", None)

    logging.warning("Unable to get web server URL, webfaf not available")
    return None


def server_name():
    """
    Return web server root URL if applicable
    """

    if webfaf_installed():
        return config.get("hub.server_name", None)

    logging.warning("Unable to get web server name, webfaf not available")
    return None


def require_https():
    """
    Return if web server requires https (default true)
    """

    if webfaf_installed():
        from pyfaf.utils.parse import str2bool
        return str2bool(config.get("hub.require_https", "true"))

    logging.warning("Unable to get require https option, webfaf not available")
    return True


def reverse(view, **kwargs):
    """
    Return full URL to pointing to `view`
    Wrapper around django"s own reverse.
    """

    if webfaf_installed():
        from flask import url_for
        from webfaf.webfaf_main import app
        app.config["SERVER_NAME"] = server_name()
        app.config['PREFERRED_URL_SCHEME'] = 'https' if require_https() else 'http'
        with app.app_context():
            kwargs["_external"] = True
            return url_for(view, **kwargs)

    logging.warning("Unable to get web server URL, webfaf not available")
    return None
