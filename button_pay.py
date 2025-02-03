import telebot
import uuid
import json
import paramiko
from telebot import types
TELEGRAM_TOKEN = '7948987856:AAERs2G3QxGXKl2J8erLzrJpy5bDH39eHUg'
SERVER_IP = '77.239.100.20'
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'HX6qP0WlYzox'
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
@bot.message_handler(func=lambda message: message.text == "Назад")
def back_to_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Купить VPN", "Мой VPN", "Реферальная программа", "Поддержка")
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["1 месяц - 99₽", "3 месяца - 259₽", "6 месяцев - 499₽","12 месяцев - 999₽"])
def choose_subscription_duration(message):
        # оплата
        user_id = message.from_user.id  #
        vless_link = generate_vless_link(user_id)
        bot.send_message(message.chat.id, f"Ваша VLESS ссылка:")
        bot.send_message(message.chat.id, vless_link)