"""
Implementation of classes Question, Tournament and Game
"""
from operator import itemgetter
import requests
import re
from xml_tools import neat, tournament_info, recent_tournaments
import logging

# Enable logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Question(object):
    """
    question with all its fields
    """

    def __init__(self, question_id: str):
        """
        :param question_id: question id, e.g. "ivan18_u.1-1"
        :return: instance of Question with all fields filled
        """

        url = f"http://api.baza-voprosov.ru/questions/{question_id}"
        response = requests.get(url, headers={"accept": "application/json"}).json()
        m = re.search(r"(?<=pic: )\S*(?=\))", response["question"])
        if m:
            response["question_image"] = m.group(0)
            response["question"] = re.sub(r"\(pic: \S*\) \n", "", response["question"])
        response["question"] = response["question"].replace("<раздатка>", "Раздаточный материал:")
        response["question"] = response["question"].replace("</раздатка>", "")
        self.id = question_id
        self.number = response["number"]
        self.question = neat(response.get("question", ""))
        self.question_image = response.get("question_image", "")
        self.answer = neat(response["answer"])
        self.pass_criteria = neat(response["passCriteria"])
        self.comments = neat(response["comments"])
        self.sources = neat(response["sources"])
        self.authors = neat(response["authors"])

    @property
    def full_answer(self):
        """
        :return: text of answer with all the complementary fields
        """
        full_answer = f"*Ответ*: {self.answer}"
        if self.pass_criteria:
            full_answer += f"\n*Зачет*: {self.pass_criteria}"
        if self.comments:
            full_answer += f"\n*Комментарии*: {self.comments}"
        if self.sources:
            full_answer += f"\n*Источники*: {self.sources}"
        if self.authors:
            full_answer += f"\n*Авторы*: {self.authors}"
        return full_answer


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

    def __init__(self, url):
        if not url or url == '_u':
            return
        self.url = url.rsplit("/", maxsplit=1)[-1]
        data = tournament_info(self.url)
        if not data:
            raise TournamentError
        self.title = data.get("title", "")
        self.description = data.get("description", "")
        self.number_of_tours = data.get("n_tours", "")
        self.number_of_questions = data.get("n_questions", [])
        self.question_ids = data.get("question_ids", [])
        self.tour_titles = data.get("tour_titles", [])
        self.tour_info = data.get("tour_info", [])
        self.tour_editors = data.get("tour_editors", [])
        self.current_tour = 1
        self.current_question = 0

    @property
    def full_description(self):
        """
        :return: string with title and description of the tournament
        """
        return "{0}{1}".format(self.title, self.description)

    def __iter__(self):
        return self

    def __next__(self):
        if (
            self.current_tour == self.number_of_tours
            and self.current_question == self.number_of_questions[-1]
            or self.current_tour > self.number_of_tours
        ):
            raise StopIteration
        else:
            self.current_question += 1
            if self.current_question > self.number_of_questions[self.current_tour - 1]:
                self.current_question = 1
                self.current_tour += 1
            return Question(
                self.question_ids[self.current_tour - 1][self.current_question - 1]
            )

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

    def __init__(self, **kwargs):
        self.tournaments_list = kwargs.get("tournaments_list")
        self.last_shown_tournament = kwargs.get("last_shown_tournament", 0)
        self.state = None
        self.current_answer = kwargs.get("current_answer")
        self.hint = kwargs.get("hint", "")
        logger.info("Загружаем турнир {}".format(kwargs.get("current_tournament")))
        self.current_tournament = Tournament(kwargs.get("current_tournament"))
        if self.current_tournament:
            self.current_tournament.current_tour = kwargs.get("current_tour", 1)
            self.current_tournament.current_question = kwargs.get("current_question", 0)

    @staticmethod
    def get_keyboard(begin, end):
        """
        :param begin: начало нумерации передаваемых турниров
        :param end: конец нумерации передаваемых турниров
        :return: раскладка виртуальной клавиатуры для выбора турниров
        """
        current_number = begin
        answer = []
        while current_number <= end:
            next_line = [
                "/play {}".format(i)
                for i in range(current_number, (min(current_number + 4, end + 1)))
            ]
            if len(next_line) < 4 and end - begin == 9:
                next_line.append("/more")
            answer.append(next_line)
            current_number += 4
        return answer

    def get_recent(self):
        """
        loads list of recent tournaments to self.tournaments_list
        :return: раскладка клавиатуры, текст сообщения со списком турниров
        """
        self.tournaments_list = recent_tournaments()
        if len(self.tournaments_list) == 0:
            return (
                [],
                "сайт db.chgk.info не возвращает список турниров. " "Попробуйте позже",
            )
        text = ""
        for index, tournament in enumerate(self.tournaments_list[:10]):
            text += str(index + 1) + ". " + tournament["title"] + "\n"
        self.last_shown_tournament = 10
        return Game.get_keyboard(1, 10), text

    def search(self, search_line, tour_db):
        """
        Поиск турниров в базе по переданной текстовой строке
        :param search_line: поисковая строка
        :param tour_db: словарь со списком всех турниров
        :return: раскладка клавиатуры, текст сообщения со списком турниров
        """
        result = []
        url_template = "http://db.chgk.info/tour/{}"
        for tour_id, tour_info in tour_db.items():
            if search_line.lower() in tour_info["title"].lower():
                result.append(
                    {
                        "link": url_template.format(tour_id),
                        "date": tour_info["date"],
                        "title": tour_info["title"],
                    }
                )
        if len(result) == 0:
            return [], "Ничего не найдено"
        else:
            self.tournaments_list = sorted(result, key=itemgetter("date"))
            text = ""
            max_border = min(10, len(self.tournaments_list))
            more_tournaments = self.tournaments_list[:max_border]
            for index, tournament in enumerate(more_tournaments):
                text += "{0}. {1} {2}\n".format(
                    str(index + 1), tournament["title"], tournament["date"]
                )
                self.last_shown_tournament = max_border
            return Game.get_keyboard(1, max_border), text

    def more(self):
        """
        show ten more tournaments from the list of loaded tournaments
        :return:
        """
        if self.last_shown_tournament == len(self.tournaments_list):
            return [], "Больше нет"
        else:
            text = ""
            max_border = min(
                self.last_shown_tournament + 10, len(self.tournaments_list)
            )
            more_tournaments = self.tournaments_list[
                self.last_shown_tournament : max_border
            ]
            for index, tournament in enumerate(more_tournaments):
                text += "{0}. {1} {2}\n".format(
                    str(index + self.last_shown_tournament + 1),
                    tournament["title"],
                    tournament.get("date", ""),
                )
            keyboard = Game.get_keyboard(self.last_shown_tournament + 1, max_border)
            self.last_shown_tournament = max_border
            return keyboard, text

    def play(self, tournament_id):
        """
        :param tournament_id: id of a tournament from self.tournaments_list
        :return: loads tournament into self.current_tournaments; posts
        description of a tournament
        """
        self.state = None
        try:
            tournament_url = self.tournaments_list[tournament_id - 1]["link"]
        except TypeError:
            raise
        except IndexError:
            raise
        try:
            self.current_tournament = Tournament(tournament_url)
            self.state = (tournament_url, 1, 0)
        except TournamentError:
            raise
        return self.current_tournament.full_description

    def ask(self):
        """
        возвращает очередной вопрос текущего турнира, если он есть; заполняет
        self.hint - подсказку, выдаваемую после публикации ответа
        :return: объект Question
        """
        try:
            ct = self.current_tournament
            question = next(ct)
            self.state = (ct.url, ct.current_tour, ct.current_question)
            self.current_answer = question.full_answer
            self.hint = ""
            preface = ""
            if ct.current_question == ct.number_of_questions[ct.current_tour - 1]:
                if ct.current_tour == ct.number_of_tours:
                    self.hint = "Конец турнира"
                else:
                    self.hint = "Конец тура"
            if question.number == 1:
                tour_number = ct.current_tour - 1
                tour_titles = ct.tour_titles
                preface = tour_titles[tour_number]
                if ct.tour_editors[tour_number]:
                    preface += "\nРедакторы: " + ct.tour_editors[tour_number]
                if ct.tour_info[tour_number]:
                    preface += "\n" + ct.tour_info[tour_number]
            return preface, question
        except TypeError:
            raise
        except StopIteration:
            raise

    def next_tour(self):
        """
        переход к следующему туру
        :return:
        """
        try:
            self.state = None
            self.current_tournament.next_tour()
        except AttributeError:
            pass
        except NextTourError:
            raise

    def export(self):
        """
        выгрузка информации об игре в словарь
        :return: словарь, позволяющий восстановить игру
        """
        return {
            "tournaments_list": self.tournaments_list,
            "last_shown_tournament": self.last_shown_tournament,
            "current_tournament": getattr(self.current_tournament, "url", None),
            "current_tour": getattr(self.current_tournament, "current_tour", None),
            "current_question": getattr(
                self.current_tournament, "current_question", None
            ),
            "current_answer": self.current_answer,
            "hint": getattr(self, "hint", ""),
        }
