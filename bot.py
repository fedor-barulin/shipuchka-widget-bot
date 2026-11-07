"""Minimal bot that sends an HTML widget (HTMLBubbles) and answers its requests.

/start sends widgets/probe.html: it shows what the widget engine can do on this device and
has a button that asks the bot. The bot answers every TelegramWidget.request() with JSON.
Replace the probe with your own HTML and answer_query() with your own logic.
"""
import json
import logging
import os
import time
from pathlib import Path

import tgwidget  # registers the layer-233 types and switches Telethon to layer 233
from tgwidget import InputMediaWidget, SetBotWidgetQueryAnswerRequest, UpdateBotWidgetQuery

from telethon import TelegramClient, events, functions
from telethon.errors import RPCError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("widget-bot")

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION = os.environ.get("SESSION_PATH", "data/bot")
WIDGET = Path(os.environ.get("WIDGET_FILE", Path(__file__).parent / "widgets" / "probe.html"))


async def send_widget(client, peer):
    html = WIDGET.read_text(encoding="utf-8")  # read on every send: change the file without a restart
    try:
        await client(functions.messages.SendMediaRequest(peer=peer, media=InputMediaWidget(html), message=""))
    except RPCError as e:
        # INPUT_MEDIA_WIDGET_TOO_LARGE: over 32 KB or over 4 KB compressed
        # INPUT_MEDIA_WIDGET_NOT_ALLOWED: this chat type does not take widgets (on 2026-11-07 only the private chat did)
        log.warning("send failed: %s", e)
        await client.send_message(peer, f"Telegram не принял виджет: {e}")


def answer_query(user_id, data):
    """Your logic goes here. data is at most 64 bytes, the answer at most 1 KB, within 15 seconds."""
    return json.dumps({"echo": data, "user": user_id, "time": time.strftime("%H:%M:%S")}, ensure_ascii=False)


def main():
    Path(SESSION).parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(SESSION, API_ID, API_HASH)

    @client.on(events.NewMessage(pattern=r"^/start", func=lambda e: e.is_private))
    async def start(event):
        await send_widget(client, event.chat_id)

    @client.on(events.Raw(UpdateBotWidgetQuery))
    async def widget_query(update):
        data = update.data.decode("utf-8", "replace")
        log.info("widget query from %s (%s): %s", update.user_id, update.chat_type, data)
        try:
            await client(SetBotWidgetQueryAnswerRequest(update.query_id, answer_query(update.user_id, data)))
        except Exception:
            log.exception("answer failed")

    client.start(bot_token=BOT_TOKEN)
    log.info("widget bot started")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
