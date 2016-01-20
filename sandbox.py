# from xml_tools import recent_tournaments, q_and_a
# from bot_tools import Question
#
# for key, value in q_and_a('har14-h2', 2, 2).items():
#     print key, value

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to send timed Telegram messages
# This program is dedicated to the public domain under the CC0 license.

"""
This Bot uses the Updater class to handle the bot and the JobQueue to send
timed messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Alarm Bot example, sends a message after a set time.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram import Updater
import logging

# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)
job_queue = None
indexer = 0



# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi! Use /set <seconds> to '
                                                 'set a timer')


def set(bot, update, args):
    """ Adds a job to the queue """
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(args[0])
        if due < 0:
                bot.sendMessage(chat_id,text='Sorry we can not go back to future!')

        global indexer
        indexer += 1
        job_number = indexer

        def alarm(bot):
            """ Inner function to send the alarm message """
            if job_number != indexer:
                return
            interval = due
            bot.sendMessage(chat_id, text='Beep! {} seconds have passed'.format(interval))

        # Add job to queue
        job_queue.put(alarm, due, repeat=False)
        bot.sendMessage(chat_id, text='Timer successfully set!')

    except IndexError:
        bot.sendMessage(chat_id, text='Usage: /set <seconds>')
    except ValueError:
        bot.sendMessage(chat_id, text='Usage: /set <seconds>')


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    global job_queue, indexer

    indexer = 0

    updater = Updater('172047371:AAFv5NeZ1Bx9ea-bt2yJeK8ajZpgHPgkLBk')
    job_queue = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", start)
    dp.addTelegramCommandHandler("set", set)

    # log all errors
    dp.addErrorHandler(error)

    # Start the Bot
    updater.start_polling()

    # Block until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()