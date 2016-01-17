# -*- coding: utf-8 -*-

from telegram import Updater
from telegram.dispatcher import run_async


def start(bot, update):
    pass


def help(bot, update):
    """ help command """
    text = u"/recent - список последних десяти загруженных в базу пакетов\n" \
           u"/more - следующие 10 турниров\n" \
           u"/play [номер пакета] - играть пакет из списка с переданным номером. Если номер не передан - самый " \
           u"последний загруженный пакет\n" \
           u"/ask - задать очередной вопрос\n" \
           u"/answer - увидеть ответ, не дожидаясь конца минуты\n" \
           u"/next_tour - следующий тур"
    bot.sendMessage(update.message.chat_id, text=text)

def main():
    # Create the EventHandler and pass it your bot's token.
    # token = '172154397:AAEeEbxveuvlfHL7A-zLBfV2HRrZkJTcsSc'
    # token for the test bot
    token = '172047371:AAFv5NeZ1Bx9ea-bt2yJeK8ajZpgHPgkLBk'
    updater = Updater(token, workers=100)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", help)
    dp.addTelegramCommandHandler("recent", recent)
    dp.addTelegramCommandHandler("more", more)
    dp.addTelegramCommandHandler("play", play)
    dp.addTelegramCommandHandler("ask", ask)
    dp.addTelegramCommandHandler("answer", answer)
    dp.addTelegramCommandHandler("next_tour", next_tour)
    dp.addTelegramCommandHandler("status", status)

    dp.addUnknownTelegramCommandHandler(unknown_command)
    dp.addTelegramRegexHandler('.*', any_message)


    dp.addErrorHandler(error)

    # Start the Bot
    updater.start_polling(poll_interval=0.1, timeout=120)

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


if __name__ == '__main__':
    main()