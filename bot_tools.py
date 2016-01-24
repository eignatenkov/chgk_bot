#!/usr/bin/env python
# -*- coding: utf-8 -*-
from xml_tools import q_and_a, tournament_info, recent_tournaments
from constants import TRANSLATIONS
from weakref import WeakKeyDictionary


class XMLField(object):
    def __init__(self, field_name, default_value=''):
        self.field_name = field_name
        self.default_value = default_value
        self.data = WeakKeyDictionary()

    def __set__(self, instance, question_dict):
        self.data[instance] = question_dict.get(self.field_name, '')

    def __get__(self, instance, owner):
        if self.data[instance]:
            return u'{0}: {1}\n'.format(TRANSLATIONS[self.field_name], self.data[instance])
        else:
            return ''


class Question(object):
    question = XMLField('question')
    question_image = XMLField('question_image')
    answer = XMLField('answer')
    pass_criteria = XMLField('pass_criteria')
    comments = XMLField('comments')
    sources = XMLField('sources')
    authors = XMLField('authors')

    def __init__(self, tournament_id, tour_number, question_number):
        """
        :param data: словарь необходимых полей: вопрос, ответ, комментарий, зачет, пр.
        :return:
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
        return u'{0}{1}{2}{3}{4}'.format(self.answer, self.pass_criteria, self.comments, self.sources, self.authors)


class Tournament(object):
    title = XMLField('title')
    description = XMLField('description')
    number_of_tours = XMLField('n_tours')
    number_of_questions = XMLField('n_questions')

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

    def __iter__(self):
        return self

    # def next(self):


class Game(object):
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        self.current_question = None
        self.tournaments_list = None
        self.last_shown_tournament = 0

    def post(self, message):
        self.bot.sendMessage(self.chat_id, message)

    def get_recent(self):
        self.tournaments_list = recent_tournaments()
        if len(self.tournaments_list) == 0:
            self.post('сайт db.chgk.info не возвращает список турниров. Попробуйте позже')
            return
        # # default tournament is the most recently added tournament
        # if 'tournament_id' not in state[chat_id] or state[chat_id].get('question_number', 0) == 0:
        #     state[chat_id]['tournament_id'] = state[chat_id]['tournaments'][0]['link']

        text = ''
        for index, tournament in enumerate(self.tournaments_list[:10]):
            text += str(index+1) + '. ' + tournament['title'] + '\n'
        self.last_shown_tournament = 10
        self.post(text)


if __name__ == "__main__":
    test_question = Question('har14-h2', 2, 2)
    print test_question.question, test_question.full_answer
    test_question = Question('har14-h2', 2, 3)
    print test_question.question, test_question.full_answer

