import telebot
import uuid
import json
import paramiko
from telebot import types

# Настройки вашего бота
TELEGRAM_TOKEN = '7948987856:AAERs2G3QxGXKl2J8erLzrJpy5bDH39eHUg'
SERVER_IP = '77.239.100.20'
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'HX6qP0WlYzox'
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
clients = {}


def generate_vless_link(user_id):
    user_uuid = str(uuid.uuid4())
    vless_link = (f"vless://{user_uuid}@{SERVER_IP}:443?type=tcp&security=reality&fp=chrome&pbk=6zedx9tc-YP4Lyh8xFp6LtEv"
                  f"vmCB9iAtoNNc3tt5Ons&sni=whatsapp.com&sid=916e9946&spx=%2F&email={user_id}#StudVPN")

    # Обновление конфигурации на сервере
    update_server_config(user_uuid,user_id)

    return vless_link


def restart_xray(ssh):
    try:
        stdin, stdout, stderr = ssh.exec_command('systemctl restart xray')
        print(stdout.read().decode())
        print(stderr.read().decode())
    except Exception as e:
        print(f"Ошибка при перезапуске Xray: {e}")


def update_server_config(new_uuid,user_id):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=SERVER_USERNAME, password=SERVER_PASSWORD)
        sftp = ssh.open_sftp()

        fl=0
        cur_uuid=""
        if user_id in clients:
            fl=1
            cur_uuid=clients[user_id]

        if fl==0:
            clients[user_id]=new_uuid


        with sftp.open(CONFIG_FILE_PATH, 'r') as config_file:
            config = json.load(config_file)

        # Обновление UUID в конфигурации
        if 'inbounds' in config:
            for inbound in config['inbounds']:
                if 'settings' in inbound and 'clients' in inbound['settings']:
                    if fl==1:
                        for client in inbound['settings']['clients']:
                            if inbound['settings']['clients'][client]['id']==cur_uuid:
                                inbound['settings']['clients'][client]['id']=new_uuid
                                clients[user_id]=new_uuid
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

    except Exception as e:
        print(f"Ошибка при обновлении конфигурации: {e}")


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id  # Получаем user_id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Купить VPN", "Мой VPN", "Реферальная программа", "Поддержка", "О нас/FAQ")
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите опцию:", reply_markup=markup)



# Обработчик кнопки "Купить VPN"
@bot.message_handler(func=lambda message: message.text == "Купить VPN")
def buy_vpn(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Тарифные планы", "Назад")
    bot.send_message(message.chat.id, "Выберите тарифный план:", reply_markup=markup)



#Обработчик команды "Назад"
@bot.message_handler(func=lambda message: message.text == "Назад")
def back_to_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Купить VPN", "Мой VPN", "Реферальная программа", "Поддержка", "О нас/FAQ")
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=markup)

#Мой ВПН, надо подключить SQL чтоб нормально читать пользователей
@bot.message_handler(func=lambda message: message.text == "Мой VPN")
def my_vpn(message):
    user_id = message.from_user.id
    if user_id in clients:
        current_uuid = clients[user_id]
        bot.send_message(message.chat.id, f"Ваш текущий тарифный план: {current_uuid}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Продлить подписку", "Инструкции по настройке", "Назад")
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "У вас нет активной подписки.")



#Реферальная ссылка
@bot.message_handler(func=lambda message: message.text == "Реферальная программа")
def referral_program(message):
    user_id = message.from_user.id
    referral_link = f"https://StudVPN/referral/{user_id}"
    bot.send_message(message.chat.id, f"Ваша реферальная ссылка: {referral_link}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Статистика рефералов", "Назад")
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)



#Статистика реферало, надо настроить базу данных
@bot.message_handler(func=lambda message: message.text == "Статистика рефералов")
def referral_statistics(message):
    bot.send_message(message.chat.id, f"В разработке надо подключить базу данных")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add( "Назад")
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


#Поддержка
@bot.message_handler(func=lambda message: message.text == "Поддержка")
def support(message):
    bot.send_message(message.chat.id, "Задайте вопрос, который вас интересует. Вам ответит первый освободившийся модератор")
    bot.send_message(message.chat.id, "Вам ответит первый освободившийся модератор")
    bot.send_message(message.chat.id, "@gblev")

#О нас
@bot.message_handler(func=lambda message: message.text == "О нас/FAQ")
def about_faq(message):
    faq = ( "О нас:\n" "Мы предоставляем надежные VPN-услуги для защиты вашей конфиденциальности.\n" )
    bot.send_message(message.chat.id, faq)



# Запуск бота
bot.polling(none_stop=True, interval=0)
