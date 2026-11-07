"""Telegram HTML widgets (HTMLBubbles) over MTProto, for Telethon 1.45.

Bot API 10.3 has no method for widgets; MTProto layer 233 has. The schema is taken from
Telegram Desktop (Telegram/SourceFiles/mtproto/scheme/api.tl). It differs from the
widget-sandbox docs (other flags in inputMediaWidget): the server accepts the Desktop one.

Import this module before creating TelegramClient: it registers the types and switches
Telethon (layer 229) to layer 233, otherwise the server does not send widget queries.
"""
import os
import struct

from telethon.tl import alltlobjects, types
from telethon.tl.tlobject import TLObject, TLRequest

WIDTH = int(os.environ.get("WIDGET_WIDTH", "430"))   # Telegram fits it to the bubble: 430 desktop, ~362 phone
HEIGHT = int(os.environ.get("WIDGET_HEIGHT", "580"))  # at most 600


def _s(o, v):
    return o.serialize_bytes(v)


class InputMediaWidget(TLObject):
    """inputMediaWidget#44f6c04e flags:# allow_queries:flags.0?true shared_widget:flags.1?true
    width:int height:int html:string public_data:flags.2?string chat_data:flags.3?string = InputMedia"""
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0x44F6C04E, 0xFAF846F4

    def __init__(self, html, width=WIDTH, height=HEIGHT, allow_queries=True, public_data=None, chat_data=None,
                 shared_widget=False):
        self.html, self.width, self.height = html, width, height
        self.allow_queries, self.public_data, self.chat_data = allow_queries, public_data, chat_data
        self.shared_widget = shared_widget

    def to_dict(self):
        return {"_": "InputMediaWidget", "width": self.width, "height": self.height}

    def _bytes(self):
        flags = (1 if self.allow_queries else 0) | (2 if self.shared_widget else 0) \
            | (4 if self.public_data is not None else 0) \
            | (8 if self.chat_data is not None else 0)
        out = [struct.pack("<IIii", self.CONSTRUCTOR_ID, flags, self.width, self.height), _s(self, self.html)]
        if self.public_data is not None:
            out.append(_s(self, self.public_data))
        if self.chat_data is not None:
            out.append(_s(self, self.chat_data))
        return b"".join(out)


class InputBotInlineMessageWidget(TLObject):
    """inputBotInlineMessageWidget#f597a3f0 flags:# allow_queries:flags.0?true shared_widget:flags.1?true
    invert_media:flags.6?true width:int height:int html:string public_data:flags.2?string chat_data:flags.3?string
    reply_markup:flags.4?ReplyMarkup message:string entities:flags.5?Vector<MessageEntity> = InputBotInlineMessage"""
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0xF597A3F0, types.InputBotInlineMessageText.SUBCLASS_OF_ID

    def __init__(self, html, width=WIDTH, height=HEIGHT, allow_queries=True, reply_markup=None, message=""):
        self.html, self.width, self.height = html, width, height
        self.allow_queries, self.reply_markup, self.message = allow_queries, reply_markup, message

    def to_dict(self):
        return {"_": "InputBotInlineMessageWidget", "width": self.width, "height": self.height}

    def _bytes(self):
        flags = (1 if self.allow_queries else 0) | (16 if self.reply_markup is not None else 0)
        out = [struct.pack("<IIii", self.CONSTRUCTOR_ID, flags, self.width, self.height), _s(self, self.html)]
        if self.reply_markup is not None:
            out.append(bytes(self.reply_markup))
        out.append(_s(self, self.message))
        return b"".join(out)


class SetBotWidgetQueryAnswerRequest(TLRequest):
    """messages.setBotWidgetQueryAnswer#f8cdec6a flags:# query_id:long result:flags.0?string = Bool"""
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0xF8CDEC6A, 0xF5B399AC

    def __init__(self, query_id, result=None):
        self.query_id, self.result = query_id, result

    def to_dict(self):
        return {"_": "SetBotWidgetQueryAnswerRequest", "query_id": self.query_id}

    def _bytes(self):
        out = [struct.pack("<IIq", self.CONSTRUCTOR_ID, 1 if self.result is not None else 0, self.query_id)]
        if self.result is not None:
            out.append(_s(self, self.result))
        return b"".join(out)


class _Parsed(TLObject):
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def to_dict(self):
        return {"_": type(self).__name__, **{k: v for k, v in self.__dict__.items() if k != "payload"}}


class WidgetQueryTypeData(_Parsed):
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0x16D8CF0B, 0x7A3B1C11

    @classmethod
    def from_reader(cls, r):
        return cls(flags=r.read_int())


class UpdateBotWidgetQuery(_Parsed):
    """updateBotWidgetQuery#b373fe68 flags:# query_id:long query_type:WidgetQueryType user_id:long peer:Peer
    msg_id:int chat_instance:long chat_type:string data:bytes widget_id:flags.0?long wallet_card:flags.1?wallet.Card"""
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0xB373FE68, 0x9F89304E

    @classmethod
    def from_reader(cls, r):
        flags = r.read_int()
        o = cls(query_id=r.read_long(), query_type=r.tgread_object(), user_id=r.read_long(),
                peer=r.tgread_object(), msg_id=r.read_int(), chat_instance=r.read_long(),
                chat_type=r.tgread_string(), data=r.tgread_bytes())
        o.widget_id = r.read_long() if flags & 1 else None
        o.wallet_card = r.tgread_object() if flags & 2 else None
        return o


class UpdateInlineBotWidgetQuery(_Parsed):
    """updateInlineBotWidgetQuery#a5f07e08 flags:# query_id:long query_type:WidgetQueryType user_id:long
    inline_message_id:InputBotInlineMessageID chat_instance:long chat_type:string data:bytes
    widget_id:flags.0?long wallet_card:flags.1?wallet.Card = Update"""
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0xA5F07E08, 0x9F89304E

    @classmethod
    def from_reader(cls, r):
        flags = r.read_int()
        o = cls(query_id=r.read_long(), query_type=r.tgread_object(), user_id=r.read_long(),
                inline_message_id=r.tgread_object(), chat_instance=r.read_long(),
                chat_type=r.tgread_string(), data=r.tgread_bytes())
        o.widget_id = r.read_long() if flags & 1 else None
        o.wallet_card = r.tgread_object() if flags & 2 else None
        return o


class UpdateMessageWidgetData(_Parsed):
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0xBBB078DD, 0x9F89304E

    @classmethod
    def from_reader(cls, r):
        flags = r.read_int()
        o = cls(peer=r.tgread_object(), msg_id=r.read_int())
        if flags & 1:
            o.public_data, o.public_data_hash = r.tgread_string(), r.read_long()
        o.chat_data = r.tgread_string() if flags & 2 else None
        o.pts, o.pts_count = r.read_int(), r.read_int()
        return o


class MessageMediaWidget(_Parsed):
    CONSTRUCTOR_ID, SUBCLASS_OF_ID = 0x2238F214, 0x476CBE32

    @classmethod
    def from_reader(cls, r):
        flags = r.read_int()
        o = cls(width=r.read_int(), height=r.read_int(), payload=r.tgread_bytes())
        if flags & 8:
            o.public_data, o.public_data_hash = r.tgread_string(), r.read_long()
        o.chat_data = r.tgread_string() if flags & 16 else None
        o.widget_id = r.read_long() if flags & 32 else None
        return o


class Channel233(types.Channel):
    """channel#7ad15240 (layer 233) = Telethon's channel (229) + flags2 bits 21, 23 and pinned_msg_id:flags2.22?int.
    A bot that is a channel admin gets it in every getDifference; without it the bot crashes on start."""
    CONSTRUCTOR_ID = 0x7AD15240

    @classmethod
    def from_reader(cls, reader):
        pos = reader.tell_position()
        reader.read_int()
        flags2 = reader.read_int()
        reader.set_position(pos)
        obj = types.Channel.from_reader(reader)
        if flags2 & (1 << 22):
            reader.read_int()  # pinned_msg_id
        return obj


class MessageReplyHeader233(types.MessageReplyHeader):
    """messageReplyHeader#ddb5ab75 (layer 233) = Telethon's (229) + quote_rich:flags.14?Vector<RichText>."""
    CONSTRUCTOR_ID = 0xDDB5AB75

    @classmethod
    def from_reader(cls, reader):
        pos = reader.tell_position()
        flags = reader.read_int()
        reader.set_position(pos)
        obj = types.MessageReplyHeader.from_reader(reader)
        if flags & (1 << 14):
            reader.read_int()  # vector constructor
            for _ in range(reader.read_int()):
                reader.tgread_object()
        return obj


for _cls in (WidgetQueryTypeData, UpdateBotWidgetQuery, UpdateInlineBotWidgetQuery, UpdateMessageWidgetData,
             MessageMediaWidget, Channel233, MessageReplyHeader233):
    alltlobjects.tlobjects[_cls.CONSTRUCTOR_ID] = _cls

# The server sends widget queries only to clients on layer 233. Telethon 1.45 is
# on 229; between them channel, channelFull, userFull and messageReplyHeader
# changed, which a bot in private chats rarely meets (a reply-to header may fail
# to parse and that one message is skipped).
import telethon.client.telegrambaseclient as _tbc  # noqa: E402
_tbc.LAYER = int(os.environ.get("TG_LAYER", "233"))
