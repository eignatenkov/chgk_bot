from telegram import Updater
from bot_tools import Game
import logging

# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)

all_games = {}


def start(bot, update):
    chat_id = update.message.chat_id
    all_games[chat_id] = Game(bot, chat_id)
    all_games[chat_id].post("Successful init!")


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


def test_queue(bot, update):
    chat_id = update.message.chat_id

    def queue_function(bot):
        return all_games[chat_id].post('15 seconds passed')
    job_queue.put(queue_function, 15, repeat=False)
    all_games[chat_id].post("Wait for it")


def help(bot, update):
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
    dp.addTelegramCommandHandler("help", help)
    dp.addTelegramCommandHandler("recent", recent)
    # dp.addTelegramCommandHandler("more", more)
    dp.addTelegramCommandHandler("play", play)
    # dp.addTelegramCommandHandler("ask", ask)
    # dp.addTelegramCommandHandler("answer", answer)
    # dp.addTelegramCommandHandler("next_tour", next_tour)
    # dp.addTelegramCommandHandler("status", status)
    #
    # dp.addUnknownTelegramCommandHandler(unknown_command)
    # dp.addTelegramRegexHandler('.*', any_message)
    #
    #
    # dp.addErrorHandler(error)

    # Start the Bot
    updater.start_polling(poll_interval=0.1, timeout=120)

    updater.idle()


if __name__ == '__main__':
    main()