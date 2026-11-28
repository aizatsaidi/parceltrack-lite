"""Production WSGI entry point for running behind the local Nginx proxy."""

from app import create_app
from app.seed import seed
from deploy.proxy import trust_local_nginx

application = create_app()

with application.app_context():
    seed()

# Nginx is the only proxy and Gunicorn only binds to loopback. Trust its
# client-IP and scheme headers so rate limits and HTTPS-aware Flask behavior
# use the original request values.
application.wsgi_app = trust_local_nginx(application.wsgi_app)
