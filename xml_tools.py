#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" tools for getting questions and tournaments from db.chgk.info
"""
import json
import requests
from urllib.request import urlopen
from bs4 import BeautifulSoup
import ssl

# This restores the same behavior as before.
CONTEXT = ssl._create_unverified_context()


def neat(text):
    """
    texts of questions from db.chgk.info contain many unnecessary newline
    symbols. This function replaces such symbols with spaces and keeps only
    those newline symbols that go in pairs. It also replaces [ with \[ to make
    MARKDOWN parse mode work.
    :param text: input string
    :return: edited text
    """
    if isinstance(text, str):
        text = text.replace('\n\n', '_zzz_')
        text = text.replace('\n', ' ')
        text = text.replace('_zzz_', '\n\n')
        text = text.replace('[', '\[')
        text = text.replace('_', '\_')
        text = text.replace('*', '\*')
    return text


def recent_tournaments():
    """
    list of recent tournaments
    :return: list of recent tournaments
    """
    recent_url = urlopen("http://db.chgk.info/last/feed", context=CONTEXT)
    soup = BeautifulSoup(recent_url, 'lxml-xml')
    tournaments = []
    for item in soup.find_all('item'):
        tournaments.append({'title': item.title.text,
                            'link': item.link.text})
    return tournaments


def tournament_info(tournament_url):
    """
    get tournament info by it's url
    :param tournament_url: url of tournament in db.chgk.info
    :return: dict with info about this tournament: description, number of
    tours, number of questions, editors, etc.
    """
    url = f'http://api.baza-voprosov.ru/packages/{tournament_url}'
    response = requests.get(url, headers={'accept': 'application/json'}).json()
    result = dict()
    result['title'] = response['title']
    description = '\n' + response.get('playedAt', '')
    if response['editors']:
        description += '\n' + u'Редакторы: ' + response['editors']
    if response['info']:
        description += '\n' + response['info']
    result['description'] = description
    result['n_tours'] = len(response['tours'])
    result['n_questions'] = [len(tour['questions']) for tour in response['tours']] if 'tours' in response else \
        [len(response['Questions'])]
    result['question_ids'] = [[question['id'] for question in tour['questions']] for tour in response['tours']]
    result['tour_titles'] = [tour['title'] for tour in response['tours']] if 'tours' in response else response['title']
    result['tour_info'] = [tour['info'] for tour in response['tours']] if 'tours' in response else response['info']
    result['tour_editors'] = [tour['editors'] if tour['editors'] != response['editors'] else '' for
                              tour in response['tours']] if 'tours' in response else [response['editors']]
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
            soup = BeautifulSoup(urlopen(url_template.format(title), context=CONTEXT),
                                 'lxml-xml')
        else:
            soup = BeautifulSoup(urlopen('http://db.chgk.info/tour/xml', context=CONTEXT),
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
