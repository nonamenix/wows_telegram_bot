import json
import os

import aiohttp

from aiotg import Bot
from telegram import ReplyKeyboardMarkup, KeyboardButton

from actions import ChatAction
import logging

# Logging
logging.basicConfig(
    level=getattr(logging, os.environ.get('BOT_LOGGING_LEVEL', 'DEBUG')),
    format='%(asctime)s | %(name)s | %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
logger.addHandler(ch)

bot = Bot(
    api_token=os.environ["BOT_TOKEN"],
    botan_token=os.environ["BOTAN_TOKEN"]
)


async def mainmenu(chat, message):
    elements = [
        'Не дошли деньги!',
        'У меня проблема!',
        'Скачать клиент',
        'Что нового?',
        'Доложи обстановку!',
        'Отмена'
    ]
    return await chat.bot.send_message(
        chat_id=chat.id,
        text="Чем я могу помочь?",
        reply_markup=json.dumps(
            ReplyKeyboardMarkup(
                [[KeyboardButton(text=el)] for el in elements],
                resize_keyboard=True,
                one_time_keyboard=True
            ).to_dict()
        )
    )


async def extramenu(chat, message):
    elements = [
        'Статистика',
        'Опросы',
        'Радио',
    ]
    return await chat.bot.send_message(
        chat_id=chat.id,
        text="Я так же умею:",
        reply_markup=json.dumps(
            ReplyKeyboardMarkup(
                [[KeyboardButton(text=el)] for el in elements],
                resize_keyboard=True,
                one_time_keyboard=True
            ).to_dict()
        )
    )


@bot.command("/start")
async def start(chat, message):
    await chat.send_text('Добро пожаловать, Капитан!')
    await default(chat, message)


@bot.command("/restart")
async def restart(chat, message):
    await chat.send_text(
        'С возвращением, Капитан!',
        disable_web_page_preview=True
    )
    await mainmenu(chat, message)


@bot.command("/stop")
def stop(chat, message):
    return chat.send_text(
        'Всего хорошего, Капитан!',
        disable_web_page_preview=True
    )


@bot.command("Что нового")
@bot.command("новости")
@bot.command("/news")
async def news(chat, message):
    await chat.send_text(
        'Новостной канал: http://telegram.me/world_of_warships',
        disable_web_page_preview=True
    )
    await mainmenu(chat, message)


@bot.command('скачать')
@bot.command('/download')
async def download(chat, message):
    await chat.send_text(
        text='Скачать игру: http://worldofwarships.ru/ru/content/game/?autodownload',
    )
    await mainmenu(chat, message)


def convert_to_md(text):
    mapping = {
        '<mark class="mark">': '*',
        '</mark>': '*',
    }

    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


@bot.command('решить (.+)')
@bot.command('help (.+)')
async def help(chat, match):
    await chat.send_chat_action(action=ChatAction.TYPING)

    matched = match.group(1)

    api_url = "https://ru.wargaming.net/support/api/kb/search?query={query}&categoryId=3&offset=0".format(
        query=matched
    )

    text = "К сожалению я ничего не нашел по запросу: {}".format(matched)

    with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status == 200:
                body = await resp.json()
                if body['total'] > 0:
                    answers = body['articles']
                    answer_template = '{title} https://ru.wargaming.net/support/kb/articles/{id}\n\n'
                    text = convert_to_md("".join([answer_template.format(**answer) for answer in answers]))

    await chat.send_text(
        text=text,
        disable_web_page_preview=True,
        parse_mode='markdown'
    )


@bot.command('отмена')
@bot.command('/cancel')
async def cancel(chat, message):
    return await chat.send_text(
        text="Так точно. Отменено!",
    )


async def retrieve_steps(chat, api_url, extra_links=None):
    text = "Капитан, уточни, пожалуйста, в чем проблема: \n\n"

    step_template = "- {title} \n⇨ /troubleshooter_steps_{id}\n\n"

    if extra_links:
        for link in extra_links:
            text += step_template.format(**link)

    with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status == 200:
                body = await resp.json()

                steps = body['steps']

                if len(steps) > 0:
                    for step in steps:
                        text += step_template.format(**step)

                    if 'parent_id' in body and body['parent_id']:
                        text += 'Вернуться назад /troubleshooter_steps_{}'.format(body['parent_id'])

                    await chat.bot.send_message(
                        chat_id=chat.id,
                        text=text,
                    )
                else:
                    await chat.bot.send_message(
                        chat_id=chat.id,
                        text="Решение: {} https://ru.wargaming.net/support/troubleshooter/steps/{}".format(
                            body['title'],
                            body['id']
                        ),
                    )
                    await quiz(chat)


@bot.command('/troubleshooter_steps_(\d+)')
async def troubleshooter_steps(chat, matched=None, step_id=None):
    if not step_id:
        step_id = matched.group(1)
    api_url = 'https://ru.wargaming.net/support/api/troubleshooter/steps/{step_id}'.format(
        step_id=step_id
    )
    await retrieve_steps(chat, api_url)


@bot.command('/troubleshooter_category_(\d+)')
async def troubleshooter_category(chat, match):
    category_id = match.group(1)
    api_url = 'https://ru.wargaming.net/support/api/troubleshooter/categories/{category_id}'.format(
        category_id=category_id
    )
    await retrieve_steps(chat, api_url)


@bot.command('У меня проблема')
@bot.command('Мне нужен помощник')
@bot.command('помощник')
@bot.command('/troubleshooter')
async def troubleshooter(chat, message):
    api_url = 'https://ru.wargaming.net/support/api/troubleshooter/categories/{category_id}'.format(
        category_id=16
    )
    await retrieve_steps(chat, api_url, extra_links=[
        {'title': 'Финансовые вопросы', 'id': 1468}
    ])


@bot.command('menu')
@bot.command('меню')
@bot.command('вернуться в меню')
async def backtomenu(chat, message):
    await mainmenu(chat, message)


@bot.default
async def default(chat, match):
    await mainmenu(chat, match)


@bot.callback
async def callback(query):
    await query.answer(
        text="hello"
    )


@bot.command("Финансовый вопрос")
@bot.command("не дошли деньги")
async def money(chat, message):
    await troubleshooter_steps(chat, step_id=1468)


@bot.command('/serverinfo')
@bot.command('Доложи обстановку!')
async def serverinfo(chat, message):
    api_url = "http://worldofwarships.ru/game-server-status/"

    with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers={'X-Requested-With': 'XMLHttpRequest'}) as resp:
            status = await resp.json()
            if resp.status == 200 and status['is_available']:
                await chat.send_text(text="Сервер доступен. Количество игроков: {}".format(
                    status['online_players']
                ))
            else:
                await chat.send_text(text="Сервер не доступен!")


@bot.command('/quiz')
async def quiz(chat, **kwargs):
    await chat.send_text(
        text="Капитан, помог ли я вам?",
        reply_markup=json.dumps(
            ReplyKeyboardMarkup([
                [KeyboardButton(text="Да, спасибо.")],
                [KeyboardButton(text="Нет! Два дня драить палубу!")],
            ],
                resize_keyboard=True,
                one_time_keyboard=True
            ).to_dict()
        )
    )


def get_user_stat():
    pass  # use inline query https://core.telegram.org/bots/api/#inline-mode


if __name__ == "__main__":
    logger.info("Running...")
    bot.run()
