# pylint: disable=C0114
import asyncio
import faulthandler
import logging
import signal

from pytgcalls import idle

from bot import bot
from helper import start_helpers
from logger import setup_logging
from plugins.bot.dev_update import notify_startup

log = logging.getLogger(__name__)

faulthandler.enable()
faulthandler.register(signal.SIGUSR1)
setup_logging()


async def main() -> None:
    log.info('starting bot')
    await bot.start()
    log.info('bot started successfully')
    await start_helpers()
    log.info('helper accounts started successfully')
    await notify_startup()
    await idle()
    log.info('shutdown complete')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info('shutdown complete')
