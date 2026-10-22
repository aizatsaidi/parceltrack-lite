-- ParcelTrack Lite database schema (MySQL). Matches the ERD on slide 5.
-- Usage: mysql -u root -p parceltrack < schema.sql

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(10) NOT NULL, 
	is_active_account BOOL NOT NULL, 
	failed_logins INTEGER NOT NULL, 
	locked_until DATETIME, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE TABLE login_events (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER, 
	event VARCHAR(30) NOT NULL, 
	ip_address VARCHAR(45), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE parcels (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	tracking_no VARCHAR(20) NOT NULL, 
	seller_id INTEGER NOT NULL, 
	assigned_rider_id INTEGER, 
	recipient_name VARCHAR(100) NOT NULL, 
	recipient_phone VARCHAR(20) NOT NULL, 
	recipient_address VARCHAR(255) NOT NULL, 
	weight_kg FLOAT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	delivered_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (tracking_no), 
	FOREIGN KEY(seller_id) REFERENCES users (id), 
	FOREIGN KEY(assigned_rider_id) REFERENCES users (id)
);

CREATE TABLE delivery_photos (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	parcel_id INTEGER NOT NULL, 
	stored_filename VARCHAR(100) NOT NULL, 
	uploaded_by INTEGER NOT NULL, 
	uploaded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parcel_id) REFERENCES parcels (id), 
	FOREIGN KEY(uploaded_by) REFERENCES users (id)
);

CREATE TABLE status_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	parcel_id INTEGER NOT NULL, 
	old_status VARCHAR(20), 
	new_status VARCHAR(20) NOT NULL, 
	changed_by INTEGER NOT NULL, 
	changed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parcel_id) REFERENCES parcels (id), 
	FOREIGN KEY(changed_by) REFERENCES users (id)
);

