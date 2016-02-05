"""
Implementation of classes Question, Tournament and Game
"""
from weakref import WeakKeyDictionary
from xml_tools import q_and_a, tournament_info, recent_tournaments
from constants import TRANSLATIONS


class XMLField(object):
    """
    descriptor class for Question fields
    """
    def __init__(self, field_name, default_value=''):
        self.field_name = field_name
        self.default_value = default_value
        self.data = WeakKeyDictionary()

    def __set__(self, instance, question_dict):
        self.data[instance] = question_dict.get(self.field_name, '')

    def __get__(self, instance, owner):
        if self.data[instance]:
            if self.field_name == 'question':
                return u'{0} {1}: {2}\n'.format(TRANSLATIONS[self.field_name],
                                                instance.question_number,
                                                self.data[instance])
            else:
                return u'{0}: {1}\n'.format(TRANSLATIONS[self.field_name],
                                            self.data[instance])
        else:
            return ''


class Question(object):
    """
    question with all its fields
    """
    answer = XMLField('answer')
    pass_criteria = XMLField('pass_criteria')
    comments = XMLField('comments')
    sources = XMLField('sources')
    authors = XMLField('authors')

    def __init__(self, tournament_id, tour_number, question_number):
        """
        :param tournament_id:
        :param tour_number:
        :param question_number:
        :return: instance of Question with all fields filled
        """
        question_dict = q_and_a(tournament_id, tour_number, question_number)
        self.id = (tournament_id, tour_number, question_number)
        self.question_number = question_number
        self.question = question_dict.get('question', '')
        self.question_image = question_dict.get('question_image', '')
        self.answer = question_dict
        self.pass_criteria = question_dict
        self.comments = question_dict
        self.sources = question_dict
        self.authors = question_dict

    @property
    def full_answer(self):
        """
        :return: text of answer with all the complementary fields
        """
        return u'{0}{1}{2}{3}{4}'.format(self.answer, self.pass_criteria,
                                         self.comments, self.sources,
                                         self.authors)


class TournamentError(Exception):
    """
    ошибка загрузки турнира
    """
    pass


class NextTourError(Exception):
    """
    ошибка перехода к следующему туру
    """
    pass


class Tournament(object):
    """
    class for tournament
    """
    def __init__(self, url, current_tour=1, current_question=0):
        self.url = url
        data = tournament_info(url)
        if not data:
            raise TournamentError
        self.title = data.get('title', '')
        self.description = data.get('description', '')
        self.number_of_tours = data.get('n_tours', '')
        self.number_of_questions = data.get('n_questions', [])
        self.tour_titles = data.get('tour_titles', [])
        self.tour_info = data.get('tour_info', [])
        self.tour_editors = data.get('tour_editors', [])
        self.current_tour = current_tour
        self.current_question = current_question

    @property
    def full_description(self):
        """
        :return: string with title and description of the tournament
        """
        return '{0}{1}'.format(self.title, self.description)

    def __iter__(self):
        return self

    def __next__(self):
        if self.current_tour == self.number_of_tours and \
                self.current_question == self.number_of_questions[-1] or \
                self.current_tour > self.number_of_tours:
            raise StopIteration
        else:
            self.current_question += 1
            if self.current_question > \
                    self.number_of_questions[self.current_tour - 1]:
                self.current_question = 1
                self.current_tour += 1
            question = Question(self.url,
                                self.current_tour,
                                self.current_question)
            return question

    def next_tour(self):
        """
        переместить указатель текущего вопроса и тура на первый вопрос
        следующего тура
        :return:
        """
        if self.current_tour < self.number_of_tours:
            self.current_tour += 1
            self.current_question = 0
        else:
            raise NextTourError


class Game(object):
    """
    implements game process for the bot
    """
    def __init__(self, bot, chat_id, current_tournament=None):
        self.bot = bot
        self.chat_id = chat_id
        self.current_tournament = current_tournament
        self.tournaments_list = None
        self.last_shown_tournament = 0
        self.state = None
        self.current_answer = None
        self.hint = ''

    def post(self, message):
        """
        :param message: text string
        :return: sends message to the chat with chat_id = self.chat_id
        """
        self.bot.sendMessage(self.chat_id, message)

    def get_recent(self):
        """
        :return: loads list of recent tournaments to self.tournaments_list;
        posts list of first 10 tournaments to the chat
        """
        self.tournaments_list = recent_tournaments()
        if len(self.tournaments_list) == 0:
            self.post('сайт db.chgk.info не возвращает список турниров. '
                      'Попробуйте позже')
            return
        text = ''
        for index, tournament in enumerate(self.tournaments_list[:10]):
            text += str(index+1) + '. ' + tournament['title'] + '\n'
        self.last_shown_tournament = 10
        self.post(text)

    def more(self):
        """
        show ten more tournaments from the list of loaded tournaments
        :return:
        """
        if self.last_shown_tournament == len(self.tournaments_list):
            self.post("Больше нет")
            return
        else:
            text = ''
            max_border = min(self.last_shown_tournament + 10,
                             len(self.tournaments_list))
            more_tournaments = self.tournaments_list[
                self.last_shown_tournament:max_border]
            for index, tournament in enumerate(more_tournaments):
                text += str(index + self.last_shown_tournament + 1) +\
                        '. ' + tournament['title'] + '\n'
            self.last_shown_tournament = max_border
            self.post(text)

    def play(self, tournament_id):
        """
        :param tournament_id: id of a tournament from self.tournaments_list
        :return: loads tournament into self.current_tournaments; posts
        description of a tournament
        """
        self.state = None
        try:
            tournament_url = self.tournaments_list[tournament_id-1]['link']
        except TypeError:
            self.post("Загрузите список турниров с помощью /recent")
            return
        try:
            self.current_tournament = Tournament(tournament_url)
        except TournamentError:
            self.post('Ошибка при загрузке турнира. Выберите другой турнир')
            return
        self.post(self.current_tournament.full_description)
        self.post("/ask - задать первый вопрос")

    def ask(self):
        """
        возвращает очередной вопрос текущего турнира, если он есть; заполняет
        self.hint - подсказку, выдаваемую после публикации ответа
        :return: объект Question
        """
        try:
            question = next(self.current_tournament)
            self.state = question.id
            self.current_answer = question.full_answer
            self.hint = 'Следующий вопрос - /ask'
            if self.state[2] == self.current_tournament.number_of_questions[
                    self.state[1]-1]:
                if self.state[1] == self.current_tournament.number_of_tours:
                    self.hint = 'Конец турнира'
                else:
                    self.hint = 'Конец тура. ' + self.hint
            if self.state[2] == 1:
                tour_number = self.state[1]-1
                text = self.current_tournament.tour_titles[tour_number] + \
                    '\nРедакторы: ' + \
                    self.current_tournament.tour_editors[tour_number] + \
                    '\n' + self.current_tournament.tour_info[tour_number]
                self.post(text)
            return question
        except TypeError:
            self.post("Выберите турнир - /play [номер турнира]")
            return
        except StopIteration:
            self.post("Сыграны все вопросы турнира. "
                      "Выберите турнир - /play [номер турнира]")
            return

    def next_tour(self):
        """
        переход к следующему туру
        :return:
        """
        try:
            self.state = None
            self.current_tournament.next_tour()
        except AttributeError:
            # self.post("Выберите турнир - /play [номер турнира]")
            pass
        except NextTourError:
            self.post("Это последний тур")
            raise

    def export(self):
        """
        выгрузка информации об игре в словарь
        :return: словарь, позволяющий восстановить игру
        """
        return {
            'current_tournament': getattr(self.current_tournament, 'url', None)
        }

if __name__ == "__main__":
    test_tournament = Tournament('http://db.chgk.info/tour/vdi15-03')
    for q in test_tournament:
        print(q.question)
