"""Task 15: trust only the forwarding values supplied by the local Nginx proxy."""

import os
import sys

from flask import Flask, jsonify, request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from deploy.proxy import trust_local_nginx


def make_client():
    app = Flask(__name__)

    @app.get("/proxy-info")
    def proxy_info():
        return jsonify(client_ip=request.remote_addr, secure=request.is_secure)

    app.wsgi_app = trust_local_nginx(app.wsgi_app)
    return app.test_client()


def test_trusted_nginx_headers_set_client_ip_and_https_scheme():
    client = make_client()

    response = client.get(
        "/proxy-info",
        headers={
            "X-Forwarded-For": "198.51.100.23",
            "X-Forwarded-Proto": "https",
        },
    )

    assert response.json == {"client_ip": "198.51.100.23", "secure": True}


def test_proxy_fix_uses_only_the_nearest_forwarded_client_value():
    client = make_client()

    response = client.get(
        "/proxy-info",
        headers={
            "X-Forwarded-For": "203.0.113.90, 198.51.100.23",
            "X-Forwarded-Proto": "http, https",
        },
    )

    assert response.json == {"client_ip": "198.51.100.23", "secure": True}
