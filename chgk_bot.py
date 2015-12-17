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
from xml_tools import tournament_info, q_and_a

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

# dict of dicts with information for every chatting user
state = dict()


# Command Handlers
def start(bot, update):
    """ Answer in Telegram """
    bot.sendMessage(update.message.chat_id, text='Hi!')
    state[update.message.chat_id] = dict()


def help(bot, update):
    """ Answer in Telegram """
    bot.sendMessage(update.message.chat_id, text='Help!')


def status(bot, update):
    """
    see full 'state' information for given chat
    """
    logger.info(str(state[update.message.chat_id]['tournament']))


def recent(bot, update):
    """
    Выдача списка недавно добавленных турниров по команде /recent
    """
    chat_id = update.message.chat_id
    recent_url = urllib2.urlopen("http://db.chgk.info/last/feed")
    recent_data = recent_url.read()
    recent_url.close()
    recent_xml = etree.fromstring(recent_data)
    if chat_id not in state.keys():
        state[chat_id] = dict()
    state[chat_id]['tournaments'] = []
    for item in recent_xml[0]:
        if item.tag == 'item':
            tournament = dict()
            for child in item:
                tournament[child.tag] = child.text
            state[chat_id]['tournaments'].append(tournament)
    # default tournament is the most recently added tournament
    state[chat_id]['tournament_id'] = state[chat_id]['tournaments'][0]['link']

    text = ''
    for index, tournament in enumerate(state[chat_id]['tournaments'][:10]):
        text += str(index+1) + '. ' + tournament['title'] + '\n'
    bot.sendMessage(chat_id, text=text)


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


def play(bot, update):
    chat_id = update.message.chat_id
    if chat_id not in state or 'tournaments' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Нет списка турниров. Сделайте /recent')
        return 0
    parameter = update.message.text.strip(' /play')
    try:
        if int(parameter) in range(1, 11):
            state[chat_id]['tournament_id'] = state[chat_id]['tournaments'][int(parameter) - 1]['link']
    except:
        pass
    current = tournament_info(state[chat_id]['tournament_id'])
    state[chat_id]['tour'] = 1
    state[chat_id]['question'] = 1
    state[chat_id].update(current)
    bot.sendMessage(chat_id, text=state[chat_id]['description'])
    bot.sendMessage(chat_id, text='/ask - задать первый вопрос')


@run_async
def ask(bot, update):
    chat_id = update.message.chat_id
    if chat_id not in state or 'tournaments' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Нет списка турниров. Сделайте /recent и /play')
        return 0

    if 'tour' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Не выбран турнир. Сделайте /play')
        return 0

    question = q_and_a(state[chat_id]['tournament_id'], state[chat_id]['tour'], state[chat_id]['question'])
    if state[chat_id]['question'] == 0:
        bot.sendMessage(chat_id, text='Турнир закончен. Выберите новый турнир')
        return 0

    if state[chat_id]['question'] == 1:
        bot.sendMessage(chat_id, text=state[chat_id]['tour_titles'][state[chat_id]['tour'] - 1])
        if state[chat_id]['tour_editors'][state[chat_id]['tour'] - 1]:
            bot.sendMessage(chat_id, text=state[chat_id]['tour_editors'][state[chat_id]['tour'] - 1])
        if state[chat_id]['tour_info'][state[chat_id]['tour'] - 1]:
            bot.sendMessage(chat_id, text=state[chat_id]['tour_info'][state[chat_id]['tour'] - 1])
    bot.sendMessage(chat_id, text='Вопрос ' + str(state[chat_id]['question']))
    sleep(1)
    # Если есть картинка, отправим ее
    if 'q_image' in question:
        bot.sendMessage(chat_id, text=question['q_image'])
    bot.sendMessage(chat_id, text=question['question'])
    if state[chat_id]['question'] < state[chat_id]['n_questions'][state[chat_id]['tour'] - 1]:
        state[chat_id]['question'] += 1
    elif state[chat_id]['tour'] < state[chat_id]['n_tours']:
        state[chat_id]['tour'] += 1
        state[chat_id]['question'] = 1
    else:
        state[chat_id]['tour'] = 0
        state[chat_id]['question'] = 0
    print state[chat_id]['tour'], state[chat_id]['question']
    sleep(10)
    bot.sendMessage(chat_id, text='Время пошло!')
    sleep(50)
    bot.sendMessage(chat_id, text='10 секунд')
    logger.info("posted")
    sleep(10)
    bot.sendMessage(chat_id, text='Время!')
    for i in range(10, -1, -1):
        bot.sendMessage(chat_id, text=str(i))
        sleep(1)
    bot.sendMessage(chat_id, text=u'Ответ: ' + question['answer'])
    sleep(5)
    if question['comments']:
        bot.sendMessage(chat_id, text=u'Комментарий: ' + question['comments'])
    sleep(2)
    bot.sendMessage(chat_id, text=u'Источники: ' + question['sources'])
    sleep(2)
    bot.sendMessage(chat_id, text=u'Авторы: ' + question['authors'])
    if state[chat_id]['question'] == 1:
        bot.sendMessage(chat_id, text=u'Конец тура.')
    elif state[chat_id]['question'] == 0:
        bot.sendMessage(chat_id, text=u'Конец турнира.')
    else:
        bot.sendMessage(chat_id, text=u'Следующий вопрос - /ask')


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
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", help)
    dp.addTelegramCommandHandler("recent", recent)
    dp.addTelegramCommandHandler("play", play)
    dp.addTelegramCommandHandler("ask", ask)
    dp.addTelegramCommandHandler("status", status)
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
