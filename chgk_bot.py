"""
Bot you can play with
"""
import logging
from time import sleep
import json
from telegram import Updater, ParseMode
from bot_tools import Game, NextTourError, TournamentError

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)
job_queue = None
tour_db = None
all_games = {}


def update_state(func):
    """
    декоратор для сохранения состояния игры в файл
    """
    def wrapper(*pargs, **kwargs):
        """
        подмена декорируемой функции
        :param pargs: формат передаваемых параметров в соответствии с
        документацией по python-telegram-bot
        :param kwargs: формат передаваемых параметров в соответствии с
        документацией по python-telegram-bot
        :return:
        """
        result = func(*pargs, **kwargs)
        state = {}
        for key, value in all_games.items():
            state[key] = value.export()
        with open('chgk_db.json', 'w') as chgk_db:
            json.dump(state, chgk_db)
        return result
    return wrapper


@update_state
def start(bot, update, **kwargs):
    """
    Запуск бота в чате
    :param bot:
    :param update:
    :return:
    """
    chat_id = update.message.chat_id
    all_games[chat_id] = Game()
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
           "/recent, /play, /ask"
    bot.sendMessage(chat_id, text)


@update_state
def recent(bot, update, **kwargs):
    """
    Получить список последних загруженных турниров
    :param bot:
    :param update:
    :return:
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    bot.sendMessage(chat_id, all_games[chat_id].get_recent())


@update_state
def more(bot, update, **kwargs):
    """
    Показать еще десять загруженных турниров
    :param bot:
    :param update:
    :return:
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    try:
        bot.sendMessage(chat_id, all_games[chat_id].more())
    except TypeError:
        bot.sendMessage(chat_id, "Не загружено ни одного турнира. /recent")


@update_state
def search(bot, update, args, **kwargs):
    """
    Поиск турниров по переданной после команды /search текстовой строке
    :param bot:
    :param update:
    :param args:
    :param kwargs:
    :return:
    """
    chat_id = update.message.chat_id
    search_line = ' '.join(args)
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    bot.sendMessage(chat_id, all_games[chat_id].search(search_line, tour_db))


@update_state
def play(bot, update, args, **kwargs):
    """
    Играть турнир с заданным номером
    :param bot:
    :param update:
    :param args:
    :return:
    """
    chat_id = update.message.chat_id
    try:
        tournament_id = int(args[0])
    except IndexError:
        tournament_id = 1
    except ValueError:
        bot.sendMessage(chat_id, "Некорректный параметр для /play")
        return
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    try:
        bot.sendMessage(chat_id, all_games[chat_id].play(tournament_id))
        bot.sendMessage(chat_id, "/ask - задать первый вопрос")
    except TypeError:
        bot.sendMessage(chat_id, "Загрузите список турниров с помощью /recent")
    except TournamentError:
        bot.sendMessage(chat_id, "Ошибка при загрузке турнира. Выберите "
                                 "другой турнир")
    except IndexError:
        bot.sendMessage(chat_id, "Нет турнира с таким номером. Выберите "
                                 "другой турнир")


@update_state
def ask(bot, update, args, **kwargs):
    """
    обработка команды /ask - задание очередного вопроса
    :param bot:
    :param update:
    :param args: может быть передан номер тура и номер вопроса в нем
    :return:
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        print(chat_id)
        all_games[chat_id] = Game()
    if len(args) not in [0, 2]:
        bot.sendMessage(chat_id, "Некорректный вызов команды /ask")
        return
    elif len(args) == 2:
        try:
            tour, number = [int(arg) for arg in args]
            print(tour, number)
            q_numbers = \
                all_games[chat_id].current_tournament.number_of_questions
            if q_numbers[0] < q_numbers[1]:
                tour += 1
            all_games[chat_id].current_tournament.current_tour = tour
            all_games[chat_id].current_tournament.current_question = number - 1
        except ValueError:
            pass
    try:
        preface, question = all_games[chat_id].ask()
        current_state = all_games[chat_id].state
        if preface:
            bot.sendMessage(chat_id, preface)
        bot.sendMessage(chat_id, 'Вопрос {}'.format(question.question_number))
        sleep(1)
        if question.question_image:
            bot.sendPhoto(chat_id, question.question_image)
        bot.sendMessage(chat_id, question.question)

        def read_question(bot):
            """ функция для очереди, запуск минуты на обсуждение """
            if current_state == all_games[chat_id].state:
                bot.sendMessage(chat_id, 'Время пошло!')

        def ten_seconds(bot):
            """ функция для очереди, отсчет 10 секунд """
            if current_state == all_games[chat_id].state:
                bot.sendMessage(chat_id, '10 секунд')

        def time_is_up(bot):
            """ функция для очереди, время кончилось """
            if current_state == all_games[chat_id].state:
                bot.sendMessage(chat_id, 'Время!')

        def post_answer(bot):
            """ функция для очереди, печать ответа """
            if current_state == all_games[chat_id].state:
                bot.sendMessage(chat_id, question.full_answer,
                                parse_mode=ParseMode.MARKDOWN)
                bot.sendMessage(chat_id, all_games[chat_id].hint)
        job_queue.put(read_question, 10, repeat=False)
        job_queue.put(ten_seconds, 50, repeat=False)
        job_queue.put(time_is_up, 60, repeat=False)
        job_queue.put(post_answer, 70, repeat=False)
    except AttributeError:
        return
    except TypeError:
        bot.sendMessage(chat_id, "Выберите турнир - /play [номер турнира]")
    except StopIteration:
        bot.sendMessage(chat_id, "Сыграны все вопросы турнира. "
                                 "Выберите турнир - /play [номер турнира]")


@update_state
def answer(bot, update, **kwargs):
    """
    Обработка команды /answer - досрочная печать ответа
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    if all_games[chat_id].current_answer:
        bot.sendMessage(chat_id, all_games[chat_id].current_answer,
                        parse_mode=ParseMode.MARKDOWN)
        bot.sendMessage(chat_id, all_games[chat_id].hint)
        all_games[chat_id].state = None
    else:
        bot.sendMessage(chat_id, "Не был задан вопрос")
        return


@update_state
def next_tour(bot, update, **kwargs):
    """
    Обработка команды /next_tour - переход к следующему туру
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    try:
        all_games[chat_id].next_tour()
        ask(bot, update, '')
    except NextTourError:
        bot.sendMessage(chat_id, "Это последний тур")


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
    logger.info("New message\nFrom: %s\nchat_id: %d\nText: %s",
                update.message.from_user,
                update.message.chat_id,
                update.message.text)


def unknown_command(bot, update):
    """
    обработчик вызова несуществующих команд
    """
    bot.sendMessage(update.message.chat_id, text='Несуществующая команда')


def bot_error(bot, update, error):
    """ Print error to console """
    logger.warning('Update %s caused error %s', update, error)


def main():
    """
    считывание состояния игр, запуск бота
    :return:
    """
    global job_queue, tour_db
    token = '172154397:AAEeEbxveuvlfHL7A-zLBfV2HRrZkJTcsSc'
    # token for the test bot
    # token = '172047371:AAFv5NeZ1Bx9ea-bt2yJeK8ajZpgHPgkLBk'
    updater = Updater(token, workers=100)
    job_queue = updater.job_queue

    with open('tour_db.json') as f:
        tour_db = json.load(f)

    try:
        with open('chgk_db.json') as f:
            state = json.load(f)
            for chat_id, game in state.items():
                all_games[int(chat_id)] = Game(**game)
    except FileNotFoundError:
        pass

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", bot_help)
    dp.addTelegramCommandHandler("recent", recent)
    dp.addTelegramCommandHandler("more", more)
    dp.addTelegramCommandHandler("play", play)
    dp.addTelegramCommandHandler("ask", ask)
    dp.addTelegramCommandHandler("answer", answer)
    dp.addTelegramCommandHandler("next_tour", next_tour)
    dp.addTelegramCommandHandler("search", search)

    dp.addUnknownTelegramCommandHandler(unknown_command)
    dp.addTelegramRegexHandler('.*', any_message)
    dp.addErrorHandler(bot_error)

    # Start the Bot
    updater.start_polling(poll_interval=0.1, timeout=120)
    updater.idle()


if __name__ == '__main__':
    main()
