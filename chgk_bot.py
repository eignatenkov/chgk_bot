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
from time import sleep
import logging
from telegram import Updater
from telegram.dispatcher import run_async
from xml_tools import tournament_info, q_and_a, recent_tournaments

root = logging.getLogger()
root.setLevel(logging.INFO)


ch = logging.FileHandler("chgk_bot.log")
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

def status(bot, update):
    """
    writes to terminal full 'state' information for given chat
    """
    for key, value in state[update.message.chat_id].items():
        if key != 'tournaments':
            print(key, ': ',)
            try:
                value.encode('utf-8')
            except:
                print(str(value))


def recent(bot, update):
    """
    /recent - print out list of ten most recently added tournaments
    """
    chat_id = update.message.chat_id
    if chat_id not in state.keys():
        bot.sendMessage(chat_id, text='/start the bot')
        return
    state[chat_id]['tournaments'] = recent_tournaments()
    if len(state[chat_id]['tournaments']) == 0:
        bot.sendMessage(chat_id, text='сайт db.chgk.info не возвращает список '
                                      'турниров. Попробуйте позже')
        state[chat_id].pop('tournaments')
        return
    # default tournament is the most recently added tournament
    if 'tournament_id' not in state[chat_id] or \
                    state[chat_id].get('question_number', 0) == 0:
        state[chat_id]['tournament_id'] = \
            state[chat_id]['tournaments'][0]['link']

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
    if 'tournaments' not in state[chat_id] or \
                    'last_shown' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Нет скачанных турниров')
        return 0
    last = state[chat_id]['last_shown']
    end = min(last+10, len(state[chat_id]['tournaments']))
    if last == end:
        bot.sendMessage(chat_id, text='Больше нет')
    text = ''
    for i in range(last, end):
        text += str(i+1) + '. ' + \
                state[chat_id]['tournaments'][i]['title'] + '\n'
    state[chat_id]['last_shown'] = end
    bot.sendMessage(chat_id, text=text)


def play(bot, update):
    """ /play tournament """
    chat_id = update.message.chat_id
    if chat_id not in state or 'tournaments' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Нет списка турниров. Сделайте /recent')
        return
    parameter = update.message.text.strip(' /play')
    if parameter != '':
        try:
            if 0 < int(parameter) < len(state[chat_id]['tournaments']) + 1:
                state[chat_id]['tournament_id'] = \
                    state[chat_id]['tournaments'][int(parameter) - 1]['link']
            else:
                bot.sendMessage(chat_id,
                                text='Турнира с таким номером нет среди '
                                     'загруженных. Играем первый турнир')
                state[chat_id]['tournament_id'] = \
                    state[chat_id]['tournaments'][0]['link']
        except:
            bot.sendMessage(chat_id, text='Параметр не распознан, '
                                          'играем первый турнир')
            state[chat_id]['tournament_id'] = \
                state[chat_id]['tournaments'][0]['link']
    current = tournament_info(state[chat_id]['tournament_id'])
    if current == '':
        bot.sendMessage(chat_id, text='Ошибка при загрузке турнира. '
                                      'Выберите другой турнир')
        return
    state[chat_id]['tour'] = 1
    state[chat_id]['question_number'] = 1
    state[chat_id].update(current)
    bot.sendMessage(chat_id, text=state[chat_id]['description'])
    bot.sendMessage(chat_id, text='/ask - задать первый вопрос')


def next_tour(bot, update):
    """
    /next_tour - play next tour
    """
    chat_id = update.message.chat_id
    if state[chat_id]['tour'] == state[chat_id]['n_tours']:
        bot.sendMessage(chat_id, text='Это последний тур турнира')
        return
    if state[chat_id]['playing']:
        state[chat_id]['break'] = True
        while state[chat_id]['playing']:
            sleep(.5)
    state[chat_id]['tour'] += 1
    state[chat_id]['question_number'] = 1
    ask(bot, update)


def wait(chat_id, time):
    while not state[chat_id]['break'] and time >= 0:
        sleep(1)
        time -= 1


@run_async
def ask(bot, update, **kwargs):
    """ /ask current question, wait 50 secs, warn that 10 secs are left,
    wait 10 secs, tell that time is up, wait 10 secs, print answer and
    additional info, get ready to ask next question.
    """
    chat_id = update.message.chat_id
    if chat_id not in state or 'tournaments' not in state[chat_id]:
        bot.sendMessage(chat_id,
                        'Нет списка турниров. Сделайте /recent и /play')
        return 0

    if 'tour' not in state[chat_id]:
        bot.sendMessage(chat_id, text='Не выбран турнир. Сделайте /play')
        return 0

    if state[chat_id]['question_number'] == 0:
        bot.sendMessage(chat_id, text='Турнир закончен. Выберите новый турнир')
        return 0

    if state[chat_id]['question_number'] == 1:
        bot.sendMessage(chat_id,
                        state[chat_id]['tour_titles'][state[chat_id]['tour'] - 1])
        if state[chat_id]['tour_editors'][state[chat_id]['tour'] - 1]:
            bot.sendMessage(chat_id,
                            state[chat_id]['tour_editors'][state[chat_id]['tour'] - 1])
        if state[chat_id]['tour_info'][state[chat_id]['tour'] - 1]:
            bot.sendMessage(chat_id,
                            state[chat_id]['tour_info'][state[chat_id]['tour'] - 1])

    state[chat_id]['question'] = q_and_a(state[chat_id]['tournament_id'],
                                         state[chat_id]['tour'],
                                         state[chat_id]['question_number'])
    if state[chat_id]['playing']:
        state[chat_id]['break'] = True
        while state[chat_id]['playing']:
            sleep(0.5)
    state[chat_id]['playing'] = True
    logger.info('current question: %d % d' %
                (state[chat_id]['tour'], state[chat_id]['question_number']))
    bot.sendMessage(chat_id, text='Вопрос ' +
                    str(state[chat_id]['question_number']))
    sleep(1)
    # Если есть картинка, отправим ее
    if 'question_image' in state[chat_id]['question']:
        bot.sendMessage(chat_id,
                        text=state[chat_id]['question']['question_image'])
    bot.sendMessage(chat_id, text=state[chat_id]['question']['question'])
    if state[chat_id]['question_number'] < \
            state[chat_id]['n_questions'][state[chat_id]['tour'] - 1]:
        state[chat_id]['question_number'] += 1
    elif state[chat_id]['tour'] < state[chat_id]['n_tours']:
        state[chat_id]['tour'] += 1
        state[chat_id]['question_number'] = 1
    else:
        state[chat_id]['tour'] = 0
        state[chat_id]['question_number'] = 0
    logger.info('next question: %d % d' % (state[chat_id]['tour'],
                                           state[chat_id]['question_number']))
    wait(chat_id, 10)
    if state[chat_id]['break']:
        state[chat_id]['playing'] = False
        state[chat_id]['break'] = False
        return
    bot.sendMessage(chat_id, text='Время пошло!')
    wait(chat_id, 50)
    if state[chat_id]['break']:
        state[chat_id]['playing'] = False
        state[chat_id]['break'] = False
        return
    bot.sendMessage(chat_id, text='10 секунд')
    wait(chat_id, 10)
    if state[chat_id]['break']:
        state[chat_id]['playing'] = False
        state[chat_id]['break'] = False
        return
    bot.sendMessage(chat_id, text='Время!')
    wait(chat_id, 10)
    if state[chat_id]['break']:
        state[chat_id]['playing'] = False
        state[chat_id]['break'] = False
        return
    bot.sendMessage(chat_id,
                    text=u'Ответ: ' + state[chat_id]['question']['answer'])
    sleep(2)
    if 'pass_criteria' in state[chat_id]['question']:
        bot.sendMessage(chat_id,
                        u'Зачет: ' +
                        state[chat_id]['question']['pass_criteria'])
    if 'comments' in state[chat_id]['question']:
        bot.sendMessage(chat_id, text=u'Комментарий: ' +
                        state[chat_id]['question']['comments'])
    sleep(2)
    bot.sendMessage(chat_id, text=u'Источники: ' +
                    state[chat_id]['question']['sources'])
    sleep(2)
    bot.sendMessage(chat_id, text=u'Авторы: ' +
                    state[chat_id]['question']['authors'])
    if state[chat_id]['question_number'] == 1:
        bot.sendMessage(chat_id, text=u'Конец тура. '
                                      u'Первый вопрос следующего тура - /ask')
    elif state[chat_id]['question_number'] == 0:
        bot.sendMessage(chat_id, text=u'Конец турнира.')
    else:
        bot.sendMessage(chat_id, text=u'Следующий вопрос - /ask')

    state[chat_id]['playing'] = False


def answer(bot, update):
    """
    Досрочный ответ
    :return: постит ответ не дожидаясь конца отсчета времени
    """
    chat_id = update.message.chat_id
    if state[chat_id]['playing']:
        state[chat_id]['break'] = True
        while state[chat_id]['playing']:
            sleep(.5)
        bot.sendMessage(chat_id, text=u'Ответ: ' +
                        state[chat_id]['question']['answer'])
        if 'comments' in state[chat_id]['question']:
            bot.sendMessage(chat_id,
                            text=u'Комментарий: ' +
                            state[chat_id]['question']['comments'])
        bot.sendMessage(chat_id, text=u'Источники: ' +
                        state[chat_id]['question']['sources'])
        bot.sendMessage(chat_id, text=u'Авторы: ' +
                        state[chat_id]['question']['authors'])
        if state[chat_id]['question_number'] == 1:
            bot.sendMessage(chat_id, text=u'Конец тура. Первый вопрос '
                                          u'следующего тура - /ask')
        elif state[chat_id]['question_number'] == 0:
            bot.sendMessage(chat_id, text=u'Конец турнира.')
        else:
            bot.sendMessage(chat_id, text=u'Следующий вопрос - /ask')
    else:
        bot.sendMessage(chat_id, text=u'Не задан вопрос')


def main():
    # Create the EventHandler and pass it your bot's token.
    # token = '172154397:AAEeEbxveuvlfHL7A-zLBfV2HRrZkJTcsSc'
    # token for the test bot
    token = '172047371:AAFv5NeZ1Bx9ea-bt2yJeK8ajZpgHPgkLBk'
    updater = Updater(token, workers=100)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.addTelegramCommandHandler("ask", ask)
    dp.addTelegramCommandHandler("answer", answer)
    dp.addTelegramCommandHandler("next_tour", next_tour)
    dp.addTelegramCommandHandler("status", status)

    # Start the Bot
    updater.start_polling(poll_interval=0.1, timeout=120)

    updater.idle()


if __name__ == '__main__':
    main()
