import sqlite3
import datetime
import uuid
import os  # Import the 'os' module

DATABASE_FILE = "user_data.db"
DEVICE_LIMIT = 4  # Maximum number of devices per user
ALLOWED_DEVICE_TYPES = ["iPhone", "Mac", "Android", "Windows"]


def convert_datetime(date_string):
    """Converts a date string to a datetime object or None."""
    if date_string:
        try:
            return datetime.datetime.fromisoformat(date_string)
        except ValueError:
            try:
                return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    return None


def create_database():
    """Creates the database and tables."""
    conn = None
    try:
        # Delete the database file if it exists
        if os.path.exists(DATABASE_FILE):
            os.remove(DATABASE_FILE)
            print(f"Existing database file '{DATABASE_FILE}' deleted.")

        conn = sqlite3.connect(DATABASE_FILE)
        conn.create_function("convert_datetime", 1, convert_datetime)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_referrals (
                telegram_id INTEGER PRIMARY KEY,
                referral_count INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                device_uuid TEXT UNIQUE,
                device_index INTEGER,  -- 1 to 4 to represent each device
                device_type TEXT,       -- Device type (iPhone, Mac, Android, Windows)
                is_paid BOOLEAN DEFAULT FALSE,
                subscription_end_time TEXT,
                FOREIGN KEY (telegram_id) REFERENCES user_referrals(telegram_id),
                UNIQUE (telegram_id, device_index)  -- Ensure only one device per index
            )
        """)
        conn.commit()
        print("Database and tables created successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred during database creation: {e}")
    finally:
        if conn:
            conn.close()


def add_user(telegram_id, referral_count=0):
    """Adds a new user."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO user_referrals (telegram_id, referral_count) VALUES (?, ?)",
                       (telegram_id, referral_count))
        conn.commit()
        print(f"User with telegram_id {telegram_id} added successfully.")
        return telegram_id
    except sqlite3.IntegrityError as e:
        print(f"Error adding user: {e}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def add_device(telegram_id, device_index, device_type, is_paid=False, subscription_end_time=None):
    """Adds a device for a user, limiting to 4 devices."""
    conn = None
    try:
        if device_index < 1 or device_index > DEVICE_LIMIT:
            print(f"Invalid device_index. Must be between 1 and {DEVICE_LIMIT}")
            return None

        if device_type not in ALLOWED_DEVICE_TYPES:
            print(f"Invalid device_type. Must be one of: {ALLOWED_DEVICE_TYPES}")
            return None

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        device_uuid = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO user_devices (device_uuid, telegram_id, device_index, device_type, is_paid, subscription_end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (device_uuid, telegram_id, device_index, device_type, is_paid, subscription_end_time))
        conn.commit()
        print(
            f"Device with UUID {device_uuid} added for user {telegram_id} at index {device_index} with type {device_type}")
        return device_uuid

    except sqlite3.IntegrityError as e:
        print(f"Error adding device: {e}")  # Could be device_index collision
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def get_user_data(telegram_id):
    """Retrieves user data, referral count, and device information."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT referral_count FROM user_referrals WHERE telegram_id = ?", (telegram_id,))
        referral_result = cursor.fetchone()
        referral_count = referral_result[0] if referral_result else 0

        cursor.execute("""
            SELECT device_uuid, device_index, device_type, is_paid, subscription_end_time
            FROM user_devices
            WHERE telegram_id = ?
            ORDER BY device_index
        """, (telegram_id,))
        devices = cursor.fetchall()  # Get all devices

        device_data = {}  # Dictionary for devices, keys will be "device1", "device2", etc.
        for i in range(1, DEVICE_LIMIT + 1):
            device_data[f"device{i}"] = None  # Initialize all possible devices to None

        for device in devices:
            device_index = device[1]
            device_data[f"device{device_index}"] = {  # Populate devices
                'device_uuid': device[0],
                'device_type': device[2],
                'is_paid': bool(device[3]),
                'subscription_end_time': device[4]
            }

        return {
            'telegram_id': telegram_id,
            'referral_count': referral_count,
            'devices': device_data
        }

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_referral_count(telegram_id, new_count):
    """Updates a user's referral count."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_referrals SET referral_count = ? WHERE telegram_id = ?", (new_count, telegram_id))
        conn.commit()
        print(f"Referral count for telegram_id {telegram_id} updated to {new_count}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def update_device_status(device_uuid, is_paid, subscription_end_time):
    """Updates a device's status."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_devices
            SET is_paid = ?, subscription_end_time = ?
            WHERE device_uuid = ?
        """, (is_paid, subscription_end_time, device_uuid))
        conn.commit()
        print(f"Device {device_uuid} updated.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def delete_device(device_uuid):
    """Deletes a device."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_devices WHERE device_uuid = ?", (device_uuid,))
        conn.commit()
        print(f"Device with UUID {device_uuid} deleted successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def delete_user(telegram_id):
    """Deletes a user and their devices."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Delete devices first
        cursor.execute("DELETE FROM user_devices WHERE telegram_id = ?", (telegram_id,))
        cursor.execute("DELETE FROM user_referrals WHERE telegram_id = ?", (telegram_id,))

        conn.commit()
        print(f"User with telegram_id {telegram_id} and their devices deleted successfully.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def get_all_users():
    """Retrieves data for all users in the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT telegram_id FROM user_referrals")
        telegram_ids = [row[0] for row in cursor.fetchall()]  # Extract Telegram IDs

        all_users_data = []
        for telegram_id in telegram_ids:
            user_data = get_user_data(telegram_id)  # Use the existing get_user_data function
            if user_data is not None:# Only add valid user data
                all_users_data.append(user_data)

        return all_users_data

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return []  # Return an empty list in case of an error
    finally:
        if conn:
            conn.close()


# Example usage:
# 1. This code will now explicitly delete the "user_data.db" file if it exists
# 2. Run this code to create a new database and tables

create_database()
telegram_id = add_user(12345, referral_count=5)

if telegram_id:  # Check if the user was added successfully
    # Register devices, with specific indices
    device_uuid1 = add_device(telegram_id, 1, "iPhone", is_paid=True, subscription_end_time="2024-06-15")
    device_uuid2 = add_device(telegram_id, 2, "Mac", is_paid=False)  # Add another device
    device_uuid3 = add_device(telegram_id, 3, "Android", is_paid=False)  # Add a third
    device_uuid4 = add_device(telegram_id, 4, "Windows", is_paid=True, subscription_end_time="2024-07-20")

    add_user(12346, referral_count=0)
    device_uuid1 = add_device(12346, 1, "iPhone", is_paid=True, subscription_end_time="2024-06-15")
    device_uuid2 = add_device(12346, 2, "Mac", is_paid=False)  # Add another device
    device_uuid3 = add_device(12346, 3, "Android", is_paid=False)  # Add a third
    device_uuid4 = add_device(12346, 4, "Windows", is_paid=True, subscription_end_time="2024-07-20")

    all_users = get_all_users()
    print("Все пользователи:")
    for user in all_users:
        print(user)

