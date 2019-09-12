import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError, Unauthorized
from enum import Enum
import logging
import hashlib
import os
import pickle
import sticker_generation

PACK_OWNER_FILE = "pack_owners.p"
STICKER_INFO_FILE = "sticker_info.p"

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

with open(PACK_OWNER_FILE, "rb") as f:
    sticker_set_owners = pickle.load(f)
with open(STICKER_INFO_FILE, "rb") as f:
    sticker_forwards = pickle.load(f) # TODO use to create sticker-to-forward system

def update_pickles():
    with open(PACK_OWNER_FILE, "wb") as f:
        pickle.dump(sticker_set_owners, f)
    with open(STICKER_INFO_FILE, "wb") as f:
        pickle.dump(sticker_forwards, f)

class UserState(Enum):
    AWAITING_FORWARD = 1
    AWAITING_EMOJI = 2
    AWAITING_PACK = 3

def attempt_pop_from_forward_queue(bot, update, user_data):
    if "state" in user_data.keys() and user_data["state"] != UserState.AWAITING_FORWARD:
        return
    else:
        user_data["state"] = UserState.AWAITING_FORWARD

    if len( user_data.get("forward_queue", []) ) > 0:
        fname = user_data["forward_queue"][0]

        try:
            with open(fname, "rb") as f:
                bot.send_photo(chat_id=update.message.from_user.id, photo=f, caption="sticker preview")
                user_data["state"] = UserState.AWAITING_EMOJI
                bot.send_message(chat_id=update.message.from_user.id, text="Send the emoji you want for this sticker, or /cancel to quit at any time")
        except Unauthorized as e:
            return update.message.reply_text("Error sending DM! Message @{} to finish creating this forward".format(bot.username))

start_handler = attempt_pop_from_forward_queue

def forward_handler(bot, update, user_data):
    if "forward_queue" not in user_data.keys():
        user_data["forward_queue"] = []

    user_data["forward_queue"].append(generate_forward(update.message))

    attempt_pop_from_forward_queue(bot, update, user_data)

# helper
def done_with_forward(user_data):
    queue = user_data.get("forward_queue", [])
    if len(queue) > 0:
        fname = queue.pop(0)
        os.remove(fname)

        user_data["state"] = UserState.AWAITING_FORWARD

def message_handler(bot, update, user_data):
    if "state" not in user_data:
        return

    if user_data["state"] == UserState.AWAITING_EMOJI:
        user_data["pending_emoji"] = update.message.text
        user_data["state"] = UserState.AWAITING_PACK
        bot.send_message(chat_id=update.message.from_user.id,
            text="Send the name of the pack you want to add this forward to, " + \
            "or \"/newpack [pack name] [pack title]\" to make a new pack")

    elif user_data["state"] == UserState.AWAITING_PACK:
        pack_name = update.message.text

        fname = user_data["forward_queue"][0]

        if pack_name not in sticker_set_owners.keys():
            bot.send_message(chat_id=update.message.from_user.id,
                text="Error: no pack found with given name."
            return

        pack_owner = sticker_set_owners[pack_name]
        pack_name += "_by_" + bot.username

        with open(fname, "rb") as f:
            bot.add_sticker_to_set(pack_owner, pack_name, f, user_data["pending_emoji"])

        done_with_forward(user_data)

        bot.send_message(chat_id=update.message.from_user.id,
            text="Successfully created sticker! " + \
            "It may take some time to appear in [the pack](https://t.me/addstickers/{})".format(pack_name),
            parse_mode=telegram.ParseMode.MARKDOWN)

        attempt_pop_from_forward_queue(bot, update, user_data)


def cancel_handler(bot, update, user_data):
    done_with_forward(user_data)
    bot.send_message(chat_id=update.message.from_user.id, text="Cancelled current operation without creating a sticker")
    attempt_pop_from_forward_queue(bot, update, user_data)

def newpack_handler(bot, update, user_data, args):
    if "state" not in user_data or user_data["state"] != UserState.AWAITING_PACK:
        update.message.reply_text(text="Invalid state! First, forward a message to start a new pack with")
        return

    if len(args) < 2:
        update.message.reply_text(text="At least 2 args required!")
        return

    pack_name = args[0]
    pack_title = " ".join(args[1:])

    if pack_name in pack_owners.keys():
        update.message.reply_text(text="Pack with that name already exists!")
        return

    from_user_id = update.message.from_user.id
    fname = user_data["forward_queue"][0]

    with open(fname, "r") as f:
        bot.create_new_sticker_set(from_user_id,
            pack_name + "_by_" + bot.username,
            pack_title, f, user_data["pending_emoji"] )

    pack_owners[pack_name] = from_user_id

    done_with_forward(user_data)

    bot.send_message(chat_id=update.message.from_user.id,
        text="Successfully created new pack with sticker! " + \
        "It may take some time to appear in [the pack](https://t.me/addstickers/{})".format(pack_name),
        parse_mode=telegram.ParseMode.MARKDOWN)

    attempt_pop_from_forward_queue(bot, update, user_data)



def pack_list_handler(bot, update):
    packs = [ bot.get_sticker_set(name) for name in sticker_set_owners.keys() ]
    packs.sort(key=lambda pack: pack.title)

    msg = "\n".join( "[{}](https://t.me/addstickers/{})".format(pack.title, pack.name) for pack in packs )
    bot.update.message.reply_text(text=msg)

if __name__ == "__main__":
    updater = Updater(token=API_KEY)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_handler, pass_user_data=True))
    dispatcher.add_handler(CommandHandler("newpack", newpack_handler, pass_user_data=True, pass_args=True))
    dispatcher.add_handler(CommandHandler("listpacks", pack_list_handler))

    dispatcher.add_handler(MessageHandler(Filters.text & Filters.forwarded, forward_handler, pass_user_data=True))
    dispatcher.add_handler(MessageHandler(Filters.text & (~ Filters.forwarded) & (~ Filters.command), message_handler, pass_user_data=True))

    # allows viewing of exceptions
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO) # not sure exactly how this works

    updater.start_polling()
    updater.idle()
