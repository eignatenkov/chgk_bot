#!/usr/bin/env python
# -*- coding: utf-8 -*-
from xml_tools import q_and_a, tournament_info


class Question:
    def __init__(self, tournament_id, tour_number, question_number):
        """
        :param data: словарь необходимых полей: вопрос, ответ, комментарий, зачет, пр.
        :return:
        """
        data = q_and_a(tournament_id, tour_number, question_number)
        self.question = data.get('question', '')
        self.question_image = data.get('question_image', '')
        self.answer = data.get('answer', '')
        self.pass_criteria = data.get('pass_criteria', '')
        self.comments = data.get('comments', '')
        self.sources = data.get('sources', '')
        self.authors = data.get('authors')


class Tournament:
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

    def next(self):

if __name__ == "__main__":
    test_question = Question('har14-h2', 2, 2)
    print test_question.question
    print test_question.answer
