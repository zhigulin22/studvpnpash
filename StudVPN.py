import telebot
import uuid
import json
import paramiko
from telebot import types
from datetime import datetime, timedelta
from database_utils import init_db, add_user, get_user, update_user_uuid, update_user_payment_status, update_user_referral_count, update_user_subscription_end_time,format_subscription_end_time
from button_pay import back_to_main_menu,choose_subscription_duration
# Настройки вашего бота
TELEGRAM_TOKEN = '7948987856:AAERs2G3QxGXKl2J8erLzrJpy5bDH39eHUg'
SERVER_IP = '77.239.100.20'
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'HX6qP0WlYzox'
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
clients={}

def generate_vless_link(user_id,message_chat_id):
    user_uuid = str(uuid.uuid4())
    vless_link = f"vless://{user_uuid}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEvvmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#StudVPN"

    # Обновление конфигурации на сервере
    update_server_config(user_uuid,user_id,message_chat_id)

    return vless_link


def restart_xray(ssh):
    try:
        stdin, stdout, stderr = ssh.exec_command('systemctl restart xray')
        print(stdout.read().decode())
        print(stderr.read().decode())
    except Exception as e:
        print(f"Ошибка при перезапуске Xray: {e}")


def update_server_config(new_uuid,user_id,message_chat_id):
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
                        for client in inbound['settings']['clients']:
                            if inbound['settings']['clients'][client]['id'] == cur_uuid:
                                inbound['settings']['clients'][client]['id']=new_uuid
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
        "Забудьте о блокировках и плохом соединении.\n\n"
        "С нашим ботом у вас будет: \n"
        "*   Самая высокая скорость\n"
        "*   Конфиденциальность ваших данных\n"
        "*   Удобный и понятный интерфейс\n"
        "*   Защита в публичных Wi-Fi сетях"
    )
    user_id = message.from_user.id  # Получаем user_id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Купить VPN", "Мой VPN", "Реферальная программа", "Поддержка")
    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)



# Обработчик кнопки "Купить VPN"
@bot.message_handler(func=lambda message: message.text == "Купить VPN")
def buy_vpn(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("iPhone", "Android", "MacBook", "Windows" "Главное меню")
    bot.send_message(message.chat.id, "Выберите устройство, для которого хотите купить ВПН:", reply_markup=markup)



@bot.message_handler(func=lambda message: message.text in ["iPhone", "Android", "MacBook", "Windows"])
def choose_mod(message):
    device = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("1 месяц - 99₽", "3 месяца - 259₽", "6 месяцев - 499₽", "12 месяцев - 999₽", "Главное меню")
    bot.send_message(message.chat.id, f"Вы выбрали {device}. Выберите срок подписки:", reply_markup=markup)



@bot.message_handler(func=lambda message: message.text == "1 месяц - 99₽")
def choose_subscription_duration_mounth(message):
    #оплата
    user_id = message.from_user.id  #
    vless_link = generate_vless_link(user_id,message.chat.id)
    user = get_user(user_id)
    if(user["is_paid"]==0):
        update_user_payment_status( user_id, 1)
        cur_time=user["subscription_end_time"]
        if cur_time:
            cur_time = cur_time + timedelta(days=30)
        else:
            cur_time = datetime.now() + timedelta(days=30)
        update_user_subscription_end_time(user_id, cur_time)
    else:
        cur_time = user["subscription_end_time"]
        update_user_subscription_end_time(user_id, cur_time + timedelta(days=30))
    bot.send_message(message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(message.chat.id, vless_link)
    user = get_user(user_id)
    formatted_time = format_subscription_end_time(user["subscription_end_time"])
    bot.send_message(message.chat.id, f"Время окончания вашей подписки: {formatted_time}")



#На 3 месяца
@bot.message_handler(func=lambda message: message.text == "3 месяца - 259₽")
def choose_subscription_duration_tree_mounth(message):
    user_id = message.from_user.id  #
    vless_link = generate_vless_link(user_id, message.chat.id)
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
    bot.send_message(message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(message.chat.id, vless_link)

#На 180 дней
@bot.message_handler(func=lambda message: message.text == "6 месяцев - 499₽")
def choose_subscription_duration_six_mounth(message):
    user_id = message.from_user.id  #
    vless_link = generate_vless_link(user_id, message.chat.id)
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
    bot.send_message(message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(message.chat.id, vless_link)


@bot.message_handler(func=lambda message: message.text == "12 месяцев - 999₽")
def choose_subscription_duration_year(message):
    user_id = message.from_user.id  #
    vless_link = generate_vless_link(user_id, message.chat.id)
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
    bot.send_message(message.chat.id, f"Ваша VLESS ссылка:")
    bot.send_message(message.chat.id, vless_link)


#Обработчик команды "Назад"
@bot.message_handler(func=lambda message: message.text == "Главное меню")
def back_to_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Купить VPN", "Мой VPN", "Реферальная программа", "Поддержка")
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=markup)



#Мой ВПН, надо подключить SQL чтоб нормально читать пользователей
@bot.message_handler(func=lambda message: message.text == "Мой VPN")
def my_vpn(message):
    user_id = message.from_user.id
    if user_id in clients:
        current_uuid = clients[user_id]
        bot.send_message(message.chat.id, f"Ваш текущий тарифный план: {current_uuid}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Продлить подписку", "Инструкции по настройке", "Главное меню")
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Главное меню")
        bot.send_message(message.chat.id, "У вас нет активной подписки.", reply_markup=markup)



#Реферальная ссылка
@bot.message_handler(func=lambda message: message.text == "Реферальная программа")
def referral_program(message):
    user_name = message.from_user.username
    referral_link = f"https://t.me/studvpn666_bot?start={user_name}"
    bot.send_message(message.chat.id, f"Ваша реферальная ссылка: {referral_link}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Статистика рефералов", "Главное меню")
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)




#Поддержка
@bot.message_handler(func=lambda message: message.text == "Поддержка")
def support(message):
    bot.send_message(message.chat.id, "Задайте вопрос, который вас интересует. Вам ответит первый освободившийся модератор")
    bot.send_message(message.chat.id, "Вам ответит первый освободившийся модератор")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add( "Главное меню")
    bot.send_message(message.chat.id, "@gblev", reply_markup=markup)




# Запуск бота
bot.polling(none_stop=True, interval=0)
init_db()