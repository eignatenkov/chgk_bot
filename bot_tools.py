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
            return u'{0}: {1}\n'.format(TRANSLATIONS[self.field_name],
                                        self.data[instance])
        else:
            return ''


class Question(object):
    """
    question with all its fields
    """
    question = XMLField('question')
    question_image = XMLField('question_image')
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
        self.question = question_dict
        self.question_image = question_dict
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


class Tournament(object):
    """
    class for tournament
    """
    # title = XMLField('title')
    # description = XMLField('description')
    # number_of_tours = XMLField('n_tours')
    # number_of_questions = XMLField('n_questions')

    def __init__(self, url):
        self.url = url
        data = tournament_info(url)
        self.title = data.get('title', '')
        self.description = data.get('description', '')
        self.number_of_tours = data.get('n_tours', '')
        self.number_of_questions = data.get('n_questions', [])
        self.tour_titles = data.get('tour_titles', [])
        self.tour_info = data.get('tour_info', '')
        self.tour_editors = data.get('tour_editors')
        self.current_tour = 1
        self.current_question = 1

    @property
    def full_description(self):
        """
        :return: string with title and description of the tournament
        """
        return '{0}{1}'.format(self.title, self.description)

    def __iter__(self):
        return self

    def __next__(self):
        if self.current_tour <= self.number_of_tours:
            question = Question(self.url,
                                self.current_tour,
                                self.current_question)
            self.current_question += 1
            if self.current_question > \
                    self.number_of_questions[self.current_tour - 1]:
                self.current_question = 1
                self.current_tour += 1
            return question
        else:
            raise StopIteration


class Game(object):
    """
    implements game process for the bot
    """
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        self.current_tournament = None
        self.tournaments_list = None
        self.last_shown_tournament = 0

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

    def play(self, tournament_id):
        """
        :param tournament_id: id of a tournament from self.tournaments_list
        :return: loads tournament into self.current_tournaments; posts
        description of a tournament
        """
        try:
            tournament_url = self.tournaments_list[tournament_id-1]['link']
        except TypeError:
            self.post("Загрузите список турниров с помощью /recent")
            return
        self.current_tournament = Tournament(tournament_url)
        self.post(self.current_tournament.full_description)
        self.post("/ask - задать первый вопрос")


if __name__ == "__main__":
    test_tournament = Tournament('http://db.chgk.info/tour/vdi15-03')
    for q in test_tournament:
        print(q.question)
