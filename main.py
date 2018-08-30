import telegram
from telegram.ext import Updater, MessageHandler, Filters
from telegram.error import TelegramError
import logging
from PIL import Image, ImageDraw, ImageFont, ImageChops
import copy
import hashlib

BACKGROUND = (36, 46, 61)
TEXT_COLOR = (255, 255, 255)
MARGIN_PX = 15

header_fnt = ImageFont.truetype('~/Library/Fonts/OpenSans-Regular.ttf', 27)
from_fnt = ImageFont.truetype('~/Library/Fonts/OpenSans-SemiBold.ttf', 26)
content_fnt = ImageFont.truetype('~/Library/Fonts/OpenSans-Regular.ttf', 44)

def are_same_image(im1, im2):
    if None in (im1, im2):
        return False
    else:
        return ImageChops.difference(im1, im2).getbbox() is None
def line_overflows(line, image_width, font):
    current_line = Image.new('RGB', (image_width, 100), color = (255, 255, 255))
    additional_dot = copy.deepcopy(current_line)
    ImageDraw.Draw(current_line).text((0,0), line, font=font, fill=(0,0,0))
    ImageDraw.Draw(additional_dot).text((0,0), line+".", font=font, fill=(0,0,0))

    return are_same_image(current_line, additional_dot)
def wrap_text(text, image_width, font):
    if text == "":
        return ""
    elif text.find("\n") != -1:
        return "\n".join([ wrap_text(block, image_width, font) for block in text.split("\n")])

    words = text.split()
    ret = ""
    blank_img = Image.new('RGB', (image_width, 100), color = (255, 255, 255))
    # TODO we really only need an image as tall as the fon't tallest character

    line = ""
    while len(words) > 0:
        next_word = words.pop(0)

        if line_overflows(line + next_word, image_width, font):
            ret += line + "\n"
            line = next_word + " "
        else:
            line += next_word + " "

    return ret + line

def get_forward_image(from_name, content):
    wrapped_content = wrap_text(content, 512 - (2 * MARGIN_PX), content_fnt)

    img = Image.new('RGB', (512, 512), color = BACKGROUND)
    d = ImageDraw.Draw(img)
    d.text((15,9), "Forwarded Message\nFrom: ", font=header_fnt, fill=TEXT_COLOR)
    d.text((93,43), from_name, font=from_fnt, fill=TEXT_COLOR)
    d.text((15,85), wrapped_content, font=content_fnt, fill=TEXT_COLOR)

    bottommost_text = None
    for y in range(511, -1, -1):
        for x in range(512):
            if img.getpixel((x, y)) != BACKGROUND:
                bottommost_text = y
                break
        if bottommost_text:
            break

    if bottommost_text:
        return img.crop((0, 0, 512, bottommost_text + MARGIN_PX))
    else:
        return img


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
    # TODO check if file exists

    get_forward_image(display_name, msg.text).save(fname)

    with open(fname, "rb") as f:
        bot.send_document(chat_id=msg.chat.id, document=f)
        #bot.send_photo(chat_id=update.message.chat.id, photo=f)

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
