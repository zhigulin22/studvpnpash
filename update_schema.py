import sqlite3
import asyncio, asyncssh
DATABASE_FILE = "newvpn4_keys.db"

async def update_database_schema():
    """Updates the database schema to add new columns and modify existing ones."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Ваши существующие таблицы

    # Добавляем новую таблицу для розыгрыша:
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS raffle_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                ticket_count INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            );
        """)
    conn.commit()
    conn.close()

# Пример вызова функции
asyncio.run(update_database_schema())
