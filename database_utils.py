import sqlite3
from datetime import datetime
import uuid

DATABASE_NAME = "vpn_keys.db"


def create_connection():
    """Создает соединение с базой данных."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn


def create_table():
    """Создает таблицу, если она не существует."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vpn_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_username TEXT NOT NULL UNIQUE,
                    vpn_key_uuid TEXT NOT NULL UNIQUE,
                    referral_uuid TEXT,
                    is_subscribed INTEGER DEFAULT 0,
                    subscription_start_date DATETIME,
                    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    referral_link_received_date DATETIME
                );
            """)
            conn.commit()
            print("Table 'vpn_users' created successfully")
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")
        finally:
            conn.close()


def add_user(telegram_username, vpn_key_uuid, referral_uuid=None, referral_link_received_date=None):
    """Добавляет нового пользователя в базу данных."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vpn_users (telegram_username, vpn_key_uuid, referral_uuid, referral_link_received_date)
                VALUES (?, ?, ?, ?)
            """, (telegram_username, vpn_key_uuid, referral_uuid, referral_link_received_date))
            conn.commit()
            print(f"User {telegram_username} with key {vpn_key_uuid} added successfully.")
            return True
        except sqlite3.IntegrityError as e:
            print(f"Error adding user: Username or key already exists: {e}")
            return False
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            return False
        finally:
            conn.close()


def get_user_by_username(telegram_username):
    """Получает информацию о пользователе по имени."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vpn_users WHERE telegram_username = ?", (telegram_username,))
            user_data = cursor.fetchone()
            return user_data
        except sqlite3.Error as e:
            print(f"Error getting user by username: {e}")
            return None
        finally:
            conn.close()


def get_user_by_uuid(vpn_key_uuid):
    """Получает информацию о пользователе по UUID ключа."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vpn_users WHERE vpn_key_uuid = ?", (vpn_key_uuid,))
            user_data = cursor.fetchone()
            return user_data
        except sqlite3.Error as e:
            print(f"Error getting user by uuid: {e}")
            return None
        finally:
            conn.close()


def update_user_subscription(telegram_username, is_subscribed=1):
    """Обновляет статус подписки пользователя."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE vpn_users
                SET is_subscribed = ?, subscription_start_date = ?
                WHERE telegram_username = ?
            """, (is_subscribed, datetime.now(), telegram_username))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"Subscription status updated for {telegram_username}. Is subscribed: {is_subscribed}")
                return True
            else:
                print(f"User {telegram_username} not found.")
                return False
        except sqlite3.Error as e:
            print(f"Error updating subscription status: {e}")
            return False
        finally:
            conn.close()


def delete_user_by_username(telegram_username):
    """Удаляет пользователя из базы данных по имени."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vpn_users WHERE telegram_username = ?", (telegram_username,))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"User {telegram_username} deleted successfully.")
                return True
            else:
                print(f"User {telegram_username} not found")
                return False
        except sqlite3.Error as e:
            print(f"Error deleting user: {e}")
            return False
        finally:
            conn.close()


def delete_user_by_uuid(vpn_key_uuid):
    """Удаляет пользователя из базы данных по UUID ключа."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vpn_users WHERE vpn_key_uuid = ?", (vpn_key_uuid,))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"User with key {vpn_key_uuid} deleted successfully.")
                return True
            else:
                print(f"User with key {vpn_key_uuid} not found")
                return False
        except sqlite3.Error as e:
            print(f"Error deleting user: {e}")
            return False
        finally:
            conn.close()


def generate_referral_link(bot_username, referral_uuid):
    """Генерирует реферальную ссылку для пользователя."""
    return f"t.me/{bot_username}?start={referral_uuid}"


def get_user_by_referral_uuid(referral_uuid):
    """Получает информацию о пользователе по referral_uuid."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vpn_users WHERE referral_uuid = ?", (referral_uuid,))
            user_data = cursor.fetchone()
            return user_data
        except sqlite3.Error as e:
            print(f"Error getting user by referral_uuid: {e}")
            return None
        finally:
            conn.close()


if __name__ == '__main__':
    create_table()  # Создаем таблицу, если ее нет

    # Пример использования
    bot_username = "YourBotName"

    # 1. Создаем пользователя, который будет реферером
    referral_user_uuid = str(uuid.uuid4())
    add_user("referrer_user", referral_user_uuid)
    # 2. Генерируем ссылку для реферера
    referral_link = generate_referral_link(bot_username, referral_user_uuid)
    print(f"Generated referral link: {referral_link}")

    # 3. Добавляем нового пользователя, который перешел по ссылке
    new_user_username = "new_user"
    new_user_uuid = str(uuid.uuid4())
    referral_link_received_date = datetime.now()
    add_user(new_user_username, new_user_uuid, referral_user_uuid, referral_link_received_date)

    # 4. Получаем информацию о пользователе по его юзернейму
    user_info = get_user_by_username(new_user_username)
    print(f"User info after link: {user_info}")

    # 5. Получаем информацию о реферере
    referrer_info = get_user_by_referral_uuid(referral_user_uuid)
    print(f"Referral info: {referrer_info}")

    # 6. Обновляем статус подписки пользователя
    update_user_subscription(new_user_username, 1)

    # 7. Получаем информацию о пользователе после обновления подписки
    user_info_after_subscription = get_user_by_username(new_user_username)
    print(f"User info after subscription: {user_info_after_subscription}")

    delete_user_by_username("referrer_user")
    delete_user_by_username("new_user")
