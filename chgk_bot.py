#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
chgk_bot for telegram

uses python-telegram-bot library

/recent - list of 10 most recently uploaded to db.chgk.info tournaments
/play [number] - play one of the tournaments. By default - most recent.
/ask - ask next question
/next_tour - skip remaining questions of current tour, ask first question from
the next.
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
    """ Greetings when start bot """
    bot.sendMessage(update.message.chat_id, text=u'Вращайте волчок')
    state[update.message.chat_id] = dict()


def help(bot, update):
    """ help command """
    text = u"/recent - список последних десяти загруженных в базу пакетов\n" \
           u"/play [номер пакета] - играть пакет из списка с переданным номером. Если номер не передан - самый " \
           u"последний загруженный пакет.\n" \
           u"/ask - задать очередной вопрос."
    bot.sendMessage(update.message.chat_id, text=text)


def status(bot, update):
    """
    writes to terminal full 'state' information for given chat
    """
    logger.info(str(state[update.message.chat_id]['tournament']))


def recent(bot, update):
    """
    /recent - print out list of ten most recently added tournaments
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
    state[chat_id]['last_shown'] = 10
    bot.sendMessage(chat_id, text=text)


def more(bot, update):
    """
    show more tournaments from loaded
    """
    chat_id = update.message.chat_id
    if 'tournaments' not in state[chat_id] or 'last_shown' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Нет скачанных турниров')
        return 0
    last = state[chat_id]['last_shown']
    end = min(last+10, len(state[chat_id]['tournaments']))
    if last == end:
        bot.sendMessage(chat_id, text='Больше нет')
    text = ''
    for i in range(last, end):
        text += str(i+1) + '. ' + state[chat_id]['tournaments'][i]['title'] + '\n'
    state[chat_id]['last_shown'] = end
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
    """ /play tournament """
    chat_id = update.message.chat_id
    if chat_id not in state or 'tournaments' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Нет списка турниров. Сделайте /recent')
        return 0
    parameter = update.message.text.strip(' /play')
    try:
        if int(parameter) in range(1, len(state[chat_id]['tournaments'])):
            state[chat_id]['tournament_id'] = state[chat_id]['tournaments'][int(parameter) - 1]['link']
    except:
        pass
    current = tournament_info(state[chat_id]['tournament_id'])
    state[chat_id]['tour'] = 1
    state[chat_id]['question'] = 1
    state[chat_id].update(current)
    bot.sendMessage(chat_id, text=state[chat_id]['description'])
    bot.sendMessage(chat_id, text='/ask - задать первый вопрос')


def next_tour(bot, update):
    """
    /next_tour - play next tour
    """
    chat_id = update.message.chat_id
    state[chat_id]['break'] = True
    state[chat_id]['tour'] += 1
    state[chat_id]['question'] = 1
    ask(bot, update)


@run_async
def ask(bot, update):
    """ /ask current question, wait 50 secs, warn that 10 secs are left,
    wait 10 secs, tell that time is up, wait 10 secs, print answer and
    additional info, get ready to ask next question.
    """
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
    # for i in range(10, -1, -1):
    #     bot.sendMessage(chat_id, text=str(i))
    #     sleep(1)
    sleep(10)
    bot.sendMessage(chat_id, text=u'Ответ: ' + question['answer'])
    sleep(2)
    if 'comments' in question:
        bot.sendMessage(chat_id, text=u'Комментарий: ' + question['comments'])
    sleep(2)
    bot.sendMessage(chat_id, text=u'Источники: ' + question['sources'])
    sleep(2)
    bot.sendMessage(chat_id, text=u'Авторы: ' + question['authors'])
    if state[chat_id]['question'] == 1:
        bot.sendMessage(chat_id, text=u'Конец тура. Первый вопрос следующего тура - /ask')
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
    token = '172154397:AAEeEbxveuvlfHL7A-zLBfV2HRrZkJTcsSc'
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", help)
    dp.addTelegramCommandHandler("recent", recent)
    dp.addTelegramCommandHandler("more", more)
    dp.addTelegramCommandHandler("play", play)
    dp.addTelegramCommandHandler("ask", ask)
    dp.addTelegramCommandHandler("next_tour", next_tour)
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
