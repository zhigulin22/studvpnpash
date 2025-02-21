import telebot, json, time
from telebot.async_telebot import AsyncTeleBot
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
import threading
import sqlite3
import paramiko
import logging
import asyncio, asyncssh
logging.getLogger('asyncssh').setLevel(logging.WARNING)
from telebot import types
from datetime import datetime, timedelta
from database_utils import create_database, get_username,update_username,get_telegram_id_by_username,update_referral_in,get_referral_in_count,get_agree_status,update_agree_status, update_referrer_id,add_user, get_referrer_id, format_subscription_end_time,add_device,get_user_referral_count,get_device_subscription_end_time, delete_user, delete_device, get_device_payment_status,get_device_uuid,update_device_status, update_referral_count,get_user_data,get_all_users,check_user_exists
from update_schema import update_database_schema
#logging.basicConfig(level=logging.DEBUG)
# Настройки вашего бота
TELEGRAM_TOKEN = '7795571968:AAFDElnnIqSHpUHjFv19hoAWljr54Rok1jE'
ADMIN_IDS = [5510185795,1120515812]
#8098756212:AAHCMSbVibz1P-RLwQvSZniKZCIQo8DkD9E
#7795571968:AAFDElnnIqSHpUHjFv19hoAWljr54Rok1jE
SERVER_IP = '77.239.100.20'
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
    vless_link = f"vless://{user_uuid_from_device}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#HugVPN_{device_type}"
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



async def send_message_with_deletion_parse(chat_id, text, parsemod):
    # Удаляем предыдущее сообщение, если оно существует
    if chat_id in last_message_ids:
        try:
            await bot.delete_message(chat_id, last_message_ids[chat_id])
        except Exception as e:
            print(f"Error deleting message: {e}")
    # Отправляем новое сообщение
    new_message = await bot.send_message(chat_id, text,parse_mode=parsemod)
    # Сохраняем идентификатор нового сообщения
    last_message_ids[chat_id] = new_message.message_id



async def generate_vless_link_for_buy(user_id,message_chat_id,device_type):
    user_uuid = await get_device_uuid(user_id,device_type)
    vless_link = f"vless://{user_uuid}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#HugVPN_{device_type}"

    # Обновление конфигурации на сервере
    await update_config_on_server(user_uuid)
    return vless_link


async def restart_xray(ssh):
    try:
        result = await ssh.run('systemctl restart xray',check=True)
    except Exception as e:
        print(f"Ошибка при перезапуске Xray: {e}")




async def remove_uuid_from_config(config_file, uuid_to_remove, uuid_keyword=UUID_KEYWORD):
    """Удаляет строку с указанным UUID из файла конфигурации."""
    try:
        # SSH подключение к серверу
        async with asyncssh.connect(SERVER_IP, username=SERVER_USERNAME, password=SERVER_PASSWORD) as ssh:

            async with ssh.start_sftp_client() as sftp:
                # Читаем конфиг
                async with sftp.open(CONFIG_FILE_PATH, 'r') as config_file:
                    content = await config_file.read()  # Читаем весь файл
                    lines = content.splitlines(keepends=True)
                if not lines:
                    return False  # Config file empty or not found

                updated_lines = []
                uuid_str = str(uuid_to_remove) # converting UUID to a string

                fl=0

                for line in lines:
                    if fl==1:
                        fl=0
                        continue
                    if  uuid_str not in line: # Check also for the UUID Keyword
                        updated_lines.append(line)
                    if uuid_str in line:
                        fl=1
                        updated_lines.pop()

                async with sftp.open(CONFIG_FILE_PATH, 'w') as config_file:
                    await config_file.write(''.join(updated_lines))

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


async def dop_free_days(user_id, col_days):
    referrer_id = await get_referrer_id(user_id)
    device_comb=["iPhone", "Android", "Mac", "Windows"]
    for device in device_comb:
        cur_time_end = await get_device_subscription_end_time(user_id, device)
        if cur_time_end != "None":
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
    if referrer_id is None:
        return
    if referrer_id == 0:
        return
    if col_days>20:
        col_days=7
    for device in device_comb:
        cur_time_end = await get_device_subscription_end_time(referrer_id, device)
        if cur_time_end != "None":
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



#Напичать в чат людям о том, что человек купил подписку по реферальной ссылке
async def user_has_payed_in_bot_be_link(user_id,user_name):
    referrer_id = await get_referrer_id(user_id)
    if referrer_id==0:
        return
    chat_id_from_sender = referrer_id
    await send_message_with_deletion(chat_id_from_sender, f"😎Пользователь {user_name} оформил подписку в боте по вашей реферальной ссылке.\n 🎁Вам было начислено за это 14 дней бесплатного пользования.🎁")
    chat_id_from_recipient = user_id
    await send_message_with_deletion(chat_id_from_recipient, "🎁Вам добавлено бесплатно 14 суток бесплатного пользования нашим ВПН на все устройства, за оплату подписки по реферальной ссылке🎁")
    cur_ref_col = await get_user_referral_count(referrer_id)
    cur_ref_col = cur_ref_col + 1
    await update_referral_count(referrer_id, cur_ref_col)
    await update_referrer_id(user_id,0)


#Напичать в чат людям о том, что человек зарегистрировался по реферальной ссылке
async def user_has_registered_in_bot_be_link(user_id,user_name):
    referrer_id = await get_referrer_id(user_id)
    chat_id_from_sender = referrer_id
    await send_message_with_deletion(chat_id_from_sender, f"😎Пользователь {user_name} зарегистрировался в боте и вам было начислено за это 7 дней бесплатного пользования.")
    chat_id_from_recipient = user_id
    await bot.send_message(chat_id_from_recipient, "🎁Вам добавлено бесплатно 38 суток пользования нашим ВПН на все устройства, за регистрацию в боте по реферальной ссылке🎁")


#Написать слова за регистраци
async def user_has_registered_in_bot(user_id):
    chat_id_from_recipient = user_id
    await bot.send_message(chat_id_from_recipient, "🎁Вам добавлено бесплатно 30 суток пользования нашим ВПН на все устройства, за регистрацию в боте🎁")



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
        await add_user(user_id, user_name_id, 0,0,True,referrer)
        await add_device(user_id, 1,"iPhone",False,"None")
        await add_device(user_id, 2, "Mac", False, "None")
        await add_device(user_id, 3, "Android", False, "None")
        await add_device(user_id, 4, "Windows", False, "None")
        if referrer is not None:
            cur_col_in = await get_referral_in_count(user_id)
            await update_referral_in(referrer,cur_col_in+1)
            await dop_free_days(user_id, 38)
            await user_has_registered_in_bot_be_link(user_id, user_name)
        else:
            await dop_free_days(user_id, 30)
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
    button7 = types.InlineKeyboardButton("🔄 Поменять ключ", callback_data='change_link')
    markup.add(button1, button2)
    markup.add(button3, button7)
    markup.add(button4, button6)
    markup.add(button5)

    await bot.send_message(user_id, welcome_message, reply_markup=markup)


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
    button1 = types.InlineKeyboardButton("📱 Iphone", url='https://t.me/HugVPN/41')
    button2 = types.InlineKeyboardButton("📲 Android", url='https://t.me/HugVPN/42')
    button3 = types.InlineKeyboardButton("💻 Mac", url='https://t.me/HugVPN/43')
    button4 = types.InlineKeyboardButton("🖥️ Windows", url='https://t.me/HugVPN/45')
    button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1,button2)
    markup.add(button3,button4)
    markup.add(button5)
    await send_message_with_deletion(call.message.chat.id,"Выберите устройство, для которого хотите получить инструкцию:",reply_markup=markup)




# Обработчик кнопки "Купить VPN"
@bot.callback_query_handler(func=lambda call: call.data == "buy_vpn")
async def buy_vpn(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("📱 iPhone", callback_data='iPhone')
    button2 = types.InlineKeyboardButton("📲 Android", callback_data='Android')
    button3 = types.InlineKeyboardButton("💻 Mac", callback_data='Mac')
    button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data='Windows')
    button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1, button2)
    markup.add(button3, button4)
    markup.add(button5)
    await send_message_with_deletion(call.message.chat.id,"Выберите устройство, для которого хотите купить ВПН:", markup)



#Купить впн
@bot.callback_query_handler(func=lambda call: call.data in ["iPhone", "Android", "Mac", "Windows"])
async def choose_mod(call):
    device = call.data
    user_id = call.from_user.id
    user_status_device = await get_device_payment_status(user_id, device)
    if user_status_device is True:
        user_endtime_device = await get_device_subscription_end_time(user_id, device)
        user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("⏳ Продлить подписку", callback_data='proceed_subscription')
        button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        await send_message_with_deletion(call.message.chat.id, f"У вас уже есть подписка для {device} 🟢.\nМожите посмотреть ключ во вкладе Мой ВПН\n\nВремя окончания вашей подписки для {device}: {user_endtime_device_str}\n\nХотите ее продлить?",markup)
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

        await send_message_with_deletion(call.message.chat.id,f"📆 Вы выбрали {device}. Выберите срок подписки:", markup)



#Оплата покупки подписки
@bot.callback_query_handler(func=lambda call: call.data.startswith("1month1") or call.data.startswith("3month1") or call.data.startswith("6month1") or call.data.startswith("12month1"))
async def choose_subscription_duration_mounth(call):
    data = call.data.split("|")
    subscription_duration = data[0]
    device = data[1]
    cur_time = 0
    user_id = call.from_user.id  #
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
    if user_status_device is True:
        user_id = call.from_user.id
        plan_text = call.data
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
                    await update_device_status(device_uuid, device, cur_time_end)
                    vless_link = await get_vless_link(user_id, device)
                    await bot.send_message(call.message.chat.id,text=f"✅ Оплата прошла успешно\n\n🔑 Ваша VLESS ссылка для {device}: ```{vless_link}```",parse_mode='MarkdownV2')
                    user_endtime_device = await get_device_subscription_end_time(user_id, device)
                    user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
                    await dop_free_days(user_id,14)
                    markup1 = types.InlineKeyboardMarkup()
                    button1 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
                    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
                    markup1.add(button1)
                    markup1.add(button2)
                    await send_message_with_deletion(call.message.chat.id,
                                                     f"⏳ Время окончания вашей подписки для {device}: {user_endtime_device_str}",
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
@bot.callback_query_handler(func=lambda call: call.data == "change_link")
async def change_link_vpn(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("📱 iPhone", callback_data=f'iPhone_change|iPhone')
    button2 = types.InlineKeyboardButton("📲 Android", callback_data=f'Android_change|Android')
    button3 = types.InlineKeyboardButton("💻 Mac", callback_data='Mac_change|Mac')
    button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data='Windows_change|Windows')
    button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)
    markup.add(button4)
    markup.add(button5)
    await send_message_with_deletion(call.message.chat.id, "👇 Выберите устройство, для которого хотите поменять свой ключ:", markup)




@bot.callback_query_handler(func=lambda call: call.data.startswith("iPhone_change") or call.data.startswith("Mac_change") or call.data.startswith("Android_change") or call.data.startswith("Windows_change"))
async def learn_key(call):
    data = call.data.split("|")
    up = data[0]
    device = data[1]
    user_id=call.from_user.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1)
    fl=0
    if device == "iPhone":
        fl=1
    elif device == "Android":
        fl=2
    elif device == "Mac":
        fl=3
    elif device == "Windows":
        fl=4
    cur_device_uuid=await get_device_uuid(user_id,device)
    cur_device_time=await get_device_subscription_end_time(user_id,device)
    cur_status_device=await get_device_payment_status(user_id,device)
    await delete_device(cur_device_uuid)
    await add_device(user_id,fl,device,cur_status_device,cur_device_time)
    new_link = await get_vless_link(user_id,device)
    user_endtime_device = await get_device_subscription_end_time(user_id, device)
    user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
    await bot.send_message(user_id,f"```{new_link}```",parse_mode='MarkdownV2')
    await send_message_with_deletion(user_id, f"Ваша новая VLESS ссылка для {device}.\nВремя окончания подписки: {user_endtime_device_str}", reply_markup=markup)



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
    button7 = types.InlineKeyboardButton("🔄 Поменять ключ", callback_data='change_link')
    markup.add(button1, button2)
    markup.add(button3, button7)
    markup.add(button4, button6)
    markup.add(button5)
    await send_message_with_deletion(call.message.chat.id,welcome_message, markup)

#Узнать свой ВПН
@bot.callback_query_handler(func=lambda call: call.data == "my_vpn")
async def my_vpn(call):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("📱 iPhone", callback_data=f'iPhone1|iPhone')
    button2 = types.InlineKeyboardButton("📲 Android", callback_data=f'Android1|Android')
    button3 = types.InlineKeyboardButton("💻 Mac", callback_data='Mac1|Mac')
    button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data='Windows1|Windows')
    button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)
    markup.add(button4)
    markup.add(button5)
    await send_message_with_deletion(call.message.chat.id,"👇 Выберите устройство, для которого хотите узнать свой ключ:", markup)

#Выбор устройства для которого нужно узнать есть ключ или нет
@bot.callback_query_handler(func=lambda call: call.data.startswith("iPhone1") or call.data.startswith("Mac1") or call.data.startswith("Android1") or call.data.startswith("Windows1"))
async def learn_key(call):
    data = call.data.split("|")
    up = data[0]
    device = data[1]
    user_id=call.from_user.id
    user_payment_status_device = await get_device_payment_status(user_id, device)
    if user_payment_status_device is True:
        user_end_time=await get_device_subscription_end_time(user_id, device)
        user_endtime_device = await format_subscription_end_time(str(user_end_time))
        current_link = await get_vless_link(user_id, device)
        await bot.send_message(call.message.chat.id, text=f"👉 Ваша VLESS ссылка для {device}: ```{current_link}```", parse_mode='MarkdownV2')
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("⏳ Продлить подписку", callback_data='proceed_subscription')
        button3 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
        button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1,button3)
        markup.add(button2)
        await send_message_with_deletion(call.message.chat.id, f"""⏳ Время окончания вашей подписки для {device}: {user_endtime_device}\nВыберите действие: """, markup)
    else:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("💰 Купить VPN", callback_data='buy_vpn')
        button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        await send_message_with_deletion(call.message.chat.id, f"🚨 У вас нет ключа для {device}\nВыберите действие:", markup)




#Выбор утройства для продления
@bot.callback_query_handler(func=lambda call: call.data == "proceed_subscription")
async def phone_to_proceed(call):
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("📱 iPhone", callback_data=f'iPhone2|iPhone')
        button2 = types.InlineKeyboardButton("📲 Android", callback_data=f'Android2|Android')
        button3 = types.InlineKeyboardButton("💻 Mac", callback_data=f'Mac2|Mac')
        button4 = types.InlineKeyboardButton("🖥️ Windows", callback_data=f'Windows2|Windows')
        button5 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        markup.add(button3)
        markup.add(button4)
        markup.add(button5)
        await send_message_with_deletion(call.message.chat.id,"👇 Выберите устройство, для которого хотите продлить свой ключ:", markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("iPhone2") or call.data.startswith("Mac2") or call.data.startswith("Android2") or call.data.startswith("Windows2"))
async def time_to_proceed(call):
    data = call.data.split("|")
    up = data[0]
    device = data[1]
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

        await send_message_with_deletion(call.message.chat.id,f"📆 Вы выбрали {device}. Выберите срок, на который хотите продлить :", markup)
    else:
        await send_message_with_deletion(call.message.chat.id, f"🚨 У вас нет ключа для {device}")
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
    markup.add(button1, button2)
    markup.add(button3, button5)
    markup.add(button4, button6)
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
    user_payment_status[user_id] = {'status': 'pending', 'attempts': 0}
    if user_status_device is True:
        user_id = call.from_user.id
        username=call.from_user.username
        plan_text = call.data
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
                    await bot.send_message(call.message.chat.id, text=f"✅ Оплата прошла успешно\n\n🔑 Ваша VLESS ссылка для {device}: ```{vless_link}```", parse_mode='MarkdownV2')
                    user_endtime_device = await get_device_subscription_end_time(user_id, device)
                    user_endtime_device_str = await format_subscription_end_time(str(user_endtime_device))
                    await user_has_payed_in_bot_be_link(user_id,username)
                    markup1 = types.InlineKeyboardMarkup()
                    button1 = types.InlineKeyboardButton("📎 Инструкции", callback_data='instruction')
                    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')
                    markup1.add(button1)
                    markup1.add(button2)
                    await send_message_with_deletion(call.message.chat.id,f"⏳ Время окончания вашей подписки для {device}: {user_endtime_device_str}",reply_markup=markup1)
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
    await send_message_with_deletion(call.message.chat.id, f"🤙 Ваша реферальная ссылка: {referral_link}\n\n1️⃣ Если человек нажмет кнопку Start по вашей ссылке, вам и ему начислится по 7 дней бесплатно\n2️⃣ Если человек оформит любую подписку по вашей ссылке, начислится 14 дней дополнительно\n\nВсе дни складываются, поэтому можно раздать ссылки друзьям и получить год бесплатного пользования", markup)




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
        await send_message_with_deletion(user_id, "Информация о топ-10 пока недоступна",reply_markup=markup)
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
    markup = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu',reply_markup=markup)
    markup.add(button2)
    await send_message_with_deletion(call.message.chat.id, f"""
    🙋‍♂️ Кол-во человек, которое зашло по вашей ссылке: {user_col_in}
    
️🙋‍♀️ Кол-во человек, которые купили подписку по вашей реферальной ссылке: {user_col_ref}. 
Всего было начислено: {user_col_in*7+user_col_ref*14} дней, за вашу активность
    """,markup)






@bot.message_handler(commands=['help'])
async def help_command(message):
    user_id=message.from_user.id
    await send_message_with_deletion(message.chat.id, f"""
        👉Посмотреть как подкючить выданый ключ можно в инструкциях на Главной странице.

👨‍🔧Если вопрос по другой теме, задай его и тебе ответит первый освободившийся администратор.‍🔧

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
    btn3 = types.InlineKeyboardButton("➕ Добавить дни всем пользователям", callback_data="add_days_to_all")
    btn11 = types.InlineKeyboardButton("📋 Получить тг айди по username", callback_data="get_tg_id")
    btn5 = types.InlineKeyboardButton("📢 Массовая рассылка", callback_data="mass_message")
    btn4 = types.InlineKeyboardButton("📣 Узнать кол-во пользователей в базе данных", callback_data="col_user")
    markup.add(backup_button)
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn11)
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
        cursor.execute("""
            SELECT device_uuid, subscription_end_time 
            FROM user_devices 
            WHERE is_paid = 1
            
        """)
        devices = cursor.fetchall()

        now = datetime.now()

        for device_uuid, subscription_end_time in devices:
            if subscription_end_time:
                expiry_date = datetime.strptime(subscription_end_time, "%Y-%m-%d %H:%M:%S.%f")
                if expiry_date < now:
                    print(f"Подписка истекла для UUID: {device_uuid}. Удаляем из конфигурации.")
                    await remove_uuid_from_config(CONFIG_FILE_PATH, device_uuid)

                    # Обновляем статус в базе
                    cursor.execute("""
                        UPDATE user_devices 
                        SET is_paid = 0, subscription_end_time = NULL
                        WHERE device_uuid = ?
                    """, (device_uuid,))

                cur=now-expiry_date


        conn.commit()
        conn.close()

    except sqlite3.Error as e:
        print(f"Ошибка при проверке подписок: {e}")




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
                AND user_name != ''
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
    scheduler.add_job(update_top_10_cache, 'interval', hours=5)
    scheduler.add_job(check_subscriptions_and_remove_expired, 'interval', days=1)
    scheduler.start()
    print("Планировщик подписок запущен.")


async def main():
    await setup_menu()  # Настраиваем команды бота
    #await update_database_schema()
    #await create_database()  # Создаём базу данных
    await start_scheduler()  #
    await bot.polling(none_stop=True)



if __name__ == '__main__':
    asyncio.run(main())
