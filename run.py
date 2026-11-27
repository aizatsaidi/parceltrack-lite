"""
Start ParcelTrack Lite:   python run.py
Then open http://127.0.0.1:5000 in your browser.

The first time it runs, it creates the database and adds FAKE demo
users and parcels (policy P4: never use real recipient data for testing).

While it runs, saving any file in app/ refreshes the browser by itself (live reload,
see app/devreload.py). This only happens when you start it with `python run.py`
on your own computer, never on the cloud server.
"""
from app import create_app
from app.seed import seed

app = create_app()

with app.app_context():
    seed()

if __name__ == "__main__":
    from app.devreload import enable_live_reload
    enable_live_reload(app)
    # debug stays off: no debugger and no stack traces shown to users (P4).
    # use_reloader restarts the server by itself when Python files change.
    app.run(debug=False, use_reloader=True)
