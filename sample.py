import sqlite3
import datetime
import telebot
from telebot.async_telebot import AsyncTeleBot
import asyncssh
from aiogram import Bot, Dispatcher, types
import pandas as pd
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telebot import types
import json
import csv
import uuid
import os  # Import the 'os' module
import asyncio

SERVER_IP = '77.239.100.20'
EXCEL_FILE = '/Users/glebstudent/Downloads/exported_all_db (1)/user_devices.csv'
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
TELEGRAM_TOKEN = '7795571968:AAFDElnnIqSHpUHjFv19hoAWljr54Rok1jE'
SERVER_PASSWORD = 'HX6qP0WlYzox'
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'
UUID_KEYWORD = "id: "
DATABASE_FILE = "vpn5_keys.db"
DEVICE_LIMIT = 4  # Maximum number of devices per user
ALLOWED_DEVICE_TYPES = ["iPhone", "Mac", "Android", "Windows"]

bot = AsyncTeleBot(TELEGRAM_TOKEN)




@bot.message_handler(commands=['start'])
async def start(message):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(
        text="Крутить колесо фортуны",
        web_app=types.WebAppInfo(url="https://murad0998.github.io/wheel.html/")
    )
    markup.add(button)

    await bot.send_message(
        message.chat.id,
        "✅ Оплата прошла успешно!\n\n🎉 У вас есть возможность крутить колесо фортуны. Нажмите кнопку ниже для перехода к мини-приложению.",
        reply_markup=markup
    )



async def restart_xray(ssh):
    try:
        result = await ssh.run('systemctl restart xray',check=True)
    except Exception as e:
        print(f"Ошибка при перезапуске Xray: {e}")


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


async def main():
    await bot.polling(none_stop=True)



if __name__ == '__main__':
    asyncio.run(main())
