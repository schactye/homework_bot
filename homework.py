from asyncio.log import logger
from http import HTTPStatus
import logging
import os
import requests
import time
from dotenv import load_dotenv
import telegram

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    filemode='a'
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отсылаем сообщение."""
    logging.info(f'message send {message}')
    return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Берем информацию от сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params
                                         )
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        status_code = homework_statuses.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    try:
        return homework_statuses.json()
    except ValueError:
        logging.Logger.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверка полученной информации."""
    if not isinstance(response, dict):
        raise TypeError('Ожидался словарь')
    if len(response) == 0:
        raise Exception('Ошибка в данных, пустой словарь')
    if 'homeworks' not in response.keys():
        message = 'Отсутствие ключа \'homeworks\' в словаре '
        logging.Logger.error(message)
        raise Exception(message)
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise Exception('Ошибка в данных')
    return homeworks


def parse_status(homework):
    """Достаем статус работы."""
    if not isinstance(homework, dict):
        message = 'Некорректный тип данных.'
        logger.error(message)
        raise TypeError(message)
    if 'homework_name' not in homework:
        parse_message = 'Нет ключа "homework_name".'
        raise KeyError(parse_message)
    if 'status' not in homework:
        parse_message = 'Нет ключа "status".'
        raise KeyError(parse_message)
    if homework['status'] not in HOMEWORK_STATUSES:
        message = "Неожиданный статус."
        logger.error(message)
        raise os.error(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка полученной информации."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def main():
    """Главный цикл работы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    url = ENDPOINT
    while True:
        try:
            get_api_answer_result = get_api_answer(url, current_timestamp)
            check_response_result = check_response(get_api_answer_result)
            if check_response_result:
                for homework in check_response_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error('Bot down')
            bot.send_message(
                text=f'Сбой в работе программы: {error}'
            )
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
