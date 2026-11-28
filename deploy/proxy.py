"""Trusted proxy middleware setup for the single local Nginx proxy."""

from werkzeug.middleware.proxy_fix import ProxyFix


def trust_local_nginx(wsgi_app):
    """Trust the client IP and scheme forwarded by the local Nginx instance."""
    return ProxyFix(wsgi_app, x_for=1, x_proto=1)
