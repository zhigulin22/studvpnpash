import sqlite3
import asyncio, asyncssh
DATABASE_FILE = "vpn5_keys.db"
async def delete():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # Проверка истёкших подписок
        cursor.execute("SELECT device_uuid, device_type, subscription_end_time, telegram_id FROM user_devices WHERE is_paid != 0")
        devices = cursor.fetchall()
        conn.close()
        now = datetime.now()
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("👉 Купить ВПН", callback_data='buy_vpn')
        markup.add(button1)

        for device_uuid, device_type, subscription_end_time, telegram_id in devices:
            if subscription_end_time and device_type == "iPhone":
                expiry_date = datetime.strptime(subscription_end_time, "%Y-%m-%d %H:%M:%S.%f")
                future_date = now
                days_left = (expiry_date - future_date).days

                if days_left <= 0:
                    await remove_uuid_from_config(device_uuid)
                    await update_device_status(device_uuid, False, None)
                    await bot.send_photo(chat_id=telegram_id,
                        photo="https://sun9-71.userapi.com/impg/8ABTe0umB9KNVsrHq39a6LTnnUWNbRSPWjYQPQ/eOPs9y2GmWs.jpg?size=604x581&quality=95&sign=d053ad5ba398d7c28905a17f9cfa67cf&type=album",  # Замените на URL вашей картинки
                        caption=f"""Ваша подписка истекла.\n Мы заметили, что ваша подписка истекла, а значит:
❌ Блокировки сайтов и соцсетей снова работают против вас
❌ Онлайн-кинотеатры, мессенджеры и сервисы могут быть недоступны
❌ Ваши данные без защиты в открытых сетях

⚡️ Восстановите подписку прямо сейчас и снова получите интернет без границ!""",reply_markup=markup)

                elif days_left == 1:
                    await bot.send_photo(chat_id=telegram_id,
                                     photo="https://i.ytimg.com/vi/hDbmmBaokeo/maxresdefault.jpg",
                                     # Замените на URL вашей картинки
                                     caption=f"""Ваша подписка закончится через 1 день.\n Мы заметили, что ваша подписка скоро истечет, а значит:
                    ❌ Блокировки сайтов и соцсетей снова работают против вас
                    ❌ Онлайн-кинотеатры, мессенджеры и сервисы могут быть недоступны
                    ❌ Ваши данные без защиты в открытых сетях

                    ⚡️ Восстановите подписку прямо сейчас и снова получите интернет без границ!""",reply_markup=markup)

                elif days_left == 3:
                    await bot.send_photo(chat_id=telegram_id,
                                         photo="https://i.ytimg.com/vi/hDbmmBaokeo/maxresdefault.jpg",
                                         # Замените на URL вашей картинки
                                         caption=f"""Ваша подписка закончится через 3 дня.\n Мы заметили, что ваша подписка скоро истечет, а значит:
                                       ❌ Блокировки сайтов и соцсетей снова работают против вас
                                       ❌ Онлайн-кинотеатры, мессенджеры и сервисы могут быть недоступны
                                       ❌ Ваши данные без защиты в открытых сетях

                                       ⚡️ Восстановите подписку прямо сейчас и снова получите интернет без границ!""",reply_markup=markup)
            elif subscription_end_time:
                expiry_date = datetime.strptime(subscription_end_time, "%Y-%m-%d %H:%M:%S.%f")
                future_date = now
                days_left = (expiry_date - future_date).days
                if days_left <= 0:
                    await remove_uuid_from_config(device_uuid)
                    await update_device_status(device_uuid, False, None)


    except sqlite3.Error as e:
        print(f"Ошибка при проверке подписок: {e}")

asyncio.run(delete())
