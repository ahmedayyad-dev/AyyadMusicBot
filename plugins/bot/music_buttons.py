# pylint: disable=C0114
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

import access
import helper
import nowplaying
import player
from languages import text

ACTION_PERMISSIONS = {'skip': 'skip', 'pause': 'pause', 'resume': 'resume', 'stop': 'stop'}


@Client.on_callback_query(filters.regex(r'^mq:'))
async def music_button(client: Client, query: CallbackQuery) -> None:
    parts = query.data.split(':')
    if len(parts) < 2:
        await query.answer()
        return
    action = parts[1]
    chat_id = query.message.chat.id
    if action == 'queue':
        if not await access.ensure_access(query, 'queue'):
            return
        current, upcoming = player.queue_snapshot(chat_id)
        await nowplaying.edit_queue(
            chat_id,
            query.message.id,
            current,
            upcoming,
            int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
        )
        await query.answer()
        return
    if action not in ACTION_PERMISSIONS:
        await query.answer()
        return
    if not await access.ensure_access(query, ACTION_PERMISSIONS[action]):
        return
    if action == 'skip':
        item = await helper.play_next(chat_id)
        if item is None:
            await query.answer(text(None, 'skip_ended'), show_alert=True)
        else:
            await query.answer(
                text(None, 'skip_done_next', track=f'{item.track.title} - {item.track.artist}')
            )
    elif action == 'pause':
        await helper.pause_call(chat_id)
        player.set_paused(chat_id, True)
        await query.answer(text(None, 'pause_done'))
        await nowplaying.refresh(chat_id)
    elif action == 'resume':
        await helper.resume_call(chat_id)
        player.set_paused(chat_id, False)
        await query.answer(text(None, 'resume_done'))
        await nowplaying.refresh(chat_id)
    else:
        await helper.leave_call(chat_id, leave_chat=False)
        await nowplaying.clear(chat_id)
        player.close(chat_id)
        await query.answer(text(None, 'stop_done'))
