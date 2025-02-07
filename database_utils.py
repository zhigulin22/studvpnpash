import sqlite3
import datetime
import uuid
import os  # Import the 'os' module

DATABASE_FILE = "vpn_keys.db"
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


def format_subscription_end_time(subscription_end_time):
    if subscription_end_time:
        try:
            # Convert string to datetime object
            subscription_datetime = datetime.datetime.fromisoformat(subscription_end_time)

            # Format the datetime object to the desired string format
            formatted_time = subscription_datetime.strftime("%d %B %Y")
            return formatted_time
        except ValueError:
            print(f"Error: Could not parse date string '{subscription_end_time}'. Returning None.")
            return subscription_end_time


import os
import sqlite3

DATABASE_FILE = 'your_database_file.db'  # Укажите ваш файл базы данных

def create_database():
    """Creates the database and tables."""
    conn = None
    try:
        # Создаем соединение с базой данных
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Создаем таблицу user_referrals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_referrals (
                telegram_id INTEGER PRIMARY KEY,
                referral_count INTEGER DEFAULT 0,
                referrer_id INTEGER,
                FOREIGN KEY (referrer_id) REFERENCES user_referrals(telegram_id)  -- Ссылка на реферера
            )
        """)

        # Создаем таблицу user_devices
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

        # Сохраняем изменения
        conn.commit()
        print("Database and tables created successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred during database creation: {e}")
    finally:
        if conn:
            conn.close()

# Пример вызова функции


def add_user(telegram_id , referral_count,referrer_id):
    """Adds a new user or updates an existing user."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Вставляем или обновляем пользователя
        cursor.execute("""
            INSERT INTO user_referrals (telegram_id, referral_count, referrer_id)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                referral_count = excluded.referral_count,
                referrer_id = excluded.referrer_id
        """, (telegram_id, referral_count, referrer_id))

        conn.commit()
        return telegram_id
    except sqlite3.IntegrityError as e:
        print(f"Error adding user: {e}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()



def get_referrer_id(telegram_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Выполняем запрос для получения реферера
    cursor.execute("""
        SELECT referrer_id FROM user_referrals WHERE telegram_id = ?
    """, (telegram_id,))

    # Получаем результат
    result = cursor.fetchone()
    conn.close()

    # Если реферер найден, возвращаем его ID, иначе возвращаем None
    if result:
        return result[0]  # Возвращаем реферера
    return None  # Если реферер не найден



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

        cursor.execute("SELECT referral_count, referrer_id FROM user_referrals WHERE telegram_id = ?", (telegram_id,))
        referral_result = cursor.fetchone()
        referral_count = referral_result[0] if referral_result else 0
        referral_id = referral_result[1] if referral_result else 0

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
            'referral_id': referral_id,
            'devices': device_data
        }

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_device_uuid(telegram_id, device_type):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT device_uuid
            FROM user_devices
            WHERE telegram_id = ? AND device_type = ?
        """, (telegram_id, device_type))

        results = cursor.fetchall() # Get all matching devices

        if len(results) == 0:
            return None # No device found
        elif len(results) > 1:
            print(f"Warning: Multiple devices found for user {telegram_id} with type {device_type}. Returning None.")
            return None  # Multiple devices found, ambiguous
        else:
            return results[0][0]  # Return the device_uuid

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None  # Return None in case of an error
    finally:
        if conn:
            conn.close()


#Получить статус оплачено или нет у устройства
def get_device_payment_status(telegram_id, device_type):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT is_paid
            FROM user_devices
            WHERE telegram_id = ? AND device_type = ?
        """, (telegram_id, device_type))

        results = cursor.fetchall()

        if len(results) == 0:
            return (None, None)  # No device found
        elif len(results) > 1:
            print(f"Warning: Multiple devices found for user {telegram_id} with type {device_type}.  Returning (None, None).")
            return (None, None)  # Multiple devices found, ambiguous
        else:
            is_paid = bool(results[0][0])  # Convert to boolean
            return is_paid

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return (None, None)  # Return None in case of an error
    finally:
        if conn:
            conn.close()

#Получить время окончания подписки на определенном устройстве
def get_device_subscription_end_time(telegram_id, device_type):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT subscription_end_time
            FROM user_devices
            WHERE telegram_id = ? AND device_type = ?
        """, (telegram_id, device_type))

        results = cursor.fetchall()

        if len(results) == 0:
            return None  # No device found
        elif len(results) > 1:
            print(f"Warning: Multiple devices found for user {telegram_id} with type {device_type}. Returning None.")
            return None  # Multiple devices found, ambiguous
        else:
            return results[0][0] # Return the subscription_end_time

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None  # Return None in case of an error
    finally:
        if conn:
            conn.close()


#Узнать кол-во рефералов
def get_user_referral_count(telegram_id):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT referral_count
            FROM user_referrals
            WHERE telegram_id = ?
        """, (telegram_id,))

        result = cursor.fetchone()

        if result:
            return result[0]  # Return the referral count
        else:
            return None  # User not found

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None  # Return None in case of an error
    finally:
        if conn:
            conn.close()

#Изменить кол-во рефералов
def update_referral_count(telegram_id, new_count):
    """Updates a user's referral count."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_referrals SET referral_count = ? WHERE telegram_id = ?", (new_count, telegram_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def update_device_status(device_uuid, is_paid, subscription_end_time):
    subscription_end_time=subscription_end_time
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

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

#Проверка есть пользователь или нет
def check_user_exists(telegram_id):
    """Checks if a user with the given telegram_id exists in the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM user_referrals WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()

        return result is not None  # Returns True if a row was found, False otherwise

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False  # Assume user doesn't exist in case of an error
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
if __name__ == "__main__":

    #delete_user(1120515812)
    all_users = get_all_users()
    print("Все пользователи:")
    for user in all_users:
        print(user)

