import time
import sqlite3
import datetime
import paramiko
import threading
DATABASE_FILE = "vpn_keys.db"
CONFIG_FILE_PATH = '/usr/local/etc/xray/config.json'
SERVER_IP = '77.239.100.20'
DATABASE_FILE = "vpn_keys.db"
SERVER_PORT = 443  # Обычно 22 для SSH
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'HX6qP0WlYzox'
UUID_KEYWORD = "id: "
from database_utils import get_device_uuid,get_device_payment_status,get_device_subscription_end_time,update_device_status

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

def check_and_remove_expired_uuids():
    """Проверяет базу данных на наличие просроченных подписок и удаляет UUID из файла конфигурации."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT telegram_id, device_type
            FROM user_devices
        """)

        all_users = cursor.fetchall()  # Получаем всех пользователей

        for telegram_id, device_type in all_users:
            subscription_end_time = get_device_subscription_end_time(telegram_id, device_type)
            user_uuid = get_device_uuid(telegram_id, device_type)
            if subscription_end_time:  # Если есть дата окончания и UUID
                try:
                    end_time = datetime.datetime.fromisoformat(subscription_end_time)
                    device_uuid = get_device_uuid(telegram_id, device_type)
                    if end_time <= datetime.datetime.now():  # Сравниваем с текущим временем
                        if remove_uuid_from_config(CONFIG_FILE_PATH, user_uuid):
                            update_device_status(device_uuid, False, None)
                            print(f"UUID {user_uuid} removed for user {telegram_id}")
                        else:
                            print(f"Failed to remove UUID {user_uuid} for user {telegram_id}")
                except ValueError as e:
                    print(f"Error parsing date for user {telegram_id}: {e}")
            else:
                print(f"No subscription end time or UUID found for user {telegram_id}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


# Запуск бота
def scheduled_task():
    """Функция, которая будет выполняться каждый час."""
    print("Running scheduled task...")
    check_and_remove_expired_uuids()
    print("Scheduled task finished.")

def run_scheduler():
    """Запускает планировщик задач в отдельном потоке."""
    while True:
        now = datetime.datetime.now()
        next_hour = now.replace(hour=0, second=0, microsecond=0) + datetime.timedelta(minutes=1)
        wait_seconds = (next_hour - now).total_seconds()

        print(f"Waiting {wait_seconds:.0f} seconds until next scheduled task...")
        time.sleep(wait_seconds)
        scheduled_task()

# --- Главная функция ---
def main():
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True  # Позволяет программе завершиться, даже если поток-планировщик еще работает
    scheduler_thread.start()

    # Здесь можно добавить код, который выполняет другие задачи вашего приложения
    print("Main application running...")
    while True:
        time.sleep(1)  # П