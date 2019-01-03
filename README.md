# forward-stickers
Instantly convert forwarded Telegram messages to ~~512px-wide images suitable for~~ stickers

## Note on obfuscation
This project hides details that cannot be released publicly in two files (each hidden with `.gitignore`):

* `API_key.txt`, which only contains the bot's API key (obtained with @BotFather)
* `sticker_set_info.txt`, which contains two lines: the target sticker set's owner's user\_id (not their username, a large integer that the Telegram API assigns) and the sticker set's name (from the `t.me/addstickers/*` URL)
