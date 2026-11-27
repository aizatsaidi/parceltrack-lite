"""
Live reload for LOCAL DEVELOPMENT ONLY (shared).

Turned on only by `python run.py` on your own laptop. A cloud server started with
Gunicorn never runs that part of run.py, so this is never active online.

What it does:
  - pages (templates) and CSS are re-read on every request, never cached
  - the browser checks every second whether any file in app/ changed, and refreshes itself
  - Python changes restart the server (Flask's reloader); the page refreshes when it is back

Flask's debug mode stays OFF: no interactive debugger and no stack traces are ever shown (policy P4).
The check endpoint returns only a number (the latest file change time), never file names or content.
"""
import os

WATCH_EXTENSIONS = (".py", ".html", ".css", ".js")


def _latest_change(folder):
    latest = 0.0
    for root, _dirs, files in os.walk(folder):
        if "__pycache__" in root:
            continue
        for name in files:
            if name.endswith(WATCH_EXTENSIONS):
                try:
                    latest = max(latest, os.path.getmtime(os.path.join(root, name)))
                except OSError:
                    pass
    return latest


def enable_live_reload(app):
    app.config["LIVE_RELOAD"] = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0      # CSS and JS are never cached
    app.jinja_env.auto_reload = True
    watched = app.root_path                           # the app/ folder

    @app.route("/__dev/changed")
    def dev_changed():
        # Only reachable on 127.0.0.1 in local development
        return {"v": _latest_change(watched)}
