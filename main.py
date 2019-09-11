import telegram
from telegram.ext import Updater, MessageHandler, Filters
from telegram.error import TelegramError
import logging
import hashlib
import os
import sticker_generation

with open("sticker_set_info.txt","r") as f:
    PACK_OWNER, PACK_NAME = f.read().splitlines()
with open("API_key.txt", "r") as f:
    API_KEY = f.read().rstrip()

def message_handler(bot, update):
    msg = update.message

    if msg.forward_from.first_name is None:
        display_name = last_name
    elif msg.forward_from.last_name is None:
        display_name = msg.forward_from.first_name
    else:
        display_name = msg.forward_from.first_name + " " + msg.forward_from.last_name

    fname = hashlib.md5((display_name + msg.text).encode('utf-8')).hexdigest() + ".png"

    # TODO better way to check for duplicates

    if os.path.exists(fname):
        bot.send_message(chat_id=update.message.chat.id,
            text="Error: sticker already in pack")
    else:
        sticker_generation.get_forward_image(display_name, msg.text).save(fname)

        with open(fname, "rb") as f:
            bot.add_sticker_to_set(PACK_OWNER, PACK_NAME, f, "🅱️")
            bot.send_message(chat_id=update.message.chat.id,
                text="Successfully created sticker! It may take a while to appear " + \
                "in [the pack](https://t.me/addstickers/{}), but here's a preview:".format(PACK_NAME),
                #"(which you can save as PNG to add to another pack):"
                parse_mode=telegram.ParseMode.MARKDOWN)
            f.seek(0)
            bot.send_photo(chat_id=update.message.chat.id, photo=f)
            os.remove(fname)


if __name__ == "__main__":
    updater = Updater(token=API_KEY)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(MessageHandler(Filters.text & Filters.forwarded, message_handler))

    # allows viewing of exceptions
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO) # not sure exactly how this works

    updater.start_polling()
    updater.idle()
