import telebot
import uuid
import json
import paramiko
import logging
import asyncio
from telebot import types
from datetime import datetime, timedelta
from cop import create_database, add_user, add_device, delete_user, delete_device, update_device_status, \
    update_referral_count, get_user_data, get_all_users

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


def get_vless_link(user_id):
    user = get_user(user_id)
    vless_link = f"vless://{user['uuid']}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#StudVPN"

    # Обновление конфигурации на сервере

    return vless_link


def generate_vless_link(user_id, message_chat_id):
    user_uuid = str(uuid.uuid4())
    vless_link = f"vless://{user_uuid}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#StudVPN"

    # Обновление конфигурации на сервере
    update_server_config(user_uuid, user_id, message_chat_id)

    return vless_link


def restart_xray(ssh):
    try:
        stdin, stdout, stderr = ssh.exec_command('systemctl restart xray')
        print(stdout.read().decode())
        print(stderr.read().decode())
    except Exception as e:
        print(f"Ошибка при перезапуске Xray: {e}")


def update_server_config(new_uuid, user_id, message_chat_id):
    user = get_user(user_id)  # Получаем данные пользователя из базы данных
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
    button1 = types.InlineKeyboardButton("iPhone", callback_data='iphone')
    button2 = types.InlineKeyboardButton("Android", callback_data='android')
    button3 = types.InlineKeyboardButton("MacBook", callback_data='macbook')
    button4 = types.InlineKeyboardButton("Windows", callback_data='windows')
    button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1, button2)
    markup.add(button3, button4)
    markup.add(button5)
    bot.edit_message_text("Выберите устройство, для которого хотите купить ВПН:", call.message.chat.id,
                          call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["iphone", "android", "macbook", "windows"])
def choose_mod(call):
    device = call.data
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("1 месяц - 99₽", callback_data='1month')
    button2 = types.InlineKeyboardButton("3 месяца - 259₽", callback_data='3month')
    button3 = types.InlineKeyboardButton("6 месяцев - 499₽", callback_data='6month')
    button4 = types.InlineKeyboardButton("12 месяцев - 999₽", callback_data='12month')
    button5 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1, button2)
    markup.add(button3, button4)
    markup.add(button5)

    bot.edit_message_text(f"Вы выбрали {device}. Выберите срок подписки:", call.message.chat.id,
                          call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data[0] == "1month")
def choose_subscription_duration_mounth(call):
    # оплата
    user_id = call.from_user.id  #
    vless_link = generate_vless_link(user_id, call.message.chat.id)
    user = get_user(user_id)

    if (user["is_paid"] == 0):
        update_user_payment_status(user_id, 1)
        cur_time = user["subscription_end_time"]
        if cur_time:
            cur_time = cur_time + timedelta(days=30)
        else:
            cur_time = datetime.now() + timedelta(days=30)
        update_user_subscription_end_time(user_id, cur_time)
    else:
        cur_time = user["subscription_end_time"]
        update_user_subscription_end_time(user_id, cur_time + timedelta(days=30))
    bot.send_message(call.message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(call.message.chat.id, vless_link, parse_mode="Markdown")
    user = get_user(user_id)
    formatted_time = format_subscription_end_time(user["subscription_end_time"])
    bot.send_message(call.message.chat.id, f"Время окончания вашей подписки: {formatted_time}")


# На 3 месяца
@bot.callback_query_handler(func=lambda call: call.data == "3month")
def choose_subscription_duration_tree_mounth(call):
    user_id = call.from_user.id  #
    vless_link = generate_vless_link(user_id, call.message.chat.id)
    user = get_user(user_id)
    if (user["is_paid"] == 0):
        update_user_payment_status(user_id, 1)
        cur_time = user["subscription_end_time"]
        if cur_time:
            cur_time = cur_time + timedelta(days=90)
        else:
            cur_time = datetime.now() + timedelta(days=90)
        update_user_subscription_end_time(user_id, cur_time)
    else:
        cur_time = user["subscription_end_time"]
        update_user_subscription_end_time(user_id, cur_time + timedelta(days=90))
    bot.send_message(call.message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(call.message.chat.id, vless_link, parse_mode="Markdown")
    user = get_user(user_id)
    formatted_time = format_subscription_end_time(user["subscription_end_time"])
    bot.send_message(call.message.chat.id, f"Время окончания вашей подписки: {formatted_time}")


# На 180 дней
@bot.callback_query_handler(func=lambda call: call.data == "6month")
def choose_subscription_duration_six_mounth(call):
    user_id = call.from_user.id  #
    vless_link = generate_vless_link(user_id, call.message.chat.id)
    user = get_user(user_id)
    if (user["is_paid"] == 0):
        update_user_payment_status(user_id, 1)
        cur_time = user["subscription_end_time"]
        if cur_time:
            cur_time = cur_time + timedelta(days=180)
        else:
            cur_time = datetime.now() + timedelta(days=180)
        update_user_subscription_end_time(user_id, cur_time)
    else:
        cur_time = user["subscription_end_time"]
        update_user_subscription_end_time(user_id, cur_time + timedelta(days=180))
    bot.send_message(call.message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(call.message.chat.id, vless_link, parse_mode="Markdown")
    user = get_user(user_id)
    formatted_time = format_subscription_end_time(user["subscription_end_time"])
    bot.send_message(call.message.chat.id, f"Время окончания вашей подписки: {formatted_time}")


@bot.callback_query_handler(func=lambda call: call.data == "12month")
def choose_subscription_duration_year(call):
    user_id = call.from_user.id  #
    vless_link = generate_vless_link(user_id, call.message.chat.id)
    user = get_user(user_id)
    if (user["is_paid"] == 0):
        update_user_payment_status(user_id, 1)
        cur_time = user["subscription_end_time"]
        if cur_time:
            cur_time = cur_time + timedelta(days=360)
        else:
            cur_time = datetime.now() + timedelta(days=360)
        update_user_subscription_end_time(user_id, cur_time)
    else:
        cur_time = user["subscription_end_time"]
        update_user_subscription_end_time(user_id, cur_time + timedelta(days=360))
    bot.send_message(call.message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(call.message.chat.id, vless_link, parse_mode="Markdown")
    user = get_user(user_id)
    formatted_time = format_subscription_end_time(user["subscription_end_time"])
    bot.send_message(call.message.chat.id, f"Время окончания вашей подписки: {formatted_time}")


# Обработчик команды "Назад"
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Купить VPN", callback_data='buy_vpn')
    button2 = types.InlineKeyboardButton("Мой VPN", callback_data='my_vpn')
    button3 = types.InlineKeyboardButton("Реферальная программа", callback_data='referral')
    button4 = types.InlineKeyboardButton("Поддержка", callback_data='support')
    markup.add(button1, button2)
    markup.add(button3, button4)
    sms = "Вы вернулись в Главное меню: "
    bot.send_message(call.message.chat.id, sms, reply_markup=markup)


# Мой ВПН, надо подключить SQL чтоб нормально читать пользователей
@bot.callback_query_handler(func=lambda call: call.data == "my_vpn")
def my_vpn(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    if user and user["is_paid"]:
        current_uuid = get_vless_link(user_id)
        bot.send_message(call.message.chat.id, f"Ваша текущая ссылка: {current_uuid}")
        formatted_time = format_subscription_end_time(user["subscription_end_time"])
        bot.send_message(call.message.chat.id, f"Время окончания вашей подписки: {formatted_time}")
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Продлить подписку", callback_data='proceed_subscription')
        button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
        markup.add(button1)
        markup.add(button2)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Продлить подписку", callback_data='proceed_subscription')
        markup.add(button1)
        bot.send_message(call.message.chat.id, "У вас нет активной подписки.", reply_markup=markup)


# Реферальная ссылка
@bot.callback_query_handler(func=lambda call: call.data == "referral")
def referral_program(call):
    user_name = call.from_user.username
    referral_link = f"https://t.me/studvpn666_bot?start={user_name}"
    bot.send_message(call.message.chat.id, f"Ваша реферальная ссылка: {referral_link}")
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Узнать кол-во рефералов", callback_data='col_ref')
    button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button1)
    markup.add(button2)
    bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "col_ref")
def referral_program(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    bot.send_message(call.message.chat.id,
                     f"Кол-во человек, которые купили подписку по вашей ссылке: {user['referral_count']}")
    bot.send_message(call.message.chat.id, f"Вам было начислено за это: {user['referral_count'] * 5} дней")
    markup = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(button2)


# Поддержка
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
init_db()
bot.polling(none_stop=True, interval=0)