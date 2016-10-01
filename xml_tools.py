#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" tools for getting questions and tournaments from db.chgk.info
"""
import json
from urllib.request import urlopen, HTTPError
from bs4 import BeautifulSoup


def neat(text):
    """
    texts of questions from db.chgk.info contain many unnecessary newline
    symbols. This function replaces such symbols with spaces and keeps only
    those newline symbols that go in pairs. It also replaces [ with \[ to make
    MARKDOWN parse mode work.
    :param text: input string
    :return: edited text
    """
    text = text.replace('\n\n', '_zzz_')
    text = text.replace('\n', ' ')
    text = text.replace('_zzz_', '\n\n')
    text = text.replace('[', '\[')
    return text


def strip_tags(tagged_text):
    """
    function that uses MLStripper and strips all HTML tags from text
    :param tagged_text: tag from BeautifulSoup object
    :return: edited text without any HTML tags in it
    """
    if '&' in tagged_text.text or '<' in tagged_text.text:
        soup = BeautifulSoup(tagged_text.text, 'lxml')
        return soup.text
    else:
        return tagged_text.text


def recent_tournaments():
    """
    list of recent tournaments
    :return: list of recent tournaments
    """
    recent_url = urlopen("http://db.chgk.info/last/feed")
    soup = BeautifulSoup(recent_url, 'lxml-xml')
    tournaments = []
    for item in soup.find_all('item'):
        tournaments.append({'title': item.title.text,
                            'link': item.link.text})
    return tournaments


def tournament_info(url):
    """
    get tournament info by it's url
    :param url: url of tournament in db.chgk.info
    :return: dict with info about this tournament: description, number of
    tours, number of questions, editors, etc.
    """
    url += '/xml'
    try:
        tournament_url = urlopen(url)
    except HTTPError:
        return ''
    tournament = BeautifulSoup(tournament_url, 'lxml-xml')
    tournament_url.close()
    result = dict()
    result['title'] = neat(tournament.Title.text)
    description = '\n' + neat(tournament.PlayedAt.text)
    if tournament.Editors.text:
        description += '\n' + u'Редакторы: ' + tournament.Editors.text
    if tournament.Info.text:
        description += '\n' + neat(tournament.Info.text)
    result['description'] = description
    result['n_tours'] = int(tournament.ChildrenNum.text)
    result['n_questions'] = [int(item.QuestionsNum.text) for item in
                             tournament.find_all('tour')] if tournament.find_all('tour') else [int(tournament.QuestionsNum.text)]
    result['tour_titles'] = [item.Title.text for item in
                             tournament.find_all('tour')] if tournament.find_all('tour') else [tournament.Title.text]
    result['tour_info'] = [neat(item.Info.text) if item.Info != tournament.Info
                           else '' for item in tournament.find_all('tour')] if tournament.find_all('tour') else [tournament.Info.text]
    result['tour_editors'] = [item.Editors.text if
                              item.Editors != tournament.Editors else '' for
                              item in tournament.find_all('tour')] if tournament.find_all('tour') else [tournament.Editors.text]
    return result


def q_and_a(tournament_url, tour, question):
    """
    get all necessary info about the question: text, handouts (if present),
    answer, comments, author, sources.
    :param tournament_url: tournament url
    :param tour: tour number
    :param question: question number
    :return: dict with info about the question
    """
    url = 'http://db.chgk.info/question/{}.{}/{}/xml'.format(
        tournament_url.split('/')[-1], tour, question)
    question_url = urlopen(url)
    quest = BeautifulSoup(question_url, 'lxml-xml')
    question_url.close()
    result = dict()
    result['question'] = neat(strip_tags(quest.Question))
    imageurl = BeautifulSoup(quest.Question.text, 'lxml').img
    if imageurl:
        result['question_image'] = imageurl['src']
    result['answer'] = neat(strip_tags(quest.Answer))
    if quest.Comments:
        result['comments'] = neat(strip_tags(quest.Comments))
    if quest.PassCriteria:
        result['pass_criteria'] = neat(strip_tags(quest.PassCriteria))
    if quest.Sources:
        result['sources'] = neat(strip_tags(quest.Sources))
    if quest.Authors:
        result['authors'] = strip_tags(quest.Authors)
    return result


def export_tournaments():
    """
    Выгрузка всех турниров из базы вопросов и сохранение их
    в файл tour_db.json
    :return:
    """

    tournaments = {}
    url_template = 'http://db.chgk.info/tour/{}/xml'

    def parse_dir(title=None):
        """
        рекурсивная функция обхода дерева турниров в db.chgk.info
        :param title: Название поддиректории в дереве
        :return: заполненный словарь tournaments
        """
        if title:
            soup = BeautifulSoup(urlopen(url_template.format(title)),
                                 'lxml-xml')
        else:
            soup = BeautifulSoup(urlopen('http://db.chgk.info/tour/xml'),
                                 'lxml-xml')
        for tour in soup.findAll('tour'):
            if tour.Type.text == 'Ч':
                tournaments[tour.TextId.text] = {'title': tour.Title.text,
                                                 'date': tour.PlayedAt.text}
            elif tour.Type.text == 'Г':
                parse_dir(tour.TextId.text)

    parse_dir()
    return tournaments

if __name__ == "__main__":
    with open('tour_db.json', 'w') as f:
        json.dump(export_tournaments(), f)
