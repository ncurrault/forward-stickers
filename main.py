import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError, Unauthorized
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

def attempt_pop_from_forward_queue(bot, update, user_data):
    if len( user_data.get("forward_queue", []) ) == 0:
        update.message.reply_text("Error: forward queue is empty")
    else:
        fname = user_data["forward_queue"][0]

        try:
            bot.send_message(chat_id=update.message.from_user.id, supress_errors=False)
            with open(fname, "rb") as f:
                bot.send_message(chat_id=update.message.from_user.id, photo=f, text="Sticker preview")
        except Unauthorized as e:
            return update.message.reply_text("Error sending DM! Message @{} to finish creating this forward".format(bot.username))

start_handler = attempt_pop_from_forward_queue

def forward_handler(bot, update, user_data):
    if "forward_queue" not in user_data.keys():
        user_data["forward_queue"] = []

    user_data["forward_queue"].append(generate_forward(update.message))

    attempt_pop_from_forward_queue(bot, update, user_data)

def message_handler(bot, update, user_data):
    pass

if __name__ == "__main__":
    updater = Updater(token=API_KEY)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_handler, pass_user_data=True))

    dispatcher.add_handler(MessageHandler(Filters.text & Filters.forwarded, forward_handler, pass_user_data=True))
    dispatcher.add_handler(MessageHandler(Filters.text & (~ Filters.forwarded), message_handler, pass_user_data=True))

    # allows viewing of exceptions
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO) # not sure exactly how this works

    updater.start_polling()
    updater.idle()
