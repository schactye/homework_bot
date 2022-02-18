
from asyncio.log import logger
from http import HTTPStatus
from http.client import REQUEST_ENTITY_TOO_LARGE, REQUEST_TIMEOUT
import logging
import os
import time
from urllib import request
from telegram import Bot
from dotenv import load_dotenv

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
   try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
   except telegram.error.TelegramError:
        logger.error('Сбой при отправке сообщения')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = request.Request.get(ENDPOINT, headers=HEADERS, params=params)
    except request.Request.exceptions.ConnectTimeout as error:
        logger.error(f'Превышено время ожидания ответа сервера {error}')
        raise error
    except request.Request.exceptions.RequestException as error:
        logger.error(f'Произошла ошибка соединения {error}')
        raise error
    if response.status_code != HTTPStatus.OK:
        logger.error(f'Сбой в работе программы: Эндпоинт {ENDPOINT} '
                     f'недоступен. Код ответа API: {response.status_code}')
        raise request.Request.HTTPError('Неверный код ответа сервера.'
                                 f'{response.status_code}')
    try:
        return response.json()
    except ValueError as error:
        logger.error(error)
        raise ValueError('Ответ не содержит валидный JSON')


def check_response(response):
    if not isinstance(response, dict):
        raise TypeError('Ожидался словарь')
    if len(response) == 0:
        raise Exception('Ошибка в данных, пустой словарь')
    if 'homeworks' not in response.keys():
        message = 'Отсутствие ключа \'homeworks\' в словаре '
        logger.error(message)
        raise Exception(message)
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise Exception('Ошибка в данных')
    return homeworks


def parse_status(homework):
    verdict = HOMEWORK_STATUSES[homework.get('status')]
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise Exception("No homework name")
    if verdict is None:
        raise Exception("No verdict")
    logging.info(f'got verdict {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    env = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for var in env:
        if var is None:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {var}')
            return False
    return True


def main():
    if not check_tokens():
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    tmp_status = 'reviewing'
    error_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
            logger.info(
                f'Изменений нет, {RETRY_TIME} секунд и проверяем API')
            current_timestamp = response.get('current_date', current_timestamp)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if error_message != message:
                error_message = message
                send_message(bot, error_message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
