# pylint: disable=C0114
import asyncio
import html
import logging
import os
import sys

from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.types import InputRichMessage, Message

from core.config import BOT_VERSION, DEV_ADMINS, bot

log = logging.getLogger(__name__)

UPDATE_TIMEOUT = 300


async def notify_startup() -> None:
    for name, user_id in DEV_ADMINS.items():
        try:
            await bot.send_rich_message(
                user_id,
                InputRichMessage(
                    html=f'<h2>البوت اشتغل</h2><p>الاصدار {BOT_VERSION}</p>', is_rtl=True
                ),
            )
        except RPCError as exc:
            log.warning('failed notifying dev %s: %s', name, exc)


async def _run_command(command: list[str]) -> tuple[int, str]:
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            ),
            timeout=UPDATE_TIMEOUT,
        )
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=UPDATE_TIMEOUT)
    except (TimeoutError, OSError) as exc:
        log.error('failed running %s: %s', command[0], exc)
        return 1, str(exc)
    return proc.returncode or 0, output.decode('utf-8', errors='replace')


@Client.on_message(
    filters.private & filters.user(list(DEV_ADMINS.values())) & filters.regex(r'^تحديث( البوت)?$')
)
async def update_bot(client: Client, message: Message) -> None:
    await bot.send_rich_message(
        message.chat.id,
        InputRichMessage(
            html='<h2>جاري تحديث البوت</h2><p>سحب التعديلات وتحديث الحزم</p>', is_rtl=True
        ),
    )
    for name, command in (('سحب التعديلات', ['git', 'pull']), ('تحديث الحزم', ['uv', 'sync'])):
        code, output = await _run_command(command)
        if code != 0:
            await bot.send_rich_message(
                message.chat.id,
                InputRichMessage(
                    html=f'<h2>فشل {name}</h2><p><code>{html.escape(output[-200:])}</code></p>',
                    is_rtl=True,
                ),
            )
            return
    await bot.send_rich_message(
        message.chat.id,
        InputRichMessage(html='<h2>تم التحديث</h2><p>جاري اعادة تشغيل البوت</p>', is_rtl=True),
    )
    os.execv(sys.executable, [sys.executable, *sys.argv])
