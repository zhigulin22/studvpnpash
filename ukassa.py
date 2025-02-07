import requests
import uuid

# Данные ЮKassa
SHOP_ID = '1026364'
API_KEY = 'test_PeQtNvYjivtuj1BEiGeiX5-TRsL_psAvCGFgYVafnPo'
RETURN_URL = 'https://t.me/studvpn666_bot'

def create_payment(amount, description):
    payment_id = str(uuid.uuid4())  # Уникальный ID платежа
    idempotence_key = str(uuid.uuid4())  # Уникальный идемпотентный ключ

    payment_data = {
        "amount": {"value": amount, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": RETURN_URL},
        "capture": True,
        "description": description,
        "metadata": {"order_id": payment_id}
    }

    headers = {
        "Idempotence-Key": idempotence_key,  # Обязательный заголовок
        "Authorization": f"Basic {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.yookassa.ru/v3/payments",
            json=payment_data,
            headers=headers,               # Передача заголовков
            auth=(SHOP_ID, API_KEY)
        )

        if response.status_code == 200:
            payment_info = response.json()
            return payment_info["confirmation"]["confirmation_url"], payment_info["id"]
        else:
            print("Ошибка при создании платежа:", response.status_code, response.text)
            return None

    except Exception as e:
        print("Ошибка соединения с ЮKassa:", e)
        return None


def check_payment_status(payment_id):
    url = f"https://api.yookassa.ru/v3/payments/{payment_id}"
    try:
        response = requests.get(
            url,
            auth=(SHOP_ID, API_KEY)
        )
        if response.status_code == 200:
            payment_info = response.json()
            return payment_info.get('status')  # Вернёт 'succeeded', 'pending', 'canceled' и т.д.
        else:
            print("Ошибка при проверке статуса платежа:", response.status_code, response.text)
            return None
    except Exception as e:
        print("Ошибка соединения с ЮKassa при проверке статуса:", e)
        return None