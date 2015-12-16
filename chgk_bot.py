#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This Bot uses the Updater class to handle the bot.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and the CLI-Loop is entered, where all text inputs are
inserted into the update queue for the bot to handle.

Usage:
Basic Echobot example, repeats messages. Reply to last chat from the command
line by typing "/reply <text>"
Type 'stop' on the command line to stop the bot.
"""

from telegram import Updater
from telegram.dispatcher import run_async
from time import sleep
import logging
import sys
import urllib2
from lxml import etree

root = logging.getLogger()
root.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = \
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

last_chat_id = 0

logger = logging.getLogger(__name__)


# Command Handlers
def start(bot, update):
    """ Answer in Telegram """
    bot.sendMessage(update.message.chat_id, text='Hi!')


def help(bot, update):
    """ Answer in Telegram """
    bot.sendMessage(update.message.chat_id, text='Help!')


def recent(bot, update):
    """
    Выдача списка недавно добавленных турниров по команде /recent
    """
    recent_url = urllib2.urlopen("http://db.chgk.info/last/feed")
    recent_data = recent_url.read()
    recent_url.close()
    recent_xml = etree.fromstring(recent_data)
    recent_tournaments = []
    for item in recent_xml[0]:
        if item.tag == 'item':
            tournament = dict()
            for child in item:
                tournament[child.tag] = child.text
            recent_tournaments.append(tournament)
    text = ''
    for index, tournament in enumerate(recent_tournaments[:10]):
        text += str(index+1) + '. ' +tournament['title'] + '\n'
    bot.sendMessage(update.message.chat_id, text=text)


def any_message(bot, update):
    """ Print to console """

    # Save last chat_id to use in reply handler
    global last_chat_id
    last_chat_id = update.message.chat_id

    logger.info("New message\nFrom: %s\nchat_id: %d\nText: %s" %
                (update.message.from_user,
                 update.message.chat_id,
                 update.message.text))


def unknown_command(bot, update):
    """ Answer in Telegram """
    bot.sendMessage(update.message.chat_id, text='Command not recognized!')


@run_async
def play(bot, update):
    bot.sendMessage(update.message.chat_id, text='Вопрос 1')
    logger.info("posted")
    sleep(50)
    bot.sendMessage(update.message.chat_id, text ='10 секунд')
    logger.info("posted")
    sleep(10)
    bot.sendMessage(update.message.chat_id, text='Время')
    for i in range(10, -1, -1):
        sleep(1)
        bot.sendMessage(update.message.chat_id, text=str(i))

@run_async
def message(bot, update):
    """
    Example for an asynchronous handler. It's not guaranteed that replies will
    be in order when using @run_async.
    """
    pass


def error(bot, update, error):
    """ Print error to console """
    logger.warn('Update %s caused error %s' % (update, error))


def cli_reply(bot, update, args):
    """
    For any update of type telegram.Update or str, you can get the argument
    list by appending args to the function parameters.
    Here, we reply to the last active chat with the text after the command.
    """
    if last_chat_id is not 0:
        bot.sendMessage(chat_id=last_chat_id, text=' '.join(args))


def cli_noncommand(bot, update, update_queue):
    """
    You can also get the update queue as an argument in any handler by
    appending it to the argument list. Be careful with this though.
    Here, we put the input string back into the queue, but as a command.
    """
    update_queue.put('/%s' % update)


def unknown_cli_command(bot, update):
    logger.warn("Command not found: %s" % update)


def main():
    # Create the EventHandler and pass it your bot's token.
    # token = '170527211:AAHjwfp0qhPTLwhZzvz0ckmtII-Fv94sBFw'
    token = '172154397:AAEeEbxveuvlfHL7A-zLBfV2HRrZkJTcsSc'
    updater = Updater(token, workers=2)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", help)
    dp.addTelegramCommandHandler("recent", recent)
    dp.addTelegramCommandHandler("play", play)
    dp.addUnknownTelegramCommandHandler(unknown_command)
    dp.addTelegramMessageHandler(message)
    dp.addTelegramRegexHandler('.*', any_message)

    dp.addStringCommandHandler('reply', cli_reply)
    dp.addUnknownStringCommandHandler(unknown_cli_command)
    dp.addStringRegexHandler('[^/].*', cli_noncommand)

    dp.addErrorHandler(error)

    # Start the Bot and store the update Queue, so we can insert updates
    update_queue = updater.start_polling(poll_interval=0.1, timeout=20)

    # Start CLI-Loop
    while True:
        try:
            text = raw_input()
        except NameError:
            text = input()

        # Gracefully stop the event handler
        if text == 'stop':
            updater.stop()
            break

        # else, put the text into the update queue
        elif len(text) > 0:
            update_queue.put(text)  # Put command into queue

if __name__ == '__main__':
    main()
