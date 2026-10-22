"""
Start ParcelTrack Lite:   python run.py
Then open http://127.0.0.1:5000 in your browser.

The first time it runs, it creates the database and adds FAKE demo
users and parcels (policy P4: never use real recipient data for testing).
"""
from app import create_app
from app.seed import seed

app = create_app()

with app.app_context():
    seed()

if __name__ == "__main__":
    app.run(debug=False)  # debug stays off: no stack traces shown to users
