from telegram import Updater
from random import choice

updater = Updater(token='172047371:AAFv5NeZ1Bx9ea-bt2yJeK8ajZpgHPgkLBk')

dispatcher = updater.dispatcher

answers = ['It is certain', 'It is decidedly so', 'Without a doubt', 'Yes, definitely', 'You may rely on it',
           'As I see it, yes', 'Most likely', 'Outlook good', 'Yes', 'Signs point to yes', 'Reply hazy try again',
           'Ask again later', 'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again',
           "Don't count on it", 'My reply is no', 'My sources say no', 'Outlook not so good', 'Very doubtful']


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Magic 8-ball is ready to answer your questions. /ask if you "
                                                         "dare")


def ask(bot, update):
    message = choice(answers)
    question = update.message.text.strip('/ask')
    if question == '':
        bot.sendMessage(chat_id=update.message.chat_id, text="You didn't ask anything, fool!")
    else:
        bot.sendMessage(chat_id=update.message.chat_id, text=message)


dispatcher.addTelegramCommandHandler('ask', ask)

dispatcher.addTelegramCommandHandler('start', start)

updater.start_polling()

updater.idle()

