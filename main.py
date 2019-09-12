import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError, Unauthorized
from enum import Enum
import logging
import hashlib
import os
import sticker_generation

with open("API_key.txt", "r") as f:
    API_KEY = f.read().rstrip()

def get_fname(display_name, message_body):
    return hashlib.md5((display_name + message_body).encode('utf-8')).hexdigest() + ".png"

def generate_forward(msg):
    if msg.forward_from.first_name is None:
        display_name = last_name
    elif msg.forward_from.last_name is None:
        display_name = msg.forward_from.first_name
    else:
        display_name = msg.forward_from.first_name + " " + msg.forward_from.last_name

    fname = get_fname(display_name, msg.text)

    if not os.path.exists(fname):
        sticker_generation.get_forward_image(display_name, msg.text).save(fname)

    return fname

class UserState(Enum):
    AWAITING_FORWARD = 1
    AWAITING_EMOJI = 2
    AWAITING_PACK = 3

def attempt_pop_from_forward_queue(bot, update, user_data):
    if "state" in user_data.keys() and user_data["state"] != UserState.AWAITING_FORWARD:
        return
    else:
        user_data["state"] = UserState.AWAITING_FORWARD

    if len( user_data.get("forward_queue", []) ) == 0:
        update.message.reply_text("Error: forward queue is empty")
    else:
        fname = user_data["forward_queue"][0]

        try:
            with open(fname, "rb") as f:
                bot.send_photo(chat_id=update.message.from_user.id, photo=f, caption="sticker preview")
                user_data["state"] = UserState.AWAITING_EMOJI
        except Unauthorized as e:
            return update.message.reply_text("Error sending DM! Message @{} to finish creating this forward".format(bot.username))

start_handler = attempt_pop_from_forward_queue

def forward_handler(bot, update, user_data):
    if "forward_queue" not in user_data.keys():
        user_data["forward_queue"] = []

    user_data["forward_queue"].append(generate_forward(update.message))

    attempt_pop_from_forward_queue(bot, update, user_data)

def message_handler(bot, update, user_data):
    if "state" not in user_data:
        return
    if not update.message.chat.id != update.from_user.id:
        return # not a DM, should be ignored

    if user_data["state"] == UserState.AWAITING_EMOJI:
        user_data["pending_emoji"] = update.message.text
        user_data["state"] = UserState.AWAITING_PACK

    elif user_data["state"] == UserState.AWAITING_PACK:
        fname = user_data["forward_queue"][0]

        pack_name = update.message.text
        pack_name += "_by_" + bot.username

        # TODO verify that pack exists, look up owner

        with open(fname, "rb") as f:
            bot.add_sticker_to_set(TODO_OWNER, pack_name, f, user_data["pending_emoji"])
            user_data["forward_queue"].pop(0)


def cancel_handler(bot, update, user_data):
    if user_data.get("forward_queue", [])
        user_data["forward_queue"].pop(0)

if __name__ == "__main__":
    updater = Updater(token=API_KEY)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_handler, pass_user_data=True))

    dispatcher.add_handler(MessageHandler(Filters.text & Filters.forwarded, forward_handler, pass_user_data=True))
    dispatcher.add_handler(MessageHandler(Filters.text & (~ Filters.forwarded) & (~ Filters.command), message_handler, pass_user_data=True))

    # allows viewing of exceptions
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO) # not sure exactly how this works

    updater.start_polling()
    updater.idle()
