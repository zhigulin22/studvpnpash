import sqlite3
import asyncio, asyncssh
DATABASE_FILE = "vpn5_keys.db"

async def update_database_schema():
    """Updates the database schema to add new columns and modify existing ones."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        #Добавляем новую колонку для хранения количества людей, которые нажали старт по вашей ссылке
        cursor.execute("""
            ALTER TABLE user_referrals
            ADD COLUMN flag INTEGER DEFAULT 0
        """)

        cursor.execute("""
            ALTER TABLE user_referrals
            ADD COLUMN purchase_amount INTEGER DEFAULT 0
        """)

        cursor.execute("""
                ALTER TABLE user_referrals
                ADD COLUMN renewal_amount INTEGER DEFAULT 0
        """)

        cursor.execute("""
                        ALTER TABLE user_referrals
                        ADD COLUMN all_pay INTEGER DEFAULT 0
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
