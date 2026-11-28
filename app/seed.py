"""Fake demo users and parcels (policy P4: never real recipient data)."""
from . import db
from .models import User, Parcel, StatusHistory
from .auth.passwords import hash_password

DEMO_USERS = [
    # name, email, role, password
    ("Admin RapidExpress", "admin@rapidexpress.test", "admin", "AdminDemo#2026"),
    ("Kedai Demo Seller", "seller@shop.test", "seller", "SellerDemo#2026"),
    ("Rider Ali", "ali@rapidexpress.test", "rider", "RiderAliDemo#2026"),
    ("Rider Siti", "siti@rapidexpress.test", "rider", "RiderSitiDemo#2026"),
]

DEMO_PARCELS = [
    # tracking_no, recipient, phone, address, weight
    ("RX-DEMO7KQ2M9", "Test Recipient A", "012-0000001", "1 Jalan Contoh, 06010 Sintok, Kedah", 1.2),
    ("RX-DEMOP4T8WZ", "Test Recipient B", "012-0000002", "2 Jalan Contoh, 05000 Alor Setar, Kedah", 0.8),
    ("RX-DEMO9HN3QX", "Test Recipient C", "012-0000003", "3 Jalan Contoh, 10200 George Town, Pulau Pinang", 2.5),
    ("RX-DEMOB6R2VK", "Test Recipient D", "012-0000004", "4 Jalan Contoh, 02600 Arau, Perlis", 0.5),
    ("RX-DEMOT5W8LC", "Test Recipient E", "012-0000005", "5 Jalan Contoh, 08000 Sungai Petani, Kedah", 1.7),
    ("RX-DEMOH2Y6RF", "Test Recipient F", "012-0000006", "6 Jalan Contoh, 13700 Seberang Jaya, Pulau Pinang", 3.1),
]

# Extra demo parcels further along the route, so the dashboard and timeline have data to show:
# index -> (rider email, list of later statuses)
DEMO_PROGRESS = {
    2: ("ali@rapidexpress.test", ["Assigned"]),
    3: ("siti@rapidexpress.test", ["Assigned"]),
    4: ("ali@rapidexpress.test", ["Assigned", "Out for Delivery"]),
    5: ("siti@rapidexpress.test", ["Assigned", "Out for Delivery", "Delivered"]),
}


def seed():
    db.create_all()
    if User.query.first():
        return  # already set up
    users = {}
    for name, email, role, password in DEMO_USERS:
        u = User(name=name, email=email, role=role,
                 password_hash=hash_password(password))
        db.session.add(u)
        users[email] = u
    db.session.flush()

    seller = users["seller@shop.test"]
    admin = users["admin@rapidexpress.test"]
    for i, (tno, name, phone, addr, w) in enumerate(DEMO_PARCELS):
        p = Parcel(tracking_no=tno, seller_id=seller.id, recipient_name=name,
                   recipient_phone=phone, recipient_address=addr, weight_kg=w)
        db.session.add(p)
        db.session.flush()
        db.session.add(StatusHistory(parcel_id=p.id, new_status="Registered",
                                     changed_by=seller.id))
        # Parcels 3 and 4 go to Ali and Siti so the 403 demo works; 5 and 6 are further along
        if i in DEMO_PROGRESS:
            email, steps = DEMO_PROGRESS[i]
            rider = users[email]
            p.assigned_rider_id = rider.id
            old = "Registered"
            for step in steps:
                by = admin if step == "Assigned" else rider
                db.session.add(StatusHistory(parcel_id=p.id, old_status=old,
                                             new_status=step, changed_by=by.id))
                old = step
            p.status = old
            if old == "Delivered":
                p.delivered_at = p.created_at
    db.session.commit()
    print("Demo data created. See README.md for the demo logins.")
