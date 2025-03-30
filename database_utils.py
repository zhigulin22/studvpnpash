import sqlite3
import datetime
import uuid
import os  # Import the 'os' module
import asyncio

DATABASE_FILE = "vpn5_keys.db"
DEVICE_LIMIT = 4  # Maximum number of devices per user
ALLOWED_DEVICE_TYPES = ["iPhone", "Mac", "Android", "Windows"]


async def convert_datetime(date_string):
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


async def format_subscription_end_time(subscription_end_time):
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


async def add_raffle_tickets(user_id, ticket_count):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Проверяем, существует ли уже запись для пользователя
        cursor.execute("SELECT ticket_count FROM raffle_entries WHERE telegram_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            # Если запись существует, прибавляем к существующему количеству
            new_ticket_count = result[0] + ticket_count
            cursor.execute("UPDATE raffle_entries SET ticket_count = ? WHERE telegram_id = ?", (new_ticket_count, user_id))
        else:
            # Если записи нет, вставляем новую
            cursor.execute("""
                INSERT INTO raffle_entries (telegram_id, ticket_count)
                VALUES (?, ?)
            """, (user_id, ticket_count))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Ошибка начисления билетов: {e}")
        return False
    finally:
        if conn:
            conn.close()


async def get_raffle_tickets(user_id):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT ticket_count FROM raffle_entries WHERE telegram_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"Ошибка получения количества билетов: {e}")
        return 0
    finally:
        if conn:
            conn.close()

# Укажите ваш файл базы данных

async def create_database():
    """Creates the database and tables."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_referrals (
                telegram_id INTEGER PRIMARY KEY,
                user_name TEXT, -- Изменено с message_id на user_name
                referral_count INTEGER DEFAULT 0,
                start_count INTEGER DEFAULT 0, -- Новая колонка
                is_agree BOOLEAN DEFAULT FALSE,
                referrer_id INTEGER,
                flag INTEGER DEFAULT 0,
                purchase_amount INTEGER DEFAULT 0,
                renewal_amount INTEGER DEFAULT 0,
                all_pay INTEGER DEFAULT 0,
                FOREIGN KEY (referrer_id) REFERENCES user_referrals(telegram_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                device_uuid TEXT UNIQUE,
                device_index INTEGER,
                device_type TEXT,
                is_paid BOOLEAN DEFAULT FALSE,
                subscription_end_time TEXT,
                FOREIGN KEY (telegram_id) REFERENCES user_referrals(telegram_id),
                UNIQUE (telegram_id, device_index)
            )
        """)

        conn.commit()
        print("Database and tables created successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred during database creation: {e}")
    finally:
        if conn:
            conn.close()

# Пример вызова функции


async def add_user(telegram_id, user_name, referral_count, start_count, is_agree, referrer_id,flag,purchase_amount,renewal_amount,all_pay):
    """Adds a new user or updates an existing user."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_referrals (telegram_id, user_name, referral_count, start_count, is_agree, referrer_id,flag, purchase_amount, renewal_amount, all_pay)
            VALUES (?, ?, ?, ?, ?, ?,?,?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                user_name=excluded.user_name,
                referral_count = excluded.referral_count,
                start_count = excluded.start_count,
                is_agree = excluded.is_agree,
                referrer_id = excluded.referrer_id,
                flag = excluded.flag,
                purchase_amount = excluded.purchase_amount,
                renewal_amount = excluded.renewal_amount,
                all_pay = excluded.all_pay
        """, (telegram_id, user_name, referral_count, start_count, is_agree, referrer_id,flag,purchase_amount,renewal_amount,all_pay))

        conn.commit()
        return telegram_id
    except sqlite3.IntegrityError as e:
        print(f"Error adding user: {e}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


async def update_referrer_id(telegram_id, new_referrer_id):
    """Updates the referrer ID for a user."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # Выполняем обновление реферера
        cursor.execute("""
            UPDATE user_referrals
            SET referrer_id = ?
            WHERE telegram_id = ?
        """, (new_referrer_id, telegram_id))

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False  # Возвращаем False в случае ошибки
    finally:
        if conn:
            conn.close()


async def get_referrer_id(telegram_id):
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


#Получить сататус согласия с политикой
async def get_agree_status(telegram_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Выполняем запрос для получения реферера
    cursor.execute("""
        SELECT is_agree FROM user_referrals WHERE telegram_id = ?
    """, (telegram_id,))

    # Получаем результат
    result = cursor.fetchone()
    conn.close()

    # Если реферер найден, возвращаем его ID, иначе возвращаем None
    if result:
        return result[0]  # Возвращаем реферера
    return None  # Если реферер не найден


#Обновляем статус согласия
async def update_agree_status(telegram_id, is_agree):
    """Updates the referrer ID for a user."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # Выполняем обновление реферера
        cursor.execute("""
            UPDATE user_referrals
            SET is_agree = ?
            WHERE telegram_id = ?
        """, (is_agree, telegram_id))

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False  # Возвращаем False в случае ошибки
    finally:
        if conn:
            conn.close()



async def add_device(telegram_id, device_index, device_type, is_paid=False, subscription_end_time=None):
    """Adds a device for a user, limiting to 4 devices."""
    conn = None
    try:
        if device_index < 1 or device_index > DEVICE_LIMIT:
            print(f"Invalid device_index. Must be between 1 and {DEVICE_LIMIT}")
            return None

        if device_type not in ALLOWED_DEVICE_TYPES:
            print(device_type)
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


async def get_user_data(telegram_id):
    """Retrieves user data, referral count, and device information."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT user_name, referral_count,start_count, is_agree, referrer_id,flag,purchase_amount,renewal_amount, all_pay FROM user_referrals WHERE telegram_id = ?", (telegram_id,))
        referral_result = cursor.fetchone()
        user_name = referral_result[0] if referral_result else 0
        referral_count = referral_result[1] if referral_result else 0
        start_count = referral_result[2] if referral_result else 0
        is_agree = referral_result[3] if referral_result else 0
        referral_id = referral_result[4] if referral_result else 0
        flag = referral_result[5] if referral_result else 0
        purchase_amount = referral_result[6] if referral_result else 0
        renewal_amount = referral_result[7] if referral_result else 0
        all_pay = referral_result[8] if referral_result else 0


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
            break

        return {
            'telegram_id': telegram_id,
            'user_name': user_name,
            'referral_count': referral_count,
            'start_count': start_count,
            'referral_id': referral_id,
            'flag': flag,
            'purchase_amount': purchase_amount,
            'renewal_amount ':renewal_amount,
            'all_pay':all_pay,
            'is_agree': is_agree,
            'devices': device_data
        }

    except sqlite3.Error as e:
        #print(f"An error occurred: {e}")
        return None
    finally:
        if conn:
            conn.close()


#оюновить юзер нем
async def update_username(telegram_id, new_username):
    """Updates the user_name for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_referrals
            SET user_name = ?
            WHERE telegram_id = ?
        """, (new_username, telegram_id))

        if cursor.rowcount == 0:
            print(f"User with telegram_id {telegram_id} not found.")
            return False

        conn.commit()
        print(f"User_name for telegram_id {telegram_id} updated to {new_username}.")
        return True
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False
    finally:
        if conn:
            conn.close()


#Плолучить имя пользователя
async def get_username(telegram_id):
    """Retrieves the username for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_name
            FROM user_referrals
            WHERE telegram_id = ?
        """, (telegram_id,))

        result = cursor.fetchone()

        if result:
            return result[0] # Return the username
        else:
            return None # User not found

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None # Return None in case of an error
    finally:
        if conn:
            conn.close()


#Получить телеграм id по имени пользователя
async def get_telegram_id_by_username(username):
    """Retrieves the telegram_id for a given username."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT telegram_id
            FROM user_referrals
            WHERE user_name = ?
        """, (username,))

        result = cursor.fetchone()

        if result:
            return result[0] # Return the telegram_id
        else:
            return None # User not found

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None # Return None in case of an error
    finally:
        if conn:
            conn.close()

#Обновление кол-во нажавших старт
async def update_referral_in(telegram_id, referral_in):
    """Updates the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_referrals
            SET start_count =  ?
            WHERE telegram_id = ?
        """, (referral_in, telegram_id))

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


# Обновление суммы первых оплат
async def update_purchase_amount(telegram_id, purchase_amount):
    """Updates the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_referrals
            SET purchase_amount =  ?
            WHERE telegram_id = ?
        """, (purchase_amount, telegram_id))

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


# получить сумму первых оплат
async def get_purchase_amount(telegram_id):
    """Retrieves the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT purchase_amount
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


# Обновление статуса первой оплаты
async def update_all_pay(telegram_id, all_pay):
    """Updates the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_referrals
            SET all_pay =  ?
            WHERE telegram_id = ?
        """, (all_pay, telegram_id))

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


# получить flag
async def get_all_pay(telegram_id):
    """Retrieves the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT all_pay
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


# Обновление статуса первой оплаты
async def update_renewal_amount(telegram_id, renewal_amount):
    """Updates the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_referrals
            SET renewal_amount =  ?
            WHERE telegram_id = ?
        """, (renewal_amount, telegram_id))

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


# получить flag
async def get_renewal_amount(telegram_id):
    """Retrieves the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT renewal_amount
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


#Обновление статуса первой оплаты
async def update_flag(telegram_id, referral_in):
    """Updates the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_referrals
            SET flag =  ?
            WHERE telegram_id = ?
        """, (referral_in, telegram_id))

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


#получить flag
async def get_flag(telegram_id):
    """Retrieves the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT flag
            FROM user_referrals
            WHERE telegram_id = ?
        """, (telegram_id,))

        result = cursor.fetchone()

        if result:
            return result[0] # Return the referral count
        else:
            return None # User not found

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None # Return None in case of an error
    finally:
        if conn:
            conn.close()


#получить кол-во прошедших страт
async def get_referral_in_count(telegram_id):
    """Retrieves the referral_in count for a given telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT start_count
            FROM user_referrals
            WHERE telegram_id = ?
        """, (telegram_id,))

        result = cursor.fetchone()

        if result:
            return result[0] # Return the referral count
        else:
            return None # User not found

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None # Return None in case of an error
    finally:
        if conn:
            conn.close()




#Получить message_id
async def get_message_id_by_telegram_id(telegram_id):
    """Retrieves the chat_id (message_id) for a user based on their telegram_id."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Выполняем запрос для получения chat_id
        cursor.execute("""
            SELECT message_id
            FROM user_referrals
            WHERE telegram_id = ?
        """, (telegram_id,))

        result = cursor.fetchone()  # Получаем результат

        if result:
            return result[0]  # Возвращаем chat_id
        else:
            print(f"No user found with telegram_id: {telegram_id}")
            return None  # Если пользователь не найден

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None  # Возвращаем None в случае ошибки
    finally:
        if conn:
            conn.close()



async def get_device_uuid(telegram_id, device_type):
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
            return None  # Multiple devices found, ambiguous
        else:
            return results[0][0]  # Return the device_uuid

    except sqlite3.Error as e:
        #print(f"An error occurred: {e}")
        return None  # Return None in case of an error
    finally:
        if conn:
            conn.close()


#Получить статус оплачено или нет у устройства
async def get_device_payment_status(telegram_id, device_type):
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
async def get_device_subscription_end_time(telegram_id, device_type):
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
async def get_user_referral_count(telegram_id):
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
async def update_referral_count(telegram_id, new_count):
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


async def update_device_status(device_uuid, is_paid, subscription_end_time):
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


async def delete_device(device_uuid):
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


async def delete_user(telegram_id):
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
async def check_user_exists(telegram_id):
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


async def get_all_users():
    """Retrieves data for all users in the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT telegram_id FROM user_referrals")
        telegram_ids = [row[0] for row in cursor.fetchall()]  # Extract Telegram IDs

        all_users_data = []
        for telegram_id in telegram_ids:
            user_data = await get_user_data(telegram_id)  # Use the existing get_user_data function
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


async def main():
    #await delete_user(5510185795)
    #await update_flag(5510185795,1)
    #await create_database()
    all_users = await get_all_users()
    print("Все пользователи:")
    for user in all_users:
        print(user)


if __name__ == '__main__':
    asyncio.run(main())
