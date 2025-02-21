import sqlite3
import asyncio, asyncssh
DATABASE_FILE = "vpn5_keys.db"

async def update_database_schema():
    """Updates the database schema to add new columns and modify existing ones."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Добавляем новую колонку для хранения количества людей, которые нажали старт по вашей ссылке
        cursor.execute("""
            ALTER TABLE user_referrals
            ADD COLUMN start_count INTEGER DEFAULT 0
        """)

        # Переименовываем колонку `message_id` в `user_name`
        cursor.execute("""
            ALTER TABLE user_referrals
            RENAME COLUMN message_id TO user_name
        """)

        conn.commit()
        print("Database schema updated successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred during database schema update: {e}")
    finally:
        if conn:
            conn.close()

# Пример вызова функции
asyncio.run(update_database_schema())
