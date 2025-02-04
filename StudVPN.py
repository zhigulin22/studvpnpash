import telebot
import uuid
import json
import paramiko
import logging
import asyncio
from telebot import types
from datetime import datetime, timedelta
from database_utils import create_database, add_user, format_subscription_end_time,add_device,get_user_referral_count,get_device_subscription_end_time, delete_user, delete_device, get_device_payment_status,get_device_uuid,update_device_status, update_referral_count,get_user_data,get_all_users,check_user_exists
# Настройки вашего бота
TELEGRAM_TOKEN = '7948987856:AAERs2G3QxGXKl2J8erLzrJpy5bDH39eHUg'
SERVER_IP = '77.239.100.20'
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'HX6qP0WlYzox'
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'

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

'''
#Для обновления конфигурации при продлении
def update_server_config_for_buy(new_uuid,user_id,message_chat_id,device_type):
    user_uuid = get_user(user_id)  # Получаем данные пользователя из базы данных
    cur_uuid = ""
    fl = 0

    if user and user["uuid"]:  # Проверяем, есть ли у пользователя UUID
        fl = 1
        cur_uuid = user["uuid"]  # Если есть, используем его


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
                    if fl == 1:
                        for client in range(len(inbound['settings']['clients'])):
                            if inbound['settings']['clients'][client]['id'] == cur_uuid:
                                inbound['settings']['clients'][client]['id'] = new_uuid
                                break
                    else:
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
        if fl == 0:  # Если пользователь новый
            if add_user(user_id, new_uuid):
                bot.send_message(message_chat_id, "Ключ успешно добавлен!")
            else:
                update_user_uuid(user_id, new_uuid)
                bot.send_message(message_chat_id, "Ключ успешно добавлен!")
        else:
            update_user_uuid(user_id, new_uuid)  # если пользователь существует, обновляем uuid
            bot.send_message(message_chat_id, "Ключ успешно обновлен!")

    except Exception as e:
        print(f"Ошибка при обновлении конфигурации: {e}")
'''


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
    if not check_user_exists(user_id):
        add_user(user_id, 0)
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
        button1 = types.InlineKeyboardButton("1 месяц - 99₽", callback_data=f'1month|{device}')
        button2 = types.InlineKeyboardButton("3 месяца - 259₽", callback_data=f'3month|{device}')
        button3 = types.InlineKeyboardButton("6 месяцев - 499₽", callback_data=f'6month|{device}')
        button4 = types.InlineKeyboardButton("12 месяцев - 999₽", callback_data=f'12month|{device}')
        button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1, button2)
        markup.add(button3, button4)
        markup.add(button5)

        bot.edit_message_text(f"Вы выбрали {device}. Выберите срок подписки:", call.message.chat.id, call.message.message_id, reply_markup=markup)



@bot.callback_query_handler(func=lambda call: call.data.startswith("1month") or call.data.startswith("3month") or call.data.startswith("6month") or call.data.startswith("12month"))
def choose_subscription_duration_mounth(call):
    data = call.data.split("|")
    subscription_duration = data[0]
    device = data[1]
    cur_time = 0
    user_id = call.from_user.id  #
    if subscription_duration == "1month": cur_time = 30
    elif subscription_duration == "3month": cur_time = 90
    elif subscription_duration == "6month": cur_time = 180
    elif subscription_duration == "12month": cur_time = 360
    user_status_device = get_device_payment_status(user_id, device)
    if (user_status_device == False):
        cur_time_end = datetime.now() + timedelta(days=cur_time)
        device_uuid = get_device_uuid(user_id, device)
        update_device_status(device_uuid, device, cur_time_end)
        markup = types.InlineKeyboardMarkup()
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button2)
        bot.send_message(call.message.chat.id, f"Ссылка для оплаты: ", reply_markup=markup)

        #оплата

        vless_link = generate_vless_link_for_buy(user_id,call.message.chat.id,device)
        bot.send_message(call.message.chat.id, f"Ваша VLESS ссылка для {device}:")
        bot.send_message(call.message.chat.id, vless_link)
        user_endtime_device = format_subscription_end_time(get_device_subscription_end_time(user_id, device))
        markup = types.InlineKeyboardMarkup()
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button2)
        bot.send_message(call.message.chat.id, f"Время окончания вашей подписки для {device}: {user_endtime_device}",reply_markup=markup)
        update_device_status(device_uuid, True, user_endtime_device)
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

#Выбор устройства для продления
@bot.callback_query_handler(func=lambda call: call.data == "my_vpn")
def my_vpn(call):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("iPhone", callback_data=f'iPhone|{user_id}')
    button2 = types.InlineKeyboardButton("Android", callback_data=f'Android|{user_id}')
    button3 = types.InlineKeyboardButton("Mac", callback_data=f'Mac|{user_id}')
    button4 = types.InlineKeyboardButton("Windows", callback_data=f'Windows|{user_id}')
    button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1, button2)
    markup.add(button3, button4)
    markup.add(button5)
    bot.edit_message_text("Выберите устройство, для которого хотите узнать свой ключ:", call.message.chat.id,call.message.message_id, reply_markup=markup)




#Выбор срока продления
@bot.callback_query_handler(func=lambda call: call.data == "proceed_subscription")
def my_vpn(call):
    device = call.data
    user_id = call.from_user.id
    user_status_device = get_device_payment_status(user_id, device)
    if user_status_device == True:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("iPhone", callback_data=f'iPhone|con')
        button2 = types.InlineKeyboardButton("Android", callback_data=f'Android|con')
        button3 = types.InlineKeyboardButton("Mac", callback_data=f'Mac|con')
        button4 = types.InlineKeyboardButton("Windows", callback_data=f'Windows|con')
        button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1, button2)
        markup.add(button3, button4)
        markup.add(button5)
        bot.edit_message_text("Выберите устройство, для которого хотите продлить свой ключ:", call.message.chat.id,call.message.message_id, reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()


@bot.callback_query_handler(func=lambda call: call.data.startswith("iPhone") or call.data.startswith("Mac") or call.data.startswith("Android") or call.data.startswith("Windows"))
def choose_subscription_duration_mounth(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("1 месяц - 99₽", callback_data=f'1month|{device}')
    button2 = types.InlineKeyboardButton("3 месяца - 259₽", callback_data=f'3month|{device}')
    button3 = types.InlineKeyboardButton("6 месяцев - 499₽", callback_data=f'6month|{device}')
    button4 = types.InlineKeyboardButton("12 месяцев - 999₽", callback_data=f'12month|{device}')
    button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1, button2)
    markup.add(button3, button4)
    markup.add(button5)

    bot.edit_message_text(f"Вы выбрали {device}. Выберите срок подписки:", call.message.chat.id,call.message.message_id, reply_markup=markup)


#Узнать ссылку для ВПН
@bot.callback_query_handler(func=lambda call: call.data.startswith("iPhone") or call.data.startswith("Mac") or call.data.startswith("Android") or call.data.startswith("Windows"))
def choose_subscription_duration_mounth(call):
    data = call.data.split("|")
    device = data[0]
    us = data[1]
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




#Реферальная ссылка
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def referral_program(call):
    user_name = call.from_user.username
    referral_link = f"https://t.me/studvpn666_bot?start={user_name}"
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

# Запуск бота
setup_menu()
create_database()
bot.polling(none_stop=True, interval=0)