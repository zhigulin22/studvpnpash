import telebot
import uuid
import json
import time
from ukassa import *
import datetime
import threading
import sqlite3
import paramiko
import logging
import asyncio
from telebot import types
from datetime import datetime, timedelta
from database_utils import create_database, add_user, get_referrer_id, format_subscription_end_time,add_device,get_user_referral_count,get_device_subscription_end_time, delete_user, delete_device, get_device_payment_status,get_device_uuid,update_device_status, update_referral_count,get_user_data,get_all_users,check_user_exists
# Настройки вашего бота
TELEGRAM_TOKEN = '7795571968:AAFWPrFsFxo3M0Pu7NDweHqB9-RiTogFr3Y'
SERVER_IP = '77.239.100.20'
DATABASE_FILE = "vpn_keys.db"
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'HX6qP0WlYzox'
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'
UUID_KEYWORD = "id: "

bot = telebot.TeleBot(TELEGRAM_TOKEN)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def get_vless_link(user_id,device_type):
    user_uuid_from_device=get_device_uuid(user_id,device_type)
    vless_link = f"vless://{user_uuid_from_device}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#StudVPN_{device_type}"

    # Обновление конфигурации на сервере

    return vless_link


def generate_vless_link_for_buy(user_id,message_chat_id,device_type):
    user_uuid = get_device_uuid(user_id,device_type)
    vless_link = f"vless://{user_uuid}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#StudVPN_{device_type}"

    # Обновление конфигурации на сервере
    update_server_config_for_buy(user_uuid,user_id,message_chat_id,device_type)

    return vless_link


def restart_xray(ssh):
    try:
        stdin, stdout, stderr = ssh.exec_command('systemctl restart xray')
        print(stdout.read().decode())
        print(stderr.read().decode())
    except Exception as e:
        print(f"Ошибка при перезапуске Xray: {e}")




def remove_uuid_from_config(config_file, uuid_to_remove, uuid_keyword=UUID_KEYWORD):
    """Удаляет строку с указанным UUID из файла конфигурации."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    lines=[]
    try:
        ssh.connect(SERVER_IP, username=SERVER_USERNAME, password=SERVER_PASSWORD)
        sftp = ssh.open_sftp()
        with sftp.open(CONFIG_FILE_PATH, 'r') as config_file:
            lines = config_file.readlines()
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
                print(line)
                updated_lines.append(line)
            if uuid_str in line:
                fl=1
                updated_lines.pop()

        for line in updated_lines:
            print(line)

        with sftp.open(CONFIG_FILE_PATH, 'w') as config_file:
            config_file.writelines(updated_lines)

        restart_xray(ssh)

        sftp.close()
        ssh.close()
    except Exception as e:
        print(f"Error writing config file: {e}")
        return False



#Для обновления при покупке
def update_server_config_for_buy(new_uuid,user_id,message_chat_id,device_type):
    # SSH подключение к серверу
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_IP, username=SERVER_USERNAME, password=SERVER_PASSWORD)
        sftp = ssh.open_sftp()

        with sftp.open(CONFIG_FILE_PATH, 'r') as config_file:
            config = json.load(config_file)

        # Обновление UUID в конфигурации
        if 'inbounds' in config:
            for inbound in config['inbounds']:
                if 'settings' in inbound and 'clients' in inbound['settings']:
                        new_client = {
                            'id': new_uuid
                        }
                        inbound['settings']['clients'].append(new_client)

        # Сохранение обновленной конфигурации
        with sftp.open(CONFIG_FILE_PATH, 'w') as config_file:
            json.dump(config, config_file, indent=4)

        # Перезапуск Xray после сохранения конфигурации
        restart_xray(ssh)

        sftp.close()
        ssh.close()
        # Добавление или обновление UUID в базе данных

    except Exception as e:
        print(f"Ошибка при обновлении конфигурации: {e}")



@bot.message_handler(commands=['start'])
def start(message):
    welcome_message = (
        "Рады приветствовать тебя в нашем ВПН \n\n"
        "🚀 Безопасный и быстрый VPN у вас под рукой! 🔒\n\n"
        "Забудьте о плохо загружающихся видео и плохом соединении.\n\n"
        "С нашим ботом у вас будет: \n"
        "*   Самая высокая скорость\n"
        "*   Конфиденциальность ваших данных\n"
        "*   Удобный и понятный интерфейс\n"
        "*   Защита в публичных Wi-Fi сетях"
    )
    user_id = message.from_user.id  # Получаем user_id
    referrer = None
    if " " in message.text:
        referrer_candidate = message.text.split()[1]
        try:
            referrer_candidate = int(referrer_candidate)
            if user_id != referrer_candidate:
                referrer = referrer_candidate
        except ValueError:
            pass

    if not check_user_exists(user_id):
        print(referrer)
        add_user(user_id, 0, referrer)
        add_device(user_id, 1,"iPhone",False,"None")
        add_device(user_id, 2, "Mac", False, "None")
        add_device(user_id, 3, "Android", False, "None")
        add_device(user_id, 4, "Windows", False, "None")
    # Создаем inline-клавиатуру

    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Купить VPN", callback_data='buy_vpn')
    button2 = types.InlineKeyboardButton("Мой VPN", callback_data='my_vpn')
    button3 = types.InlineKeyboardButton("Реферальная программа", callback_data='referral')
    button4 = types.InlineKeyboardButton("Поддержка", callback_data='support')
    markup.add(button1, button2)
    markup.add(button3, button4)

    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)


# Обработчик кнопки "Купить VPN"
@bot.callback_query_handler(func=lambda call: call.data == "buy_vpn")
def buy_vpn(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("iPhone", callback_data='iPhone')
    button2 = types.InlineKeyboardButton("Android", callback_data='Android')
    button3 = types.InlineKeyboardButton("Mac", callback_data='Mac')
    button4 = types.InlineKeyboardButton("Windows", callback_data='Windows')
    button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1, button2)
    markup.add(button3, button4)
    markup.add(button5)
    bot.edit_message_text("Выберите устройство, для которого хотите купить ВПН:", call.message.chat.id, call.message.message_id, reply_markup=markup)



@bot.callback_query_handler(func=lambda call: call.data in ["iPhone", "Android", "Mac", "Windows"])
def choose_mod(call):
    device = call.data
    user_id = call.from_user.id
    user_status_device = get_device_payment_status(user_id, device)
    if user_status_device == True:
        bot.send_message(call.message.chat.id, f"У вас уже есть подписка для {device}.")
        user_endtime_device = get_device_subscription_end_time(user_id, device)
        bot.send_message(call.message.chat.id, f"Время окончания вашей подписки для {device}: {user_endtime_device}")
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Продлить подписку", callback_data='proceed_subscription')
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        bot.send_message(call.message.chat.id, "Хотите ее продлить?", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("1 месяц - 99₽", callback_data=f'1month1|{device}')
        button2 = types.InlineKeyboardButton("3 месяца - 259₽", callback_data=f'3month1|{device}')
        button3 = types.InlineKeyboardButton("6 месяцев - 499₽", callback_data=f'6month1|{device}')
        button4 = types.InlineKeyboardButton("12 месяцев - 999₽", callback_data=f'12month1|{device}')
        button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1, button2)
        markup.add(button3, button4)
        markup.add(button5)

        bot.edit_message_text(f"Вы выбрали {device}. Выберите срок подписки:", call.message.chat.id, call.message.message_id, reply_markup=markup)





@bot.callback_query_handler(func=lambda call: call.data.startswith("1month1") or call.data.startswith("3month1") or call.data.startswith("6month1") or call.data.startswith("12month1"))
def choose_subscription_duration_mounth(call):
    data = call.data.split("|")
    subscription_duration = data[0]
    device = data[1]
    cur_time = 0
    user_id = call.from_user.id  #
    if subscription_duration == "1month":
        cur_time = 30
        amount = 99
        sub = "1 месяц"
    elif subscription_duration == "3month":
        cur_time = 90
        amount = 259
        sub = "3 месяца"
    elif subscription_duration == "6month":
        cur_time = 180
        amount = 499
        sub = "6 месяцев"
    elif subscription_duration == "12month":
        cur_time = 360
        amount = 999
        sub = "12 месяцев"
    user_status_device = get_device_payment_status(user_id, device)
    if (user_status_device == False):
        cur_time_end = datetime.now() + timedelta(days=cur_time)
        device_uuid = get_device_uuid(user_id, device)
        update_device_status(device_uuid, device, cur_time_end)
        markup = types.InlineKeyboardMarkup()
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button2)
        bot.send_message(call.message.chat.id, f"Ссылка для оплаты: ", reply_markup=markup)

        # #оплата
        #
        # user_id = call.from_user.id
        # plan_text = call.data
        # description = f"Подписка на {sub}."
        #
        # # 📤 Создание платежа через ЮKassa
        # payment_link, payment_id = create_payment(amount, description)
        #
        # if payment_link:
        #     bot.send_message(call.message.chat.id, text=f"Перейдите по ссылке для оплаты:\n{payment_link}")
        #
        #     attempts = 0
        #     max_attempts = 120  # Проверяем в течение 10 минут
        #     while attempts < max_attempts:
        #         status = check_payment_status(payment_id)
        #         if status == 'succeeded':
        #             vless_link = generate_vless_link_for_buy(user_id, call.message.chat.id, device)
        #             bot.send_message(call.message.chat.id, text=f"Ваша VLESS ссылка для {device}: {vless_link}")
        #             user_endtime_device = get_device_subscription_end_time(user_id, device)
        #             update_device_status(device_uuid, True, user_endtime_device)
        #             user_endtime_device = format_subscription_end_time(user_endtime_device)
        #             bot.send_message(call.message.chat.id,
        #                              f"Время окончания вашей подписки для {device}: {user_endtime_device}",
        #                              reply_markup=markup)
        #             break
        #         elif status == 'canceled':
        #             bot.send_message(call.message.chat.id, text="Платёж был отменён.")
        #             break
        #         else:
        #             time.sleep(5)
        #             attempts += 1
        #
        #     if attempts == max_attempts:
        #         bot.send_message(call.message.chat.id, text="Истекло время ожидания оплаты. Попробуйте снова.")
        # else:
        #     bot.send_message(call.message.chat.id, text="Произошла ошибка при создании платежа. Попробуйте позже.")

        vless_link = generate_vless_link_for_buy(user_id, call.message.chat.id, device)
        bot.send_message(call.message.chat.id, text=f"Ваша VLESS ссылка для {device}: {vless_link}")
        user_endtime_device = get_device_subscription_end_time(user_id, device)
        update_device_status(device_uuid, True, user_endtime_device)
        user_endtime_device = format_subscription_end_time(user_endtime_device)
        bot.send_message(call.message.chat.id,f"Время окончания вашей подписки для {device}: {user_endtime_device}", reply_markup=markup)
        #dop_free_days(call.message.chat.id,user_id)
        markup = types.InlineKeyboardMarkup()
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button2)
    else:
        bot.send_message(call.message.chat.id, f"У вас уже есть подписка для {device}." )
        user_endtime_device = format_subscription_end_time(get_device_subscription_end_time(user_id, device))
        bot.send_message(call.message.chat.id, f"Время окончания вашей подписки для {device}: {user_endtime_device}")
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Продлить подписку", callback_data='proceed_subscription')
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        bot.send_message(call.message.chat.id, "Хотите ее продлить?", reply_markup=markup)

#Обработчик команды "Назад"
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Купить VPN", callback_data='buy_vpn')
    button2 = types.InlineKeyboardButton("Мой VPN", callback_data='my_vpn')
    button3 = types.InlineKeyboardButton("Реферальная программа", callback_data='referral')
    button4 = types.InlineKeyboardButton("Поддержка", callback_data='support')
    markup.add(button1, button2)
    markup.add(button3, button4)
    sms="Вы вернулись в Главное меню: "
    bot.send_message(call.message.chat.id,sms, reply_markup=markup)

#Узнать свой ВПН
@bot.callback_query_handler(func=lambda call: call.data == "my_vpn")
def my_vpn(call):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("iPhone", callback_data=f'iPhone1|iPhone')
    button2 = types.InlineKeyboardButton("Android", callback_data=f'Android1|Android')
    button3 = types.InlineKeyboardButton("Mac", callback_data='Mac1|Mac')
    button4 = types.InlineKeyboardButton("Windows", callback_data='Windows1|Windows')
    button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1, button2)
    markup.add(button3, button4)
    markup.add(button5)
    bot.edit_message_text("Выберите устройство, для которого хотите узнать свой ключ:", call.message.chat.id,call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("iPhone1") or call.data.startswith("Mac1") or call.data.startswith("Android1") or call.data.startswith("Windows1"))
def learn_key(call):
    data = call.data.split("|")
    up = data[0]
    device = data[1]
    user_id=call.from_user.id
    user_payment_status_device=get_device_payment_status(user_id, device)
    if user_payment_status_device == True:
        user_endtime_device = format_subscription_end_time(get_device_subscription_end_time(user_id, device))
        current_link = get_vless_link(user_id, device)
        bot.send_message(call.message.chat.id, f"Ваша текущая ссылка для {device}: ")
        bot.send_message(call.message.chat.id, current_link)
        bot.send_message(call.message.chat.id, f"Время окончания вашей подписки для {device}: {user_endtime_device}")
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Продлить подписку", callback_data='proceed_subscription')
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, f"У вас нет ключа для {device}")
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Купить VPN", callback_data='buy_vpn')
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)




#Выбор утройства
@bot.callback_query_handler(func=lambda call: call.data == "proceed_subscription")
def phone_to_proceed(call):
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("iPhone", callback_data=f'iPhone2|iPhone')
        button2 = types.InlineKeyboardButton("Android", callback_data=f'Android2|Android')
        button3 = types.InlineKeyboardButton("Mac", callback_data=f'Mac2|Mac')
        button4 = types.InlineKeyboardButton("Windows", callback_data=f'Windows2|Windows')
        button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1, button2)
        markup.add(button3, button4)
        markup.add(button5)
        bot.edit_message_text("Выберите устройство, для которого хотите продлить свой ключ:", call.message.chat.id,call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("iPhone2") or call.data.startswith("Mac2") or call.data.startswith("Android2") or call.data.startswith("Windows2"))
def time_to_proceed(call):
    data = call.data.split("|")
    up = data[0]
    device = data[1]
    user_id = call.from_user.id
    user_status_device = get_device_payment_status(user_id, device)
    if user_status_device == True:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("1 месяц - 99₽", callback_data=f'1month2|{device}')
        button2 = types.InlineKeyboardButton("3 месяца - 259₽", callback_data=f'3month2|{device}')
        button3 = types.InlineKeyboardButton("6 месяцев - 499₽", callback_data=f'6month2|{device}')
        button4 = types.InlineKeyboardButton("12 месяцев - 999₽", callback_data=f'12month2|{device}')
        button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1, button2)
        markup.add(button3, button4)
        markup.add(button5)

        bot.edit_message_text(f"Вы выбрали {device}. Выберите срок, на который хотите продлить :", call.message.chat.id,call.message.message_id, reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, f"У вас нет ключа для {device}")
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Купить VPN", callback_data='buy_vpn')
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)

#Продление подписки
@bot.callback_query_handler(func=lambda call: call.data.startswith("1month2") or call.data.startswith("3month2") or call.data.startswith("6month2") or call.data.startswith("12month2"))
def pay_to_proceed(call):
    data = call.data.split("|")
    subscription_duration = data[0]
    device = data[1]
    cur_time = 0
    user_id = call.from_user.id  #
    if subscription_duration == "1month2":
        cur_time = 30
    elif subscription_duration == "3month2":
        cur_time = 90
    elif subscription_duration == "6month2":
        cur_time = 180
    elif subscription_duration == "12month2":
        cur_time = 360
    user_status_device = get_device_payment_status(user_id, device)
    if (user_status_device == True):
        bot.send_message(call.message.chat.id, f"Ссылка для оплаты: ")

        # оплата

        cur_time_end=get_device_subscription_end_time(user_id, device)
        cur_time_end = datetime.fromisoformat(cur_time_end)
        cur_time_end = cur_time_end + timedelta(days=cur_time)
        device_uuid = get_device_uuid(user_id, device)
        update_device_status(device_uuid, device, cur_time_end)
        vless_link = get_vless_link(user_id, device)
        bot.send_message(call.message.chat.id, f"Ваша VLESS ссылка для {device}:")
        bot.send_message(call.message.chat.id, vless_link)
        user_endtime_device = format_subscription_end_time(get_device_subscription_end_time(user_id, device))
        markup = types.InlineKeyboardMarkup()
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button2)
        bot.send_message(call.message.chat.id, f"Время окончания вашей подписки для {device}: {user_endtime_device}",reply_markup=markup)




#Реферальная ссылка
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def referral_program(call):
    user_name = call.from_user.id
    referral_link = f"https://t.me/@Stud_VPN_bot?start={user_name}"
    bot.send_message(call.message.chat.id, f"Ваша реферальная ссылка: {referral_link}")
    markup = types.InlineKeyboardMarkup()
    button1=types.InlineKeyboardButton("Узнать кол-во рефералов", callback_data='col_ref')
    button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1)
    markup.add(button2)
    bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "col_ref")
def referral_program(call):
    user_id = call.from_user.id
    user_col_ref=get_user_referral_count(user_id)
    bot.send_message(call.message.chat.id, f"Кол-во человек, которые купили подписку по вашей ссылке: {user_col_ref}")
    bot.send_message(call.message.chat.id,f"Вам было начислено за это: {user_col_ref*5} дней")
    markup = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu',reply_markup=markup)
    markup.add(button2)




#Поддержка
@bot.callback_query_handler(func=lambda call: call.data == "support")
def support(call):
    bot.send_message(call.message.chat.id, "Задайте вопрос, который вас интересует.")
    bot.send_message(call.message.chat.id, "Вам ответит первый освободившийся модератор")
    markup = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button2)
    bot.send_message(call.message.chat.id, "@StudVPN_Support", reply_markup=markup)


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id, """
        Задайте вопрос, который вас интересует. 
        
Вам ответит первый освободившийся модератор

@StudVPN_Support
    """)


def setup_menu():
    commands = [
        types.BotCommand("start", "Главное меню"),
        types.BotCommand("help", "Помощь")
    ]
    try:
       bot.set_my_commands(commands)
       logging.info("Команды меню успешно установлены.")
    except Exception as e:
        logging.error(f"Ошибка при установке команд меню: {e}")


setup_menu()
create_database()
bot.polling(none_stop=True, interval=0)
