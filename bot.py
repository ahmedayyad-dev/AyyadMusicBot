# pylint: disable=C0114
from pyrogram import Client

from constants import API_ID, API_HASH, TOKEN

bot = Client(
    'bot',
    API_ID,
    API_HASH,
    bot_token=TOKEN,
    fetch_replies=False,
    fetch_topics=False,
    fetch_stories=False,
    fetch_stickers=False,
    plugins=dict(root='plugins/bot'),
)
