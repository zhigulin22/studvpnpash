import telebot, json, time
from telebot.async_telebot import AsyncTeleBot
import telebot
from telebot import types
import asyncssh
import aiofiles
import asyncio
import shutil
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uuid
import os
import json
import aiogram
import time
from ukassa import *
import datetime
from telebot.asyncio_helper import ApiTelegramException
import threading
import sqlite3
import paramiko
import logging
import asyncio, asyncssh
logging.getLogger('asyncssh').setLevel(logging.WARNING)
from telebot import types
from datetime import datetime, timedelta
from database_utils import create_database,add_raffle_tickets,get_all_pay,update_all_pay,get_raffle_tickets,update_purchase_amount,update_renewal_amount,update_flag,get_purchase_amount,get_renewal_amount,get_flag, get_username,update_username,get_telegram_id_by_username,update_referral_in,get_referral_in_count,get_agree_status,update_agree_status, update_referrer_id,add_user, get_referrer_id, format_subscription_end_time,add_device,get_user_referral_count,get_device_subscription_end_time, delete_user, delete_device, get_device_payment_status,get_device_uuid,update_device_status, update_referral_count,get_user_data,get_all_users,check_user_exists
from update_schema import update_database_schema
#logging.basicConfig(level=logging.DEBUG)
# Настройки вашего бота
TELEGRAM_TOKEN = '8098756212:AAHCMSbVibz1P-RLwQvSZniKZCIQo8DkD9E'
ADMIN_IDS = [5510185795,1120515812,851394287]
#8098756212:AAHCMSbVibz1P-RLwQvSZniKZCIQo8DkD9E
#7795571968:AAFDElnnIqSHpUHjFv19hoAWljr54Rok1jE
SERVER_IP = '213.165.37.141'
DATABASE_FILE = "vpn5_keys.db"
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'HX6qP0WlYzox'
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'
UUID_KEYWORD = "id: "

bot = AsyncTeleBot(TELEGRAM_TOKEN)

logging.basicConfig(
     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

last_message_ids = {}
user_payment_status = {}
admin_sms={}
top_10_cache = []

async def get_vless_link(user_id,device_type):
    user_uuid_from_device = await get_device_uuid(user_id,device_type)
    vless_link = f"vless://{user_uuid_from_device}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#HugVPN"
    # Обновление конфигурации на сервере
    return vless_link


async def send_message_with_deletion(chat_id, text,reply_markup=None):
    # Удаляем предыдущее сообщение, если оно существует
    if chat_id in last_message_ids:
        try:
            await bot.delete_message(chat_id, last_message_ids[chat_id])
        except Exception as e:
            print(f"Error deleting message: {e}")
    # Отправляем новое сообщение
    new_message = await bot.send_message(chat_id, text,reply_markup=reply_markup)
    # Сохраняем идентификатор нового сообщения
    last_message_ids[chat_id] = new_message.message_id





async def generate_vless_link_for_buy(user_id,message_chat_id,device_type):
    user_uuid = await get_device_uuid(user_id,device_type)
    vless_link = f"vless://{user_uuid}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#HugVPN"

    # Обновление конфигурации на сервере
    await update_config_on_server(user_uuid)
    return vless_link


async def restart_xray(ssh):
    try:
        result = await ssh.run('systemctl restart xray',check=True)
    except Exception as e:
        print(f"Ошибка при перезапуске Xray: {e}")






async def remove_uuid_from_config( uuid_to_remove):
    """Удаляет строку с указанным UUID из файла конфигурации."""
    try:
        # SSH подключение к серверу
        async with asyncssh.connect(SERVER_IP, username=SERVER_USERNAME, password=SERVER_PASSWORD) as ssh:

            async with ssh.start_sftp_client() as sftp:
                # Читаем конфиг
                async with sftp.open(CONFIG_FILE_PATH, 'r') as config_file:
                    config_content = await config_file.read()

                # Загружаем конфиг как JSON
                config = json.loads(config_content)

                # Переходим к списку клиентов
                clients = config["inbounds"][0]["settings"]["clients"]

                # Фильтруем список, удаляя клиентов с указанным UUID
                updated_clients = [
                    client for client in clients if client["id"] != uuid_to_remove
                ]

                # Передаем обновленный список в конфиг
                config["inbounds"][0]["settings"]["clients"] = updated_clients

                # Сериализуем обратно в JSON
                updated_config_content = json.dumps(config, indent=4)

                # Перезаписываем файл
                async with sftp.open(CONFIG_FILE_PATH, 'w') as config_file:
                    await config_file.write(updated_config_content)

            # Функция перезапуска сервиса (определите по необходимости)
            await restart_xray(ssh)

    except Exception as e:
        print(f"Error writing config file: {e}")
        return False

#Добавление нового Uuid в конфиг
async def update_config_on_server(new_uuid):
    try:
        # SSH подключение к серверу
        async with asyncssh.connect(SERVER_IP, username=SERVER_USERNAME, password=SERVER_PASSWORD) as ssh:

            # Открываем SFTP-сессию
            async with ssh.start_sftp_client() as sftp:
                # Читаем конфиг
                async with sftp.open(CONFIG_FILE_PATH, 'r') as config_file:
                    content = await config_file.read()
                    config = json.loads(content)

                # Обновляем UUID в конфиге
                if 'inbounds' in config:
                    for inbound in config['inbounds']:
                        if 'settings' in inbound and 'clients' in inbound['settings']:
                            new_client = {'id': new_uuid}
                            inbound['settings']['clients'].append(new_client)

                # Сохраняем обновленный конфиг
                async with sftp.open(CONFIG_FILE_PATH, 'w') as config_file:
                    await config_file.write(json.dumps(config, indent=4))

            # Перезапуск Xray после обновления конфига
            await restart_xray(ssh)

    except Exception as e:
        print(f"Ошибка при обновлении конфигурации: {e}")



async def dop_free_days_for_one(user_id, col_days):
    device_comb=["iPhone"]
    for device in device_comb:
        cur_time_end = await get_device_subscription_end_time(user_id, device)
        if cur_time_end != 0 and cur_time_end is not None:
            cur_time_end_new_format = datetime.fromisoformat(cur_time_end)
            cur_time_end_new_format = cur_time_end_new_format + timedelta(days=col_days)
            cur_status=await get_device_payment_status(user_id, device)
            device_uuid = await get_device_uuid(user_id, device)
            await update_device_status(device_uuid, True, cur_time_end_new_format)
            if not cur_status:
                await update_config_on_server(device_uuid)
        else:
            cur_time_end = datetime.now() + timedelta(days=col_days)
            device_uuid = await get_device_uuid(user_id, device)
            cur_status = await get_device_payment_status(user_id, device)
            await update_device_status(device_uuid, True, cur_time_end)
            if not cur_status:
                await update_config_on_server(device_uuid)



async def dop_free_days(user_id, col_days):
    referrer_id = await get_referrer_id(user_id)
    print(referrer_id)
    device_comb=["iPhone"]
    for device in device_comb:
        cur_time_end = await get_device_subscription_end_time(user_id, device)
        if cur_time_end != "None" and cur_time_end is not None:
            cur_time_end_new_format = datetime.fromisoformat(cur_time_end)
            cur_time_end_new_format = cur_time_end_new_format + timedelta(days=col_days)
            cur_status=await get_device_payment_status(user_id, device)
            device_uuid = await get_device_uuid(user_id, device)
            await update_device_status(device_uuid, True, cur_time_end_new_format)
            if not cur_status:
                await update_config_on_server(device_uuid)
        else:
            cur_time_end = datetime.now() + timedelta(days=col_days)
            device_uuid = await get_device_uuid(user_id, device)
            cur_status = await get_device_payment_status(user_id, device)
            await update_device_status(device_uuid, True, cur_time_end)
            if not cur_status:
                await update_config_on_server(device_uuid)
    cur_fl = await get_flag(user_id)
    if cur_fl == 0:
        if await check_user_exists(referrer_id):
            for device in device_comb:
                cur_time_end = await get_device_subscription_end_time(referrer_id, device)
                if cur_time_end is not None:
                    cur_time_end_new_format = datetime.fromisoformat(cur_time_end)
                    cur_time_end_new_format = cur_time_end_new_format + timedelta(days=col_days)
                    cur_status = await get_device_payment_status(user_id, device)
                    device_uuid = await get_device_uuid(referrer_id, device)
                    await update_device_status(device_uuid, True, cur_time_end_new_format)
                    if not cur_status:
                        await update_config_on_server(device_uuid)
                else:
                    cur_time_end = datetime.now() + timedelta(days=col_days)
                    device_uuid = await get_device_uuid(referrer_id, device)
                    cur_status = await get_device_payment_status(user_id, device)
                    await update_device_status(device_uuid, True, cur_time_end)
                    if not cur_status:
                        await update_config_on_server(device_uuid)





#Написать слова за регистраци
async def user_has_registered_in_bot(user_id):
    chat_id_from_recipient = user_id
    await bot.send_message(chat_id_from_recipient, "🎁Вам добавлено бесплатно 14 суток пользования нашим ВПН на все устройства, за регистрацию в боте🎁")



#Обрабатываем старт
@bot.message_handler(commands=['start'])
async def start(message):
    user_name = message.from_user.first_name
    welcome_message = (
        f"""{user_name}, 🚀 Добро пожаловать в HugVPN – ваш надёжный и быстрый VPN!

🔒 Полная анонимность и защита данных
⚡ Максимальная скорость без ограничений
🛡️ Никакой рекламы и утечек информации

💰 Оплата VPN проходит с помощью надежной платформы ЮKassa и ваша карта не будет привязана, то есть автопродления VPN нет.

🎁 Хочешь бесплатный VPN?
Присоединяйся к нашей реферальной программе и получай бесплатные недели использования!
        
🟢 Ваш профиль активен"""
    )
    user_id = message.from_user.id  # Получаем user_id
    user_name_id=message.from_user.username
    referrer = None
    if " " in message.text:
        referrer_candidate = message.text.split()[1]
        try:
            referrer_candidate = int(referrer_candidate)
            if user_id != referrer_candidate:
                referrer = referrer_candidate
        except ValueError:
            pass
    if not await check_user_exists(user_id):
        if str(referrer)[0] == '#': referrer = None
        await add_user(user_id, user_name_id, 0,0,True,referrer,0,0,0,0)
        print(1)
        await add_device(user_id, 1,"iPhone",False,None)
        #await add_device(user_id, 2, "Mac", False, None)
        #await add_device(user_id, 3, "Android", False, None)
        #await add_device(user_id, 4, "Windows", False, None)
        if referrer is not None:
            cur_col_in = await get_referral_in_count(referrer)
            await update_referral_in(referrer,cur_col_in+1)
            await dop_free_days_for_one(user_id, 21)
            await dop_free_days_for_one(referrer, 5)
        else:
            await dop_free_days(user_id, 14)
            await user_has_registered_in_bot(user_id)
    # Создаем inline-клавиатуру
    cur_user_name = await get_username(user_id)
    if cur_user_name != user_name_id:
        await update_username(user_id,user_name_id)

    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("💰 Купить VPN", callback_data='buy_vpn')
    button2 = types.InlineKeyboardButton("💼 Мой VPN", callback_data='my_vpn')
    button3 = types.InlineKeyboardButton("🎁 Пригласить", callback_data='referral')
    button4 = types.InlineKeyboardButton("☎️ Поддержка", url="https://t.me/HugVPN_support")
    button5 = types.InlineKeyboardButton("🌐 О сервисе", callback_data='service')
    button6 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
    # новая кнопка участия в розыгрыше
    button7 = types.InlineKeyboardButton("🎲 Поменять конфиг", callback_data='change_link')

    markup.add(button1, button2)
    markup.add(button3, button5)
    markup.add(button4, button6)
    markup.add(button7)  # кнопка размещается отдельно в нижнем ряду

    await bot.send_message(user_id, welcome_message, reply_markup=markup)


async def check_channel_subscription(user_id):
    channel_username = "@HugVPN"  # Замените на имя вашего канала
    try:
        member = await bot.get_chat_member(channel_username, user_id)
        # Если пользователь является создателем, администратором или участником – считаем, что он подписан
        if member.status in ["creator", "administrator", "member"]:
            return True
        else:
            return False
    except Exception as e:
        print(f"Ошибка проверки подписки пользователя {user_id}: {e}")
        return False


#Розыгрыш
@bot.callback_query_handler(func=lambda call: call.data == "join_raffle1")
async def join_raffle(call):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("🎲 Участвовать", callback_data='join_raffle')
    markup.add(button1)
    await bot.send_message(user_id, f"""🎁 Проводится розыгрыш с 10 победителями среди вас 
Призы:
🥇1 место - Telegram Premium на 1 год + годовая подписка на VPN от @HugVPN_bot
🥈2 место - Telegram Premium на 3 месяца + годовая подписка на VPN от @HugVPN_bot
3️⃣ 3 место - Telegram Premium на 1 месяц + годовая подписка на VPN от @HugVPN_bot
🎫 4 - 6 место - 6 месяцев подписка на VPN от @HugVPN_bot
🎫7 - 10 место - 3 месяца подписки на VPN от @HugVPN_bot

🔑 Чтобы участвовать в розыгрыше, нужно всего лишь подписаться на канал @HugVPN, за это дается один билет на участие
Победитель будет выбираться рандомно из базы людей, которые продлили или купили подписку в период с 30 марта - 30 апреля

📊 Ваше кол-во мест в таблице будет равняться суммарному количеству месяцев, на которое вы продлили или купили подписку + 1 билет за подписку
Вы можете купить два раза по 6 месяц и у вас будет 12 мест в таблице, что сильно повышает шансы выиграть""", reply_markup=markup)



    # Проверяем подписку на канал




#Розыгрыш
@bot.callback_query_handler(func=lambda call: call.data == "join_raffle")
async def join_raffle(call):
    user_id = call.from_user.id

    # Проверяем подписку на канал
    is_subscribed = await check_channel_subscription(user_id)
    if not is_subscribed:
        await send_message_with_deletion(
            call.message.chat.id,
            "❌ Чтобы участвовать в розыгрыше, подпишитесь на наш канал https://t.me/HugVPN!"
        )
        return

    # Проверяем наличие активной подписки (для примера используем устройство "iPhone")
    current_tickets = await get_raffle_tickets(user_id)
    if current_tickets == 0:
        await add_raffle_tickets(user_id, 1)
        current_tickets = 1
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("🎲 Купить", callback_data='buy_vpn')
    markup.add(button1)
    if current_tickets == 1:
        await send_message_with_deletion(
            call.message.chat.id,
            "❌ У вас сейчас 1 билет, за подписку на канал. Можно увеличить шансы, купив или продлив подписку",reply_markup=markup
        )
        return
    markup1 = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("🚀Главное меню", callback_data='main_menu')
    markup1.add(button2)
    await send_message_with_deletion(
        call.message.chat.id,
        f"✅ Вы участвуете в розыгрыше! Сейчас у вас {current_tickets} билет(ов). Итоги 30 апреля",reply_markup=markup1
    )




#Выдает информацию о нас
@bot.callback_query_handler(func=lambda call: call.data == "service")
async def buy_vpn(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("📒 Отзывы", url="https://t.me/HugVPN/54")
    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1)
    markup.add(button2)
    welcome_message = (
        """
 🌐✨Мы создали этого бота, чтобы вы могли:

- Легко и быстро подключаться к VPN и главное без рекламы.
- Защищать свои данные от посторонних глаз с помощью современных технологий шифрования.
- Экономить время — настройка занимает всего пару кликов, а после первого подключения нужно будет просто нажимать 1 кнопку!

Почему выбирают HugVPN?
💰 Один из самых дешевых тарифов (2.5 рубля/день)
🚀 Высокая скорость: никаких тормозов, только комфортный серфинг.
🔒 Безопасность: ваши данные всегда под защитой.
🌍 Глобальность: расширяем сеть серверов постоянно .
💬 Удобство: всё, что нужно, это нажать кнопку.

Наша миссия — сделать интернет безопасным и быстрым для каждого. Попробуйте HugVPN прямо сейчас и ощутите разницу! 😊
"""
    )
    await send_message_with_deletion(call.message.chat.id,welcome_message,reply_markup=markup)



#Кнопка инструкций надо настроить
@bot.callback_query_handler(func=lambda call: call.data == "instruction")
async def buy_vpn(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("📱 iPhone", url='https://t.me/HugVPN/41')
    button2 = types.InlineKeyboardButton("📲 Android", url='https://t.me/HugVPN/42')
    button3 = types.InlineKeyboardButton("💻 Mac", url='https://t.me/HugVPN/43')
    button4 = types.InlineKeyboardButton("🖥️ Windows", url='https://t.me/HugVPN/45')
    button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1,button2)
    markup.add(button3,button4)
    markup.add(button5)
    await send_message_with_deletion(call.message.chat.id,"Выберите устройство, для которого хотите получить инструкцию:",reply_markup=markup)




# Обработчик кнопки "Купить VPN"
# @bot.callback_query_handler(func=lambda call: call.data == "buy_vpn")
# async def buy_vpn(call):
#     markup = types.InlineKeyboardMarkup()
#     button1 = types.InlineKeyboardButton("📱 iPhone", callback_data='iPhone')
#     button2 = types.InlineKeyboardButton("📲 Android", callback_data='Android')
#     button3 = types.InlineKeyboardButton("💻 Mac", callback_data='Mac')
#     button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data='Windows')
#     button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
#     markup.add(button1, button2)
#     markup.add(button3, button4)
#     markup.add(button5)
#     await send_message_with_deletion(call.message.chat.id,"Выберите устройство, для которого хотите купить ВПН:", markup)



#Купить впн
@bot.callback_query_handler(func=lambda call: call.data == "buy_vpn")
async def buy_vpn(call):
    device = "iPhone"
    user_id = call.from_user.id
    print(user_id)
    user_status_device = await get_device_payment_status(user_id, device)
    if user_status_device is True:
        user_endtime_device = await get_device_subscription_end_time(user_id, device)
        user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("⏳ Продлить подписку", callback_data='proceed_subscription')
        button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        await send_message_with_deletion(call.message.chat.id, f"У вас уже есть подписка 🟢\nМожете посмотреть ключ во вкладе Мой VPN\n\nВремя окончания вашей подписки: {user_endtime_device_str}\n\nХотите ее продлить?",markup)
    else:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("- 1 месяц - 99₽", callback_data=f'1month1|{device}')
        button2 = types.InlineKeyboardButton("- 3 месяца - 255₽ (-15%)", callback_data=f'3month1|{device}')
        button3 = types.InlineKeyboardButton("- 6 месяцев - 480₽ (-20%)", callback_data=f'6month1|{device}')
        button4 = types.InlineKeyboardButton("- 12 месяцев - 999₽ (-25%)", callback_data=f'12month1|{device}')
        button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        markup.add(button3)
        markup.add(button4)
        markup.add(button5)

        await send_message_with_deletion(call.message.chat.id,f"📆Выберите срок подписки:", markup)



#Оплата покупки подписки
@bot.callback_query_handler(func=lambda call: call.data.startswith("1month1") or call.data.startswith("3month1") or call.data.startswith("6month1") or call.data.startswith("12month1"))
async def choose_subscription_duration_mounth(call):
    data = call.data.split("|")
    subscription_duration = data[0]
    device = data[1]
    cur_time = 0
    user_id = call.from_user.id  #
    user_name = call.from_user.username
    amount = 0
    sub = ""
    if subscription_duration == "1month1":
        cur_time = 31
        amount = 99
        sub = "1 месяц"
    elif subscription_duration == "3month1":
        cur_time = 91
        amount = 255
        sub = "3 месяца"
    elif subscription_duration == "6month1":
        cur_time = 181
        amount = 480
        sub = "6 месяцев"
    elif subscription_duration == "12month1":
        cur_time = 361
        amount = 899
        sub = "12 месяцев"
    user_status_device = await get_device_payment_status(user_id, device)
    markup1 = types.InlineKeyboardMarkup()
    button4 = types.InlineKeyboardButton("❌ Отменить платеж", callback_data='cancel_pay')
    markup1.add(button4)
    markup = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button2)
    user_payment_status[user_id] = {'status': 'pending', 'attempts': 0}
    if user_status_device is not True:
        user_id = call.from_user.id
        plan_text = call.data
        col = 0
        description = f"✅ Подписка на {sub}."
        # 📤 Создание платежа через ЮKassa
        payment_link, payment_id = await create_payment(amount, description)
        if payment_link:
            await send_message_with_deletion(call.message.chat.id, f"👇 Перейдите по ссылке для оплаты:\n{payment_link}",reply_markup=markup1)
            attempts = 0
            max_attempts = 120  # Проверяем в течение 10 минут
            while attempts < max_attempts:
                if user_payment_status[user_id]['status'] == 'canceled':
                    break
                status = await check_payment_status(payment_id)
                if status == 'succeeded':
                    cur_time_end = datetime.now() + timedelta(days=cur_time)
                    device_uuid = await get_device_uuid(user_id, device)
                    await dop_free_days_for_one(user_id,1)
                    await update_device_status(device_uuid, True, cur_time_end)
                    vless_link = await get_vless_link(user_id, device)
                    await bot.send_message(call.message.chat.id,text=f"✅ Оплата прошла успешно\n\n🔑 Ваша VLESS ссылка: ```{vless_link}```",parse_mode='MarkdownV2')
                    await bot.send_message(5510185795,text=f"✅ Купил {user_name} на {amount}")
                    col = col + 1
                    if col%3 == 1:
                        await bot.send_message(1120515812, text=f"Мурад СОСИ ЧЛЕН \n ✅ Купил {user_name} на {amount}")
                    #Розыгрыш
                    await add_raffle_tickets(user_id, cur_time//30)
                    user_endtime_device = await get_device_subscription_end_time(user_id, device)
                    user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
                    cur_refer = await get_referrer_id(user_id)
                    if cur_refer is not None and cur_refer != 0:
                        cur_fl = await get_flag(user_id)
                        if cur_fl == 0:
                            await dop_free_days_for_one(cur_refer, 10)
                        cur_col_ref_buy = await get_user_referral_count(cur_refer)
                        cur_col_ref_buy = cur_col_ref_buy + 1
                        await update_referral_count(cur_refer, cur_col_ref_buy)
                    if cur_refer is not None and cur_refer != 0:
                        cur_fl = await get_flag(user_id)
                        if cur_fl == 0:
                            cur_sum = await get_purchase_amount(cur_refer)
                            cur_sum = cur_sum + amount
                            await update_purchase_amount(cur_refer,cur_sum)
                        else:
                            cur_sum = await get_renewal_amount(cur_refer)
                            cur_sum = cur_sum + amount
                            await update_renewal_amount(cur_refer, cur_sum)
                    await update_flag(user_id, 1)
                    markup1 = types.InlineKeyboardMarkup()
                    button1 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
                    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
                    markup1.add(button1)
                    markup1.add(button2)
                    await send_message_with_deletion(call.message.chat.id,
                                                     f"⏳ Время окончания вашей подписки: {user_endtime_device_str}",
                                                     reply_markup=markup1)
                    break
                elif status == 'canceled':
                    await send_message_with_deletion(call.message.chat.id, text="❌ Платёж был отменён.")
                    break
                else:
                    await asyncio.sleep(5)
                    attempts += 1

            if attempts == max_attempts:
                await send_message_with_deletion(call.message.chat.id,text="❌Истекло время ожидания оплаты. Попробуйте снова.",reply_markup=markup)
        else:
            await send_message_with_deletion(call.message.chat.id, text="❌Произошла ошибка при создании платежа. Попробуйте позже.",reply_markup=markup)



#Помеять ссылку
#bot.callback_query_handler(func=lambda call: call.data == "change_link")
# async def change_link_vpn(user_id,my_yser_id):
#     markup = types.InlineKeyboardMarkup()
#     button1 = types.InlineKeyboardButton("📱 iPhone", callback_data=f'iPhone_change|iPhone|{user_id}')
#     button2 = types.InlineKeyboardButton("📲 Android", callback_data=f'Android_change|Android|{user_id}')
#     button3 = types.InlineKeyboardButton("💻 Mac", callback_data='Mac_change|Mac|{user_id}')
#     button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data='Windows_change|Windows|{user_id}')
#     button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
#     markup.add(button1)
#     markup.add(button2)
#     markup.add(button3)
#     markup.add(button4)
#     markup.add(button5)
#     await send_message_with_deletion(my_yser_id, "👇 Выберите устройство, для которого хотите поменять свой ключ:", markup)




@bot.callback_query_handler(func=lambda call: call.data == "change_link")
async def change_link(call):
    print(1)
    target_user_id=call.from_user.id
    device = "iPhone"
    #user_id=call.from_user.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1)
    fl = 1
    cur_status_device=await get_device_payment_status(target_user_id,device)
    if cur_status_device is True:
        cur_device_uuid = await get_device_uuid(target_user_id, device)
        await remove_uuid_from_config(cur_device_uuid)
        cur_device_time = await get_device_subscription_end_time(target_user_id, device)
        await delete_device(cur_device_uuid)
        await add_device(target_user_id,fl,device,cur_status_device,cur_device_time)
        new_uuid = await get_device_uuid(target_user_id,device)
        await update_config_on_server(new_uuid)
        new_link = await get_vless_link(target_user_id,device)
        user_endtime_device = await get_device_subscription_end_time(target_user_id, device)
        user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
        await bot.send_message(target_user_id,f"```{new_link}```",parse_mode='MarkdownV2')
    else:
        print(1)
        await send_message_with_deletion(target_user_id,f"У вас нет активного ключа, купите его",reply_markup=markup)


#Обработчик команды "Назад"
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
async def back_to_main_menu(call):
    user_name = call.from_user.first_name
    welcome_message = (
        f"""{user_name}, 🚀 Добро пожаловать в HugVPN – ваш надёжный и быстрый VPN!

🔒 Полная анонимность и защита данных
⚡ Максимальная скорость без ограничений
🛡️ Никакой рекламы и утечек информации

💰 Оплата VPN проходит с помощью надежной платформы ЮKassa и ваша карта не будет привязана, то есть автопродления VPN нет.

🎁 Хочешь бесплатный VPN?
Присоединяйся к нашей реферальной программе и получай бесплатные недели использования!

        
🟢 Ваш профиль активен"""

    )
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("💰 Купить VPN", callback_data='buy_vpn')
    button2 = types.InlineKeyboardButton("💼 Мой VPN", callback_data='my_vpn')
    button3 = types.InlineKeyboardButton("🎁 Пригласить", callback_data='referral')
    button4 = types.InlineKeyboardButton("☎️ Поддержка", url="https://t.me/HugVPN_support")
    button5 = types.InlineKeyboardButton("🌐 О сервисе", callback_data='service')
    button6 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
    button7 = types.InlineKeyboardButton("🎲 Поменять конфиг", callback_data='change_link')
    markup.add(button1, button2)
    markup.add(button3, button5)
    markup.add(button4, button6)
    markup.add(button7)
    await send_message_with_deletion(call.message.chat.id,welcome_message, markup)

#Узнать свой ВПН
# @bot.callback_query_handler(func=lambda call: call.data == "my_vpn")
# async def my_vpn(call):
#     user_id = call.from_user.id
#     markup = types.InlineKeyboardMarkup()
#     button1 = types.InlineKeyboardButton("📱 iPhone", callback_data=f'iPhone1|iPhone')
#     button2 = types.InlineKeyboardButton("📲 Android", callback_data=f'Android1|Android')
#     button3 = types.InlineKeyboardButton("💻 Mac", callback_data='Mac1|Mac')
#     button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data='Windows1|Windows')
#     button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
#     markup.add(button1)
#     markup.add(button2)
#     markup.add(button3)
#     markup.add(button4)
#     markup.add(button5)
#     await send_message_with_deletion(call.message.chat.id,"👇 Выберите устройство, для которого хотите узнать свой ключ:", markup)

#Выбор устройства для которого нужно узнать есть ключ или нет
@bot.callback_query_handler(func=lambda call: call.data == "my_vpn")
async def my_vpn(call):
    #data = call.data.split("|")
    #up = data[0]
    device = "iPhone"
    user_id=call.from_user.id
    user_payment_status_device = await get_device_payment_status(user_id, device)
    if user_payment_status_device is True:
        user_end_time=await get_device_subscription_end_time(user_id, device)
        user_endtime_device = await format_subscription_end_time(str(user_end_time))
        current_link = await get_vless_link(user_id, device)
        await bot.send_message(call.message.chat.id, text=f"👉 Ваша VLESS ссылка: ```{current_link}```", parse_mode='MarkdownV2')
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("⏳ Продлить подписку", callback_data='proceed_subscription')
        button3 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
        button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1,button3)
        markup.add(button2)
        await send_message_with_deletion(call.message.chat.id, f"""⏳ Время окончания вашей подписки: {user_endtime_device}\nВыберите действие: """, markup)
    else:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("💰 Купить VPN", callback_data='buy_vpn')
        button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        await send_message_with_deletion(call.message.chat.id, f"🚨 У вас нет ключа\nВыберите действие:", markup)




#Выбор утройства для продления
# @bot.callback_query_handler(func=lambda call: call.data == "proceed_subscription")
# async def phone_to_proceed(call):
#         markup = types.InlineKeyboardMarkup()
#         button1 = types.InlineKeyboardButton("📱 iPhone", callback_data=f'iPhone2|iPhone')
#         button2 = types.InlineKeyboardButton("📲 Android", callback_data=f'Android2|Android')
#         button3 = types.InlineKeyboardButton("💻 Mac", callback_data=f'Mac2|Mac')
#         button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data=f'Windows2|Windows')
#         button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
#         markup.add(button1)
#         markup.add(button2)
#         markup.add(button3)
#         markup.add(button4)
#         markup.add(button5)
#         await send_message_with_deletion(call.message.chat.id,"👇 Выберите устройство, для которого хотите продлить свой ключ:", markup)


@bot.callback_query_handler(func=lambda call: call.data == "proceed_subscription")
async def phone_to_proceed(call):
    #data = call.data.split("|")
    #up = data[0]
    device = "iPhone"
    user_id = call.from_user.id
    user_status_device = await get_device_payment_status(user_id, device)
    if user_status_device is True:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("- 1 месяц - 99₽", callback_data=f'1month2|{device}')
        button2 = types.InlineKeyboardButton("- 3 месяца - 255₽ (-15%)", callback_data=f'3month2|{device}')
        button3 = types.InlineKeyboardButton("- 6 месяцев - 480₽ (-20%)", callback_data=f'6month2|{device}')
        button4 = types.InlineKeyboardButton("- 12 месяцев - 899₽ (-25%)", callback_data=f'12month2|{device}')
        button5 = types.InlineKeyboardButton("🏠Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        markup.add(button3)
        markup.add(button4)
        markup.add(button5)

        await send_message_with_deletion(call.message.chat.id,f"📆Выберите срок, на который хотите продлить :", markup)
    else:
        await send_message_with_deletion(call.message.chat.id, f"🚨 У вас нет ключа")
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("💰 Купить VPN", callback_data='buy_vpn')
        button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        await send_message_with_deletion(call.message.chat.id, "👇 Выберите действие:", markup)

#Отмена платежа
@bot.callback_query_handler(func=lambda call: call.data == "cancel_pay")
async def cancel_pay(call):
    user_id=call.from_user.id
    user_name = call.from_user.first_name
    welcome_message = (
        f"{user_name}, твой платеж отменен ❌"
    )
    if user_id in user_payment_status and user_payment_status[user_id]['status'] == 'pending':
        user_payment_status[user_id]['status'] = 'canceled'
    else:
        await send_message_with_deletion(call.message.chat.id, "Нет активного платежа для отмены.")
        return
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("💰 Купить VPN", callback_data='buy_vpn')
    button2 = types.InlineKeyboardButton("💼 Мой VPN", callback_data='my_vpn')
    button3 = types.InlineKeyboardButton("🎁 Пригласить", callback_data='referral')
    button4 = types.InlineKeyboardButton("☎️ Поддержка", url="https://t.me/HugVPN_support")
    button5 = types.InlineKeyboardButton("🌐 О сервисе", callback_data='service')
    button6 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
    #button7 = types.InlineKeyboardButton("🌍 Купить карту", url='https://t.me/TopCardWorld_bot')
    markup.add(button1, button2)
    markup.add(button3, button5)
    markup.add(button4, button6)
    #markup.add(button5)
    await send_message_with_deletion(call.message.chat.id, welcome_message, markup)



#Продление подписки
@bot.callback_query_handler(func=lambda call: call.data.startswith("1month2") or call.data.startswith("3month2") or call.data.startswith("6month2") or call.data.startswith("12month2"))
async def pay_to_proceed(call):
    data = call.data.split("|")
    subscription_duration = data[0]
    device = data[1]
    cur_time = 0
    user_id = call.from_user.id  #
    amount = 0
    sub = ""
    if subscription_duration == "1month2":
        cur_time = 31
        amount = 99
        sub = "1 месяц"
    elif subscription_duration == "3month2":
        cur_time = 91
        amount = 255
        sub = "3 месяца"
    elif subscription_duration == "6month2":
        cur_time = 181
        amount = 480
        sub = "6 месяцев"
    elif subscription_duration == "12month2":
        cur_time = 361
        amount = 899
        sub = "12 месяцев"
    user_status_device = await get_device_payment_status(user_id, device)
    markup1 = types.InlineKeyboardMarkup()
    button4 = types.InlineKeyboardButton("❌ Отменить платеж", callback_data='cancel_pay')
    markup1.add(button4)
    markup = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button2)
    col = 0
    user_payment_status[user_id] = {'status': 'pending', 'attempts': 0}
    if user_status_device is True:
        user_id = call.from_user.id
        user_name = call.from_user.username
        description = f"✅ Подписка на {sub}."
        # 📤 Создание платежа через ЮKassa
        payment_link, payment_id = await create_payment(amount, description)
        if payment_link:
            await send_message_with_deletion(call.message.chat.id, f"👇 Перейдите по ссылке для оплаты:\n{payment_link}",reply_markup=markup1)
            attempts = 0
            max_attempts = 120  # Проверяем в течение 10 минут
            while attempts < max_attempts:
                if user_payment_status[user_id]['status'] == 'canceled':
                    break
                status = await check_payment_status(payment_id)
                if status == 'succeeded':
                    cur_time_end = await get_device_subscription_end_time(user_id, device)
                    cur_time_end = datetime.fromisoformat(cur_time_end)
                    cur_time_end = cur_time_end + timedelta(days=cur_time)
                    device_uuid = await get_device_uuid(user_id, device)
                    await update_device_status(device_uuid, True, cur_time_end)
                    vless_link = await get_vless_link(user_id, device)
                    await bot.send_message(call.message.chat.id, text=f"✅ Оплата прошла успешно\n\n🔑 Ваша VLESS ссылка: ```{vless_link}```", parse_mode='MarkdownV2')
                    await bot.send_message(5510185795, text=f"✅ Продлил {user_name} на {amount}")
                    col = col + 1
                    if col % 3 == 1:
                        await bot.send_message(1120515812, text=f"Мурад СОСИ ЧЛЕН \n ✅ Продлил {user_name} на {amount}")
                    # Розыгрыш
                    await add_raffle_tickets(user_id, cur_time // 30)
                    cur_refer = await get_referrer_id(user_id)
                    if cur_refer is not None and cur_refer != 0:
                        cur_fl = await get_flag(user_id)
                        if cur_fl == 0:
                            await dop_free_days_for_one(cur_refer, 10)
                        cur_col_ref_buy = await get_user_referral_count(cur_refer)
                        cur_col_ref_buy = cur_col_ref_buy + 1
                        await update_referral_count(cur_refer,cur_col_ref_buy)
                    if cur_refer is not None and cur_refer != 0:
                        cur_fl = await get_flag(user_id)
                        if cur_fl == 0:
                            cur_sum = await get_purchase_amount(cur_refer)
                            cur_sum = cur_sum + amount
                            await update_purchase_amount(cur_refer,cur_sum)
                        else:
                            cur_sum = await get_renewal_amount(cur_refer)
                            cur_sum = cur_sum + amount
                            await update_renewal_amount(cur_refer, cur_sum)
                    await update_flag(user_id, 1)
                    user_endtime_device = await get_device_subscription_end_time(user_id, device)
                    user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
                    markup1 = types.InlineKeyboardMarkup()
                    button1 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
                    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
                    markup1.add(button1)
                    markup1.add(button2)
                    await send_message_with_deletion(call.message.chat.id,f"⏳ Время окончания вашей подписки: {user_endtime_device_str}",reply_markup=markup1)
                    break
                elif status == 'canceled':
                    print(4)
                    await send_message_with_deletion(call.message.chat.id, text="❌ Платёж был отменён.")
                    break
                else:
                    await asyncio.sleep(5)
                    attempts += 1

            print(1)
            if attempts == max_attempts:
                await send_message_with_deletion(call.message.chat.id, text="❌Истекло время ожидания оплаты. Попробуйте снова.",reply_markup=markup)
        else:
            await send_message_with_deletion(call.message.chat.id, text="❌Произошла ошибка при создании платежа. Попробуйте позже.",reply_markup=markup)



#Реферальная ссылка
@bot.callback_query_handler(func=lambda call: call.data == "referral")
async def referral_program(call):
    user_name = call.from_user.id
    referral_link = f"https://t.me/HugVPN_bot?start={user_name}"
    markup = types.InlineKeyboardMarkup()
    button1=types.InlineKeyboardButton("👉 Узнать свою статистику", callback_data='col_ref')
    button2 = types.InlineKeyboardButton("🌟 Топ 10 амбасадоров", callback_data='top_ref')
    button3 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)
    await send_message_with_deletion(call.message.chat.id, f"🤙 Ваша реферальная ссылка: {referral_link}\n\n1️⃣ Если человек нажмет кнопку Start по вашей ссылке, вам и ему начислится по 5 дней бесплатно\n2️⃣ Если человек оформит любую подписку по вашей ссылке, вам начислится 10 дней дополнительно\n\nВсе дни складываются, поэтому можно раздать ссылки друзьям и получить год бесплатного пользования", markup)




async def update_top_10_cache():
    """Обновляет кэш топ-10 пользователей"""
    global top_10_cache
    top_10_cache = await get_top_10_referrers()

    # for i, user in enumerate(top_10_cache, 1):
    #     print(
    #         f"{i}. {user['username']}: всего {user['total']} (рефералов: {user['referrals']}, стартов: {user['starts']})")



async def get_current_top_10():
    """Возвращает текущий кэш топ-10"""
    return top_10_cache



#Топ 10 рефералов
@bot.callback_query_handler(func=lambda call: call.data == "top_ref")
async def print_top_ref(call):
    user_id=call.from_user.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1)
    top_10 = await get_current_top_10()
    if not top_10:
        await send_message_with_deletion(user_id, "Пока нет лидеров",reply_markup=markup)
        return

    response = "🏆 Топ-10 активных пользователей:\n\n"
    for i, user in enumerate(top_10, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
        response += f"{medal} {i}. @{user['username']}\n"
        response += f"   Всего: {user['total']} (💵 {user['referrals']} + 🤵 {user['starts']})\n"

    await send_message_with_deletion(user_id,response,reply_markup=markup)



#Моя статистика
@bot.callback_query_handler(func=lambda call: call.data == "col_ref")
async def referral_program(call):
    user_id = call.from_user.id
    user_col_ref = await get_user_referral_count(user_id)
    user_col_in=await get_referral_in_count(user_id)
    all_pay = await get_all_pay(user_id)
    sum_suf = await get_renewal_amount(user_id)
    print(user_col_in)
    markup = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu',reply_markup=markup)
    markup.add(button2)
    await send_message_with_deletion(call.message.chat.id, f"""
    🙋‍♂️ Кол-во человек, которое зашло по вашей ссылке: {user_col_in}
    
️🙋‍♀️ Кол-во раз, когда оплатили подписку по вашей реферальной ссылке: {user_col_ref}
Сумма продлений по вашей реферальной ссылке: {sum_suf}
Выплачено за продления: {all_pay}
Баланс выплат: {max(0,sum_suf - all_pay)}

Вывод возможен от 300 рублей.
Вам было начислено: {user_col_in*5+user_col_ref*10} дней, за вашу активность

Статистика в разделе топ-10 обновляется каждые 20 минут, если вас сразу туда не записало, это нормально, нужно немного подождать)
    """,markup)






@bot.message_handler(commands=['help'])
async def help_command(message):
    user_id=message.from_user.id
    await send_message_with_deletion(message.chat.id, f"""
        👉 Посмотреть, как подключить выданный ключ, можно в инструкциях на главной странице.

Таблица топов по рефералам обновляется каждые 20 минут. Если и после этого срока начисление не учтено, напишите нам.
👨‍🔧 Если вопрос по другой теме, задайте его, и вам ответит первый освободившийся администратор 🔧

@HugVPN_Support
    """)


@bot.message_handler(commands=['policy'])
async def privat_policy(message):
    user_id = message.from_user.id
    await send_message_with_deletion(message.chat.id, """
        👉Политика конфиденциальности бота
https://telegra.ph/Usloviya-ispolzovaniya-i-Politika-konfidencialnosti-VPN-bota-HugVPN-02-14
    """)




#Панель админа
@bot.message_handler(commands=['admin'])
async def admin_menu(message):
    # Проверить, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await bot.send_message(message.chat.id, "🙅‍♂️ У вас нет доступа к административной панели.")
        return

    # Админ-меню
    markup = types.InlineKeyboardMarkup()
    backup_button = types.InlineKeyboardButton("📥 Backup DB", callback_data="backup_db")
    btn1 = types.InlineKeyboardButton("📋 Получить данные о пользователе", callback_data="get_user_info")
    btn2 = types.InlineKeyboardButton("✏️ Изменить данные пользователя", callback_data="edit_user_data")
    btn3 = types.InlineKeyboardButton("➕ Изменить сумму вывода человека", callback_data="change_all_pay")
    btn10 = types.InlineKeyboardButton("➕ Узнать сумму, которую человек 100% получает", callback_data="get_payment_col")
    btn11 = types.InlineKeyboardButton("📋 Получить тг айди по username", callback_data="get_tg_id")
    btn7 = types.InlineKeyboardButton("🧤 Поменять ссылку пользователю", callback_data="ask_to_change")
    btn8 = types.InlineKeyboardButton("👙 Поменять рефералов_старт кол-во ", callback_data="change_col_ref_start")
    btn9 = types.InlineKeyboardButton("👙 Поменять рефералов_после кол-во",callback_data="change_col_ref_buy")
    btn5 = types.InlineKeyboardButton("📢 Массовая рассылка", callback_data="mass_message")
    btn4 = types.InlineKeyboardButton("📣 Узнать кол-во пользователей в базе данных", callback_data="col_user")
    markup.add(backup_button)
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn10)
    markup.add(btn11)
    markup.add(btn7)
    markup.add(btn8)
    markup.add(btn9)
    markup.add(btn5)
    markup.add(btn4)
    await send_message_with_deletion(message.chat.id, "🔧 Админ-панель", reply_markup=markup)





async def setup_menu():
    commands = [
        types.BotCommand("start", "✅ Главное меню"),
        types.BotCommand("help", "☎️ Помощь"),
        types.BotCommand("policy", "📄 Политика конфиденциальности")
    ]
    try:
        await bot.set_my_commands(commands)
        logging.info("Команды меню успешно установлены.")
    except Exception as e:
        logging.error(f"Ошибка при установке команд меню: {e}")



@bot.callback_query_handler(func=lambda call: call.data == "col_user")
async def get_user_info(call):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        success = 0

        cursor.execute("SELECT telegram_id FROM user_referrals")
        telegram_ids = [row[0] for row in cursor.fetchall()]  # Extract Telegram IDs
        col = len(telegram_ids)
        await send_message_with_deletion(call.message.chat.id, f"Сейчас в базе данных: {col} пользователей зарегистрировано")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return []  # Return an empty list in case of an error
    finally:
        if conn:
            conn.close()




@bot.callback_query_handler(func=lambda call: call.data == "change_col_ref_buy")
async def change_col_ref_start(call: types.CallbackQuery):
    """Запрос на добавление дней всем пользователям."""
    user_id = call.from_user.id
    admin_sms[user_id] = "change_col_ref_buy"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите имя пользователя человека без @:")


@bot.callback_query_handler(func=lambda call: call.data == "change_all_pay")
async def change_col_ref_start(call: types.CallbackQuery):
    """Запрос на добавление дней всем пользователям."""
    user_id = call.from_user.id
    admin_sms[user_id] = "change_all_pay"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите имя пользователя человека без @:")


@bot.callback_query_handler(func=lambda call: call.data == "get_payment_col")
async def change_col_ref_start(call: types.CallbackQuery):
    """Запрос на добавление дней всем пользователям."""
    user_id = call.from_user.id
    admin_sms[user_id] = "get_payment_col"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите имя пользователя человека без @:")


@bot.callback_query_handler(func=lambda call: call.data == "change_col_ref_start")
async def change_col_ref_start(call: types.CallbackQuery):
    """Запрос на добавление дней всем пользователям."""
    user_id = call.from_user.id
    admin_sms[user_id] = "change_col_ref_start"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите имя пользователя человека без @:")

@bot.callback_query_handler(func=lambda call: call.data == "ask_to_change")
async def ask_to_change(call: types.CallbackQuery):
    """Запрос на добавление дней всем пользователям."""
    user_id = call.from_user.id
    admin_sms[user_id] = "ask_to_change"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите имя пользователя человека без @:")

#Добавление дней всем пользователям ---
@bot.callback_query_handler(func=lambda call: call.data == "add_days_to_all")
async def start_add_days_to_all(call: types.CallbackQuery):
    """Запрос на добавление дней всем пользователям."""
    user_id = call.from_user.id
    admin_sms[user_id] = "add_days_to_all"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите количество дней, которые нужно добавить всем пользователям:")
#По юзер нейму изнать айди--
@bot.callback_query_handler(func=lambda call: call.data == "get_tg_id")
async def start_add_days_to_all(call: types.CallbackQuery):
    """Запрос на добавление дней всем пользователям."""
    user_id = call.from_user.id
    admin_sms[user_id] = "get_tgid"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите username без @:")
# --- Получение информации о пользователе ---
@bot.callback_query_handler(func=lambda call: call.data == "get_user_info")
async def get_user_info(call: types.CallbackQuery):
    """Запрос на получение информации о пользователе."""
    user_id = call.from_user.id
    admin_sms[user_id] = "get_inf"  # Устанавливаем текущий действие
    await send_message_with_deletion(call.message.chat.id, "Введите Telegram ID пользователя, чтобы получить данные:")

# --- Изменение данных пользователя ---
@bot.callback_query_handler(func=lambda call: call.data == "edit_user_data")
async def edit_user_data(call: types.CallbackQuery):
    """Запрос на изменение данных пользователя."""
    user_id = call.from_user.id
    admin_sms[user_id] = "edit_inf"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите Telegram ID пользователя, данные которого вы хотите изменить:")

# --- Массовая рассылка ---
@bot.callback_query_handler(func=lambda call: call.data == "mass_message")
async def mass_message(call: types.CallbackQuery):
    """Запрос на массовую рассылку."""
    user_id = call.from_user.id
    admin_sms[user_id] = "mass_mes"  # Устанавливаем текущую задачу
    await send_message_with_deletion(call.message.chat.id, "Введите сообщение для массовой рассылки:")

# --- Обработчик текстовых сообщений ---
@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS)
async def handle_admin_action(message: types.Message):
    """Обработка действий администратора."""
    user_id = message.from_user.id

    # Проверяем, есть ли действие, назначенное админу
    if user_id not in admin_sms:
        await send_message_with_deletion(message.chat.id, "❌ Вы не выбрали действие. Используйте /start для запуска.")
        return

    current_action = admin_sms[user_id]

    # Получение информации о пользователе
    if current_action == "add_days_to_all":
        try:
            days_to_add = int(message.text.strip())  # Преобразуем ввод в число
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()

            # Обновляем подписку всем пользователям
            try:
                cursor.execute("SELECT telegram_id FROM user_referrals")
                telegram_ids = [row[0] for row in cursor.fetchall()]
                total_users = len(telegram_ids)
                if total_users == 0:
                    await send_message_with_deletion(
                        message.chat.id, "❌ Пользователи не найдены в базе данных."
                    )
                    return

                # Обновляем каждому пользователю количество дней
                for user in telegram_ids:
                    print(user)
                    await dop_free_days(user, days_to_add)  # Заглушка для обновления дней подписки

                await bot.send_message(
                    message.chat.id,
                    f"✅ Успешно добавлено {days_to_add} дней всем {total_users} пользователям!"
                )

            except sqlite3.Error as e:
                await send_message_with_deletion(message.chat.id, f"❌ Ошибка базы данных: {e}")
            finally:
                conn.close()
        except ValueError:
            await send_message_with_deletion(message.chat.id, "❌ Введите корректное число.")
        finally:
            del admin_sms[user_id]  # Очищаем задачу
    elif current_action == "get_inf":
        target_user_id = message.text.strip()
        if not await check_user_exists(target_user_id):
            await send_message_with_deletion(
                message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден."
            )
        else:
            # Формирование информации о пользователе
            user_info = f"""
            👤 Полная информация о пользователе {target_user_id}:
            Кол-во рефералов: {await get_user_referral_count(target_user_id)}
            Пригласивший человек: {await get_referrer_id(target_user_id)}
            Подписки:
            - iPhone: {await get_device_subscription_end_time(target_user_id, "iPhone")}
            - Android: {await get_device_subscription_end_time(target_user_id, "Android")}
            - Mac: {await get_device_subscription_end_time(target_user_id, "Mac")}
            - Windows: {await get_device_subscription_end_time(target_user_id, "Windows")}
            """
            await bot.send_message(message.chat.id, user_info)

        # Очищаем задачу
        del admin_sms[user_id]
    elif current_action == "ask_to_change":
        target_user_name = message.text.strip()
        target_user_id=await get_telegram_id_by_username(target_user_name)
        if not await check_user_exists(target_user_id):
            await send_message_with_deletion(
                message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден."
            )
        else:
            await change_link(target_user_id)

        # Очищаем задачу
        del admin_sms[user_id]

    elif current_action == "get_payment_col":
        target_user_name = message.text.strip()
        target_user_id=await get_telegram_id_by_username(target_user_name)
        if not await check_user_exists(target_user_id):
            await send_message_with_deletion(
                message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден."
            )
        else:
            ans = await get_purchase_amount(target_user_id)
            await send_message_with_deletion(
                message.chat.id, f"Сумма {ans}"
            )


    elif current_action == "change_all_pay":
        target_user_name = message.text.strip()
        target_user_id=await get_telegram_id_by_username(target_user_name)
        if not await check_user_exists(target_user_id):
            await send_message_with_deletion(
                message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден."
            )
        else:
            admin_sms[user_id] = {"action": "change_all_pay", "target_user_id": target_user_id}
            ans = await get_all_pay(target_user_id)
            ans1 = await get_renewal_amount(target_user_id)
            await send_message_with_deletion(
                message.chat.id, f"Текущая сумма выплат: {ans}. На балансе пользователя: {ans1} Введите новую сумму выплат c учетом уже текущий(текущая + то, что выплатили сейчас):"
            )


    # Изменение данных пользователя
    elif current_action == "edit_inf":
        target_user_id = message.text.strip()
        if not await check_user_exists(target_user_id):
            await bot.send_message(
                message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден."
            )
        else:
            admin_sms[user_id] = {"action": "add_days", "target_user_id": target_user_id}
            await send_message_with_deletion(
                message.chat.id,
                f"Пользователь {target_user_id} найден. Введите количество дней для добавления:",
            )
    elif current_action == "change_col_ref_start":
        target_user_name = message.text.strip()
        target_user_id=await get_telegram_id_by_username(target_user_name)
        if not await check_user_exists(target_user_id):
            await bot.send_message(
                message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден."
            )
        else:
            admin_sms[user_id] = {"action": "change_col_ref_start", "target_user_id": target_user_id}
            await send_message_with_deletion(
                message.chat.id,
                f"Пользователь {target_user_id} найден. Введите реальное количество рефералоа:",
            )
    elif current_action == "change_col_ref_buy":
        target_user_name = message.text.strip()
        target_user_id=await get_telegram_id_by_username(target_user_name)
        if not await check_user_exists(target_user_id):
            await bot.send_message(
                message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден."
            )
        else:
            admin_sms[user_id] = {"action": "change_col_ref_buy", "target_user_id": target_user_id}
            await send_message_with_deletion(
                message.chat.id,
                f"Пользователь {target_user_id} найден. Введите реальное количество рефералоа:",
            )

    elif current_action == "get_tgid":
        username = message.text.strip().replace("@", "")
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()

            # Поиск пользователя по username
            cursor.execute("""
                        SELECT telegram_id, user_name 
                        FROM user_referrals 
                        WHERE LOWER(user_name) = LOWER(?)
                    """, (username,))

            result = cursor.fetchone()

            if result:
                telegram_id, stored_username = result
                # Получаем дополнительную информацию о пользователе
                referral_count = await get_user_referral_count(telegram_id)
                referal_in = await get_referral_in_count(telegram_id)

                response = f"""
        📱 <b>Информация о пользователе</b>:

        👤 Username: @{stored_username}
        🆔 Telegram ID: <code>{telegram_id}</code>
        👥 Рефералов привлечено: {referral_count}
        📥 Пришло по рефералке: {referal_in}

        <i>Чтобы скопировать ID, нажмите на него.</i>
        """
                await bot.send_message(
                    message.chat.id,
                    response,
                    parse_mode='HTML'
                )
            else:
                await send_message_with_deletion( message.chat.id,f"❌ Пользователь с username @{username} не найден в базе данных.")
        except sqlite3.Error as e:
            await send_message_with_deletion(message.chat.id, f"❌ Произошла ошибка при поиске пользователя: {e}")
        finally:
            if conn:
                conn.close()
            del admin_sms[user_id]

    # Добавление дней пользователю
    elif isinstance(current_action, dict) and current_action.get("action") == "add_days":
        try:
            days_to_add = int(message.text.strip())
            target_user_id = current_action["target_user_id"]
            await dop_free_days(target_user_id, days_to_add)
            await send_message_with_deletion(
                message.chat.id,
                f"✅ Пользователю {target_user_id} добавлено {days_to_add} дней подписки.",
            )
        except ValueError:
            await send_message_with_deletion(message.chat.id, "❌ Введите корректное число дней.")
        finally:
            del admin_sms[user_id]

    elif isinstance(current_action, dict) and current_action.get("action") == "change_col_ref_start":
        try:
            days_to_change = int(message.text.strip())
            target_user_id = current_action["target_user_id"]
            await update_referral_in(target_user_id,days_to_change)
            await send_message_with_deletion(
                message.chat.id,
                f"✅ Пользователю {target_user_id} изменено {days_to_change}.",
            )
        except ValueError:
            await send_message_with_deletion(message.chat.id, "❌ Введите корректное число дней.")
        finally:
            del admin_sms[user_id]
    elif isinstance(current_action, dict) and current_action.get("action") == "change_all_pay":
        try:
            sum = int(message.text.strip())
            target_user_id = current_action["target_user_id"]
            cur_bal = await get_renewal_amount(target_user_id)
            await update_all_pay(target_user_id,sum)
            await send_message_with_deletion(
                message.chat.id,
                f"✅ Пользователю {target_user_id} изменена общая сумма выплат на {sum}.",
            )
        except ValueError:
            await send_message_with_deletion(message.chat.id, "❌ Введите корректную сумму.")
        finally:
            del admin_sms[user_id]
    elif isinstance(current_action, dict) and current_action.get("action") == "change_col_ref_buy":
        try:
            days_to_change = int(message.text.strip())
            target_user_id = current_action["target_user_id"]
            await update_referral_count(target_user_id,days_to_change)
            await send_message_with_deletion(
                message.chat.id,
                f"✅ Пользователю {target_user_id} изменено.",
            )
        except ValueError:
            await send_message_with_deletion(message.chat.id, "❌ Введите корректное число дней.")
        finally:
            del admin_sms[user_id]

    # Массовая рассылка
    elif current_action == "mass_mes":
        mass_message_text = message.text
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT telegram_id FROM user_referrals")
            telegram_ids = [row[0] for row in cursor.fetchall()]  # ID пользователей
            success = 0

            for user in telegram_ids:
                try:
                    await bot.send_message(user, mass_message_text)
                    success += 1
                except Exception as e:
                    logging.error(f"Ошибка при отправке сообщения пользователю {user}: {e}")

            await bot.send_message(
                message.chat.id, f"✅ Сообщение отправлено {success} пользователям."
            )
        except sqlite3.Error as e:
            await send_message_with_deletion(message.chat.id, f"❌ Ошибка базы данных: {e}")
        finally:
            conn.close()
            del admin_sms[user_id]


@bot.callback_query_handler(func=lambda call: call.data == "backup_db")
async def backup_database(call: types.CallbackQuery):
    """Создание и отправка резервной копии базы данных."""
    user_id = call.from_user.id

    if user_id not in ADMIN_IDS:
        await bot.answer_callback_query(call.id, "⛔️ У вас нет прав администратора")
        return

    try:
        # Отправляем сообщение о начале создания бэкапа
        status_message = await bot.send_message(call.message.chat.id, "📦 Создаю резервную копию базы данных...")

        # Создаем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"

        # Проверяем существование базы данных
        if not os.path.exists(DATABASE_FILE):
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=status_message.message_id,
                text="❌ Ошибка: файл базы данных не найден"
            )
            return

        # Создаем копию
        shutil.copy2(DATABASE_FILE, backup_filename)

        # Получаем размер файла
        file_size = os.path.getsize(backup_filename) / (1024 * 1024)  # в МБ

        # Отправляем файл
        with open(backup_filename, 'rb') as file:
            await bot.send_document(
                chat_id=call.message.chat.id,
                document=file,
                caption=f"📤 Резервная копия базы данных\n"
                        f"📅 Дата создания: {timestamp}\n"
                        f"📦 Размер: {file_size:.2f} МБ"
            )

        # Удаляем временный файл
        os.remove(backup_filename)

        # Обновляем статусное сообщение
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=status_message.message_id,
            text="✅ Резервная копия успешно создана и отправлена"
        )

    except Exception as e:
        await bot.send_message(
            call.message.chat.id,
            f"❌ Произошла ошибка при создании резервной копии: {str(e)}"
        )





#Проверка базы данных на окончание срока подписки
async def check_subscriptions_and_remove_expired():
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
            if subscription_end_time:
                expiry_date = datetime.strptime(subscription_end_time, "%Y-%m-%d %H:%M:%S.%f")
                future_date = now
                days_left = (expiry_date - future_date).days
                print(days_left)
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



    except ApiTelegramException as e:
        if e.error_code == 403:
            print(f"Ошибка: пользователь заблокировал бота.")
        else:
            print(f"Ошибка API Telegram: {e}")




#получить топ 10 рефералов
async def get_top_10_referrers():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                user_name,
                referral_count,
                start_count,
                (referral_count + start_count) as total_count
            FROM user_referrals 
            WHERE user_name IS NOT NULL 
                AND user_name != "adubaiii"
                AND user_name != "GbPerviy"
                AND user_name != "yuldek"
                AND user_name != "ManagerMediaRust"
                AND (referral_count > 0 OR start_count > 0)
            ORDER BY total_count DESC 
            LIMIT 10
        """)

        results = cursor.fetchall()


        return [
            {
                "username": row[0],
                "referrals": row[1],
                "starts": row[2],
                "total": row[3]
            }
            for row in results
        ]

    except sqlite3.Error as e:
        print(f"Ошибка при получении топ-10: {e}")
        return []
    finally:
        if conn:
            conn.close()


async def start_scheduler():
    scheduler = AsyncIOScheduler()
    await update_top_10_cache()
    scheduler.add_job(update_top_10_cache, 'interval', minutes=20)
    scheduler.add_job(check_subscriptions_and_remove_expired, 'interval', hours=24)
    scheduler.start()
    print("Планировщик подписок запущен.")
    #fmf
async def main():
    await setup_menu()  # Настраиваем команды бота
    #await update_referral_in(1568939620,2)
    #await update_referral_in(851394287, 1)
    #await update_database_schema()
    #await update_device_status("4a96be34-251e-4712-a93b-d3c7dbecaeaa",False,None)
    #await create_database()  # Создаём базу данных
    await start_scheduler()  #
    await bot.polling(none_stop=True)


if __name__ == '__main__':
    asyncio.run(main())

