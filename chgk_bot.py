"""
Bot you can play with
"""
import logging
import argparse
from time import sleep
from datetime import datetime
import json
import boto3
import os
from botocore.client import ClientError
from telegram import ParseMode, ReplyKeyboardMarkup, TelegramError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from bot_tools import Game, NextTourError, TournamentError
from xml_tools import export_tournaments
from rating_tools import get_country_results_on_weekend

# Enable logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
job_queue = None
tour_db = None
s3_resource = None
all_games = {}


def start(bot, update):
    """
    Запуск бота в чате
    :param bot:
    :param update:
    :return:
    """
    chat_id = update.message.chat_id
    all_games[chat_id] = Game()
    text = "/recent - список последних десяти загруженных в базу пакетов\n" \
           "/search [поисковый запрос] - поиск турнира по названию\n" \
           "/more - следующие 10 турниров\n" \
           "/play [номер пакета] - играть пакет из списка с переданным " \
           "номером. Если номер не передан - самый последний загруженный " \
           "пакет\n" \
           "/ask - задать очередной вопрос\n" \
           "/ask 2 4 - задать 4-й вопрос 2-го тура текущего турнира\n" \
           "/answer - увидеть ответ, не дожидаясь конца минуты\n" \
           "/next_tour - следующий тур"
    custom_keyboard = [['/recent']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    bot.sendMessage(chat_id, text, reply_markup=reply_markup)


def recent(bot, update):
    """
    Получить список последних загруженных турниров
    :param bot:
    :param update:
    :return:
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    keyboard, text = all_games[chat_id].get_recent()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    bot.sendMessage(chat_id, text, reply_markup=reply_markup)


def more(bot, update):
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
        keyboard, text = all_games[chat_id].more()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    except TypeError:
        bot.sendMessage(chat_id, "Не загружено ни одного турнира. /recent")


def search(bot, update, args):
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
    keyboard, text = all_games[chat_id].search(search_line, tour_db)
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    bot.sendMessage(chat_id, text, reply_markup=reply_markup)


def play(bot, update, args):
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
        custom_keyboard = [['/ask']]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard,
                                           resize_keyboard=True)
        bot.sendMessage(chat_id, all_games[chat_id].play(tournament_id),
                        reply_markup=reply_markup)

    except TypeError:
        bot.sendMessage(chat_id, "Загрузите список турниров с помощью /recent")
    except TournamentError:
        bot.sendMessage(chat_id, "Ошибка при загрузке турнира. Выберите "
                                 "другой турнир")
    except IndexError:
        bot.sendMessage(chat_id, "Нет турнира с таким номером. Выберите "
                                 "другой турнир")


def ask(bot, update, args):
    """
    обработка команды /ask - задание очередного вопроса
    :param bot:
    :param update:
    :param args: может быть передан номер тура и номер вопроса в нем
    :return:
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        logger.info("Новый участник %s, создаем игру", chat_id)
        all_games[chat_id] = Game()
    if len(args) not in [0, 2]:
        bot.sendMessage(chat_id, "Некорректный вызов команды /ask")
        logger.warning("Некорректный вызов команды /ask. args: %s", args)
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
            logger.warning("Некорректный вызов команды /ask. args: %s", args)
            return
    try:
        preface, question = all_games[chat_id].ask()
        current_state = all_games[chat_id].state
        if preface:
            bot.sendMessage(chat_id, preface)
        logger.info("Чат {0}, задаем вопрос {1}".format(
            chat_id, question.question_number))
        bot.sendMessage(chat_id, 'Вопрос {}'.format(question.question_number))
        sleep(1)
        if question.question_image:
            bot.sendPhoto(chat_id, question.question_image)
        custom_keyboard = [['/ask', '/answer']]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard,
                                           resize_keyboard=True)
        bot.sendMessage(chat_id, question.question,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN)

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
                custom_keyboard = [['/ask']]
                reply_markup = ReplyKeyboardMarkup(custom_keyboard,
                                                   resize_keyboard=True)
                bot.sendMessage(chat_id, question.full_answer,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup)
                logger.info("Чат {0}, шлем ответ".format(chat_id))
                if all_games[chat_id].hint:
                    bot.sendMessage(chat_id, all_games[chat_id].hint)
        job_queue.put(read_question, 10, repeat=False)
        job_queue.put(ten_seconds, 50, repeat=False)
        job_queue.put(time_is_up, 60, repeat=False)
        job_queue.put(post_answer, 70, repeat=False)
    except AttributeError:
        logger.warning("Ошибка Attribute Error")
        bot.sendMessage(chat_id, "Выберите турнир - /play [номер турнира]")
    except TypeError:
        logger.warning("Не выбран турнир")
        bot.sendMessage(chat_id, "Выберите турнир - /play [номер турнира]")
    except StopIteration:
        logger.info("Кончились вопросы турнира")
        bot.sendMessage(chat_id, "Сыграны все вопросы турнира. "
                                 "Выберите турнир - /play [номер турнира]")


def answer(bot, update):
    """
    Обработка команды /answer - досрочная печать ответа
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        all_games[chat_id] = Game()
    if all_games[chat_id].current_answer:
        logger.info("Чат {0}, шлем ответ".format(chat_id))
        custom_keyboard = [['/ask']]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard,
                                           resize_keyboard=True)
        bot.sendMessage(chat_id, all_games[chat_id].current_answer,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup)
        if all_games[chat_id].hint:
            bot.sendMessage(chat_id, all_games[chat_id].hint)
        all_games[chat_id].state = None
    else:
        bot.sendMessage(chat_id, "Не был задан вопрос")
        return


def next_tour(bot, update):
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
           "/search [поисковый запрос] - поиск турнира по названию\n" \
           "/more - следующие 10 турниров\n" \
           "/play [номер пакета] - играть пакет из списка с переданным " \
           "номером. Если номер не передан - самый последний загруженный " \
           "пакет\n" \
           "/ask - задать очередной вопрос\n" \
           "/ask 2 4 - задать 4-й вопрос 2-го тура текущего турнира\n" \
           "/answer - увидеть ответ, не дожидаясь конца минуты\n" \
           "/next_tour - следующий тур\n" \
           "/state - состояние игры"
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


def broadcast(bot, update):
    """
    Отправка сообщения всем пользователям
    :param bot:
    :param update:
    :return:
    """
    if update.message.chat_id == 94366427:
        to_delete = []
        for chat_id in all_games:
            try:
                bot.sendMessage(chat_id, update.message.text[11:])
                logger.info("Успешно отправлено %s", chat_id)
            except TelegramError as e:
                if e.message == 'Unauthorized':
                    logger.info("Не отправлено %s, бот блокирован", chat_id)
                    to_delete.append(chat_id)
                else:
                    logger.info("Не отправлено, %s", e.message)
        for user in to_delete:
            all_games.pop(user)


def get_state(bot, update):
    """
    Посмотреть текущий турнир, тур, вопрос
    :param bot:
    :param update:
    :return: информация о текущем турнире, туре, вопросе
    """
    chat_id = update.message.chat_id
    if chat_id not in all_games:
        bot.sendMessage(chat_id, text='Сейчас вы не играете никакой турнир')
    else:
        cur_tour = all_games[chat_id].current_tournament
        reply = "Последний сыгранный вопрос: {0}, тур {1}, вопрос {2}".format(
            cur_tour.title, cur_tour.current_tour, cur_tour.current_question
        )
        bot.sendMessage(chat_id, text=reply)


def current_results(bot, update):
    chat_id = update.message.chat_id
    message = ''
    for key, value in get_country_results_on_weekend().items():
        message += '*Турнир: {}*\n'.format(key)
        message += 'Команда\tМесто\tВзято\tБонус\n'
        message += '`------------------------`\n'
        for item in sorted(value, key=lambda x: float(x.get('position', 0))):
            message += '{0}\t{1}\t{2}\t*{3}*\n'.format(item.get('name', '-'),
                                                     item.get('position', 0),
                                                     item.get('questions_total', 0),
                                                     item.get('bonus_b', 0))
        message += '\n'
    bot.sendMessage(chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
    logger.info('Результаты отправлены')


def main():
    """
    считывание состояния игр, запуск бота
    :return:
    """
    global job_queue, tour_db, s3_resource

    parser = argparse.ArgumentParser()
    parser.add_argument('-test', action='store_true')
    args = parser.parse_args()
    if args.test:
        logger.info('Запускаем отладочного бота')
        token = os.environ['TEST_TOKEN']
    else:
        token = os.environ['TOKEN']

    s3_key = os.environ['AWS_ACCESS_KEY_ID']
    s3_secret = os.environ['AWS_SECRET_ACCESS_KEY']

    updater = Updater(token, workers=100)
    job_queue = updater.job_queue
    s3_resource = boto3.Session(aws_access_key_id=s3_key,
                                aws_secret_access_key=s3_secret).resource('s3')
    s3_tour_db = s3_resource.Object('chgk-bot', 'tour_db.json')
    s3_chgk_db = s3_resource.Object('chgk-bot', 'chgk_db.json')

    logger.info('Загружаем базу турниров')
    try:
        # with open('tour_db.json') as f:
        tour_db = json.loads(s3_tour_db.get()['Body'].read().decode('utf-8'))
        logger.info('База турниров загружена из s3')
    except ClientError:
        logger.warn('В s3 пусто, выгружаем турниры из базы')
        tour_db = export_tournaments()
        logger.info('Турниры выгружены из базы')
        with open('tour_db.json', 'w') as f:
            json.dump(tour_db, f)
        s3_tour_db.upload_file('tour_db.json')
        logger.info('Турниры загружены в s3')

    logger.info('Загружаем состояния игр из s3')

    flag = s3_resource.Object('chgk-bot', 'flag')

    def is_flag():
        try:
            flag.load()
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                exists = False
            else:
                raise e
        else:
            exists = True
        return exists

    try:
        if not args.test:
            while is_flag():
                logger.info('Бот уже запущен, ждем закрытия')
                sleep(2)

            logger.info('Ставим флаг')

            with open("flag", 'w') as f:
                json.dump({'flag': 1}, f)
            flag.upload_file("flag")

            logger.info('Флаг поставлен')
        logger.info('Загружаем состояния игр')

        game_state = json.loads(s3_chgk_db.get()['Body'].read().decode('utf-8'))
        for chat_id, game in game_state.items():
            all_games[int(chat_id)] = Game(**game)
        logger.info('Состояния игр успешно загружены')
    except ClientError:
        logger.info('Состояния игр не найдены, играем с нуля')

    def update_tour_db(bot):
        """
        Регулярное обновление списка турниров
        :param bot: фиктивный параметр для того, чтобы можно было использовать
        очередь пакета telegram
        :return:
        """

        d = datetime.today()
        if d.timetuple()[3] > 5:
            job_queue.put(update_tour_db, 60*60*(25-d.timetuple()[3]),
                          repeat=False)
            logger.info("рано обновлять базу турниров, ставим в ожидание")
        else:
            job_queue.put(update_tour_db, 60*60*24, repeat=False)
            logger.info("Начинаем обновлять базу турниров")
            global tour_db
            tour_db = export_tournaments()
            logger.info("База турниров успешно обновлена")
            with open('tour_db.json', 'w') as f:
                json.dump(tour_db, f)
            s3_tour_db.upload_file('tour_db.json')

    update_tour_db(updater.bot)

    logger.info('Поехали')

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", bot_help))
    dp.add_handler(CommandHandler("recent", recent))
    dp.add_handler(CommandHandler("more", more))
    dp.add_handler(CommandHandler("play", play, pass_args=True))
    dp.add_handler(CommandHandler("ask", ask, pass_args=True))
    dp.add_handler(CommandHandler("answer", answer))
    dp.add_handler(CommandHandler("next_tour", next_tour))
    dp.add_handler(CommandHandler("search", search, pass_args=True))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("state", get_state))

    # rating interface, just for fun
    dp.add_handler(CommandHandler("results", current_results))

    dp.add_handler(MessageHandler([Filters.command], unknown_command))
    dp.add_handler(MessageHandler([], any_message))
    dp.add_error_handler(bot_error)

    # Start the Bot
    updater.start_polling()
    updater.idle()

    # Dump current state when receive SIGTERM or SIGINT
    if not args.test:
        state = {}
        for key, value in all_games.items():
            state[key] = value.export()
        logger.info("Сохраняем состояние игр в s3")
        with open('chgk_db.json', 'w') as chgk_db:
            json.dump(state, chgk_db)
        s3_resource.Bucket('chgk-bot').upload_file('chgk_db.json',
                                                   'chgk_db.json')
        logger.info('Состояния игр сохранены')
        logger.info('снимаем флаг')
        flag.delete()
        logger.info('Флаг снят')

    else:
        logger.info("Выходим из тестового запуска, ничего не сохраняя")


if __name__ == '__main__':
    main()
