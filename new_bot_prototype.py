"""
Bot you can play with
"""
import logging
from time import sleep
from telegram import Updater
from bot_tools import Game

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)

all_games = {}


def start(bot, update):
    chat_id = update.message.chat_id
    all_games[chat_id] = Game(bot, chat_id)
    text = "/recent - список последних десяти загруженных в базу пакетов\n" \
           "/more - следующие 10 турниров\n" \
           "/play [номер пакета] - играть пакет из списка с переданным " \
           "номером. Если номер не передан - самый последний загруженный " \
           "пакет\n" \
           "/ask - задать очередной вопрос\n" \
           "/answer - увидеть ответ, не дожидаясь конца минуты\n" \
           "/next_tour - следующий тур\n" \
           "Сыграть последний загруженный турнир, начиная с первого " \
           "вопроса - последовательно выполнить " \
           "/start, /recent, /play, /ask"
    all_games[chat_id].post(text)


def recent(bot, update):
    chat_id = update.message.chat_id
    try:
        all_games[chat_id].get_recent()
    except KeyError:
        bot.sendMessage(chat_id, "/start the bot")


def play(bot, update, args):
    chat_id = update.message.chat_id
    try:
        tournament_id = int(args[0])
    except IndexError:
        tournament_id = 1
    except ValueError:
        bot.sendMessage(chat_id, "Некорректный параметр для /play")
        return
    try:
        all_games[chat_id].play(tournament_id)
    except KeyError:
        bot.sendMessage(chat_id, "/start the bot")


def ask(bot, update):
    """
    обработка команды /ask - задание очередного вопроса
    """
    chat_id = update.message.chat_id
    try:
        question = all_games[chat_id].ask()
        current_state = all_games[chat_id].state
        all_games[chat_id].post('Вопрос {}'.format(question.question_number))
        sleep(1)
        if question.question_image:
            all_games[chat_id].post(question.question_image)
        all_games[chat_id].post(question.question)

        def read_question(bot):
            if current_state == all_games[chat_id].state:
                all_games[chat_id].post('Время пошло!')

        def ten_seconds(bot):
            if current_state == all_games[chat_id].state:
                all_games[chat_id].post('10 секунд')

        def time_is_up(bot):
            if current_state == all_games[chat_id].state:
                all_games[chat_id].post('Время!')

        def post_answer(bot):
            if current_state == all_games[chat_id].state:
                all_games[chat_id].post(question.full_answer)
                all_games[chat_id].post('Следующий вопрос: /ask')
        job_queue.put(read_question, 10, repeat=False)
        job_queue.put(ten_seconds, 50, repeat=False)
        job_queue.put(time_is_up, 60, repeat=False)
        job_queue.put(post_answer, 70, repeat=False)
    except KeyError:
        bot.sendMessage(chat_id, "/start the bot")
    except AttributeError:
        return


def answer(bot, update):
    """
    Обработка команды /answer - досрочная печать ответа
    """
    chat_id = update.message.chat_id
    try:
        all_games[chat_id].post(all_games[chat_id].current_answer)
        all_games[chat_id].post('Следующий вопрос: /ask')
        all_games[chat_id].state = None
    except KeyError:
        bot.sendMessage(chat_id, "/start the bot")
    except AttributeError:
        return


def bot_help(bot, update):
    """ help command """
    text = "/recent - список последних десяти загруженных в базу пакетов\n" \
           "/more - следующие 10 турниров\n" \
           "/play [номер пакета] - играть пакет из списка с переданным " \
           "номером. Если номер не передан - самый последний загруженный " \
           "пакет\n" \
           "/ask - задать очередной вопрос\n" \
           "/answer - увидеть ответ, не дожидаясь конца минуты\n" \
           "/next_tour - следующий тур"
    bot.sendMessage(update.message.chat_id, text=text)


def any_message(bot, update):
    """
    запись всех сообщений во всех чатах в лог
    """
    logger.info("New message\nFrom: %s\nchat_id: %d\nText: %s" %
                (update.message.from_user,
                 update.message.chat_id,
                 update.message.text))


def unknown_command(bot, update):
    """
    обработчик вызова несуществующих команд
    """
    bot.sendMessage(update.message.chat_id, text='Несуществующая команда')


def bot_error(bot, update, error):
    """ Print error to console """
    logger.warning('Update {0} caused error {1}'.format(update, error))


def main():
    global job_queue
    # token = '172154397:AAEeEbxveuvlfHL7A-zLBfV2HRrZkJTcsSc'
    # token for the test bot
    token = '172047371:AAFv5NeZ1Bx9ea-bt2yJeK8ajZpgHPgkLBk'
    updater = Updater(token, workers=100)
    job_queue = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", bot_help)
    dp.addTelegramCommandHandler("recent", recent)
    # dp.addTelegramCommandHandler("more", more)
    dp.addTelegramCommandHandler("play", play)
    dp.addTelegramCommandHandler("ask", ask)
    dp.addTelegramCommandHandler("answer", answer)
    # dp.addTelegramCommandHandler("next_tour", next_tour)
    # dp.addTelegramCommandHandler("status", status)
    #
    dp.addUnknownTelegramCommandHandler(unknown_command)
    dp.addTelegramRegexHandler('.*', any_message)
    dp.addErrorHandler(bot_error)

    # Start the Bot
    updater.start_polling(poll_interval=0.1, timeout=120)
    updater.idle()


if __name__ == '__main__':
    main()
