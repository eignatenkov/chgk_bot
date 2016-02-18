#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" tools for getting questions and tournaments from db.chgk.info
"""
from urllib.request import urlopen, HTTPError
from html.parser import HTMLParser
from lxml import etree, html
from bs4 import BeautifulSoup


def neat(text):
    """
    texts of questions from db.chgk.info contain many unnecessary newline
    symbols. This function replaces such symbols with spaces and keeps only
    those newline symbols that go in pairs.
    :param text: input string
    :return: edited text
    """
    text = text.replace('\n\n', '_zzz_')
    text = text.replace('\n', ' ')
    text = text.replace('_zzz_', '\n\n')
    return text


class MLStripper(HTMLParser):
    """ class from stackoverflow post to strip all HTML tags from the text
    of the question
    """
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    """
    function that uses MLStripper and strips all HTML tags from text
    :param html: input text
    :return: edited text without any HTML tags in it
    """
    # сначала заменим тэги для тире на --, чтобы не потерять их
    html = html.replace('&mdash;', '--')
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def recent_tournaments():
    """
    list of recent tournaments
    :return: list of recent tournaments
    """
    recent_url = urlopen("http://db.chgk.info/last/feed")
    recent_data = recent_url.read()
    recent_url.close()
    recent_xml = etree.fromstring(recent_data)
    tournaments = []
    for item in recent_xml[0]:
        if item.tag == 'item':
            tournament = dict()
            for child in item:
                tournament[child.tag] = child.text
            tournaments.append(tournament)
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
    tournament = etree.fromstring(tournament_url.read())
    tournament_url.close()
    result = dict()
    result['title'] = tournament.find('Title').text
    description = '\n' + tournament.find('PlayedAt').text
    if tournament.find('Editors').text is not None:
        description += '\n' + u'Редакторы: ' + tournament.find('Editors').text
    if tournament.findtext('Info') is not None:
        description += '\n' + neat(tournament.findtext('Info'))
    result['description'] = description
    result['n_tours'] = int(tournament.findtext('ChildrenNum'))
    result['n_questions'] = []
    result['tour_titles'] = []
    result['tour_info'] = []
    result['tour_editors'] = []
    for child in tournament:
        if child.tag == 'tour':
            result['n_questions'].append(int(child.findtext('QuestionsNum')))
            result['tour_titles'].append(child.findtext('Title'))
            result['tour_info'].append(neat(child.findtext('Info')))
            result['tour_editors'].append(child.findtext('Editors'))
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
    quest = etree.fromstring(question_url.read())
    question_url.close()
    result = dict()
    result['question'] = neat(strip_tags(quest.findtext('Question')))
    xhtml = html.document_fromstring(quest.findtext('Question'))
    imageurl = xhtml.xpath('//img/@src')
    if len(imageurl) > 0:
        result['question_image'] = imageurl[0]
    result['answer'] = neat(strip_tags(quest.findtext('Answer')))
    if quest.findtext('Comments'):
        result['comments'] = neat(strip_tags(quest.findtext('Comments')))
    if quest.findtext('PassCriteria'):
        result['pass_criteria'] = neat(strip_tags(quest.findtext('PassCriteria')))
    if quest.findtext('Sources'):
        result['sources'] = neat(strip_tags(quest.findtext('Sources')))
    if quest.findtext('Authors'):
        result['authors'] = strip_tags(quest.findtext('Authors'))
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
                tournaments[tour.TextId.text] = tour.Title.text
            elif tour.Type.text == 'Г':
                parse_dir(tour.TextId.text)

    parse_dir()
    return tournaments

if __name__ == "__main__":
    export_tournaments()
