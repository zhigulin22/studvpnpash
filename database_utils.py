import sqlite3
from datetime import datetime,timedelta

file_name = 'vpn_keys.db'

# Функция для преобразования datetime в ISO-8601 строку
def adapt_datetime(dt):
    return dt.isoformat()

# Функция для преобразования ISO-8601 строки в datetime
def convert_datetime(iso_str):
    return datetime.fromisoformat(iso_str)

def format_subscription_end_time(subscription_end_time):
    if subscription_end_time:
        return subscription_end_time.strftime("%d %B %Y") # Форматирование: день месяц год
    else:
        return None

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(file_name)
    conn.create_function("convert_datetime", 1, convert_datetime)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            uuid TEXT,
            referral_count INTEGER DEFAULT 0,
            is_paid BOOLEAN DEFAULT FALSE,
            subscription_end_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        )
    """)
    conn.commit()
    conn.close()
    sqlite3.register_adapter(datetime, adapt_datetime)

# Добавление нового пользователя
def add_user(telegram_id, uuid):
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (telegram_id, uuid) VALUES (?, ?)", (telegram_id, uuid))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
       conn.close()

# Получение пользователя по telegram_id
def get_user(telegram_id):
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {
            "telegram_id": user[0],
            "uuid": user[1],
            "referral_count": user[2],
            "is_paid": user[3],
            "subscription_end_time": convert_datetime(user[4]) if user[4] else None
        }
    return None

# Обновление uuid пользователя
def update_user_uuid(telegram_id, uuid):
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET uuid = ? WHERE telegram_id = ?", (uuid, telegram_id))
    conn.commit()
    conn.close()

# Обновление статуса оплаты пользователя
def update_user_payment_status(telegram_id, is_paid):
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_paid = ? WHERE telegram_id = ?", (is_paid, telegram_id))
    conn.commit()
    conn.close()

# Обновление количества приглашенных пользователей
def update_user_referral_count(telegram_id, referral_count):
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET referral_count = ? WHERE telegram_id = ?", (referral_count, telegram_id))
    conn.commit()
    conn.close()

def delete_user(telegram_id):
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        return True  # Успешное удаление
    except Exception as e:
        conn.rollback() # Отмена транзакции в случае ошибки
        return False  # Ошибка удаления
    finally:
        conn.close()

# Обновление времени окончания подписки
def update_user_subscription_end_time(telegram_id, subscription_end_time):
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET subscription_end_time = ? WHERE telegram_id = ?", (subscription_end_time, telegram_id))
    conn.commit()
    conn.close()

# Функция для получения всех пользователей
def get_all_users():
    conn = sqlite3.connect(file_name)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return [
      {
        "telegram_id": user[0],
        "uuid": user[1],
        "referral_count": user[2],
        "is_paid": user[3],
        "subscription_end_time": convert_datetime(user[4]) if user[4] else None
      }
      for user in users
    ]

if __name__ == "__main__":
    # Пример использования
    #init_db()

    # Добавляем нового пользователя
    #delete_user(5510185795)
    all_users = get_all_users()
    print("Все пользователи:")
    for user in all_users:
        print(user)