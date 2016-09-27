import requests
from urllib.request import urlopen
import json
import datetime
import dateutil.parser
from bs4 import BeautifulSoup
import codecs

with requests.Session() as session:
    session.get("http://rating.chgk.info")


def api_call(url):
    # with requests.Session() as session:
    #     session.get("http://rating.chgk.info")
    response = session.get(url)
    return json.loads(response.content.decode('UTF-8'))


def find_team_by_name(name):
    url = 'http://rating.chgk.info/api/teams.json/search?name={}'.format(name)
    return api_call(url)


def get_tournament_results_by_id(tournament_id):
    url = 'http://rating.chgk.info/api/tournaments/{}/list.json'.format(
        tournament_id)
    return api_call(url)


def get_tournaments():
    url = 'http://rating.chgk.info/api/tournaments.json'
    return api_call(url)


def get_weekend_tournaments(sunday=None):
    if not sunday:
        today = datetime.date.today()
        sunday = today - datetime.timedelta(days=today.weekday()+1)

    def is_tournament_on_weekend(tournament, sunday_date):
        begin = dateutil.parser.parse(tournament['date_start']).date()
        end = dateutil.parser.parse(tournament['date_end']).date()
        return begin <= sunday_date and \
               end >= sunday_date - datetime.timedelta(days=1)

    return [item for item in get_tournaments()['items'] if
            is_tournament_on_weekend(item, sunday)]


def get_team_info(team_id):
    url = 'http://rating.chgk.info/api/teams/{}'.format(team_id)
    return api_call(url)[0]


def get_team_rating(team_id, release_id=None, last=False):
    if release_id:
        url = 'http://rating.chgk.info/api/teams/{0}/rating/{1}.json'.format(
            team_id, release_id)
    elif last:
        url = 'http://rating.chgk.info/api/teams/{}/rating/b.json'.format(
            team_id)
    else:
        url = 'http://rating.chgk.info/api/teams/{}/rating.json'.format(team_id)
    return api_call(url)


def get_teams_by_town(town):
    url = 'http://rating.chgk.info/api/teams.json/search?town={}'.format(town)
    raw_result = api_call(url)
    return {item['idteam']: item['name'] for item in raw_result['items']}


def get_player_info(player_id):
    url = 'http://rating.chgk.info/api/players/{}.json'.format(player_id)
    return api_call(url)


def get_teams_results_on_tournaments(teams, t_id):
    teams_set = set(teams)

    def add_title(team_info):
        team_info['name'] = teams[team_info['idteam']]
        return team_info

    return [add_title(item) for item in get_tournament_results_by_id(t_id)
            if item['idteam'] in teams_set]


def get_town_results_on_tournament(town, t_id):
    town_teams = get_teams_by_town(town)
    return get_teams_results_on_tournaments(town_teams, t_id)


def get_town_results_on_weekend(town, sunday=None):
    t_list = get_weekend_tournaments(sunday)
    result = {}

    for tnmnt in t_list:
        t_results = get_town_results_on_tournament(town, tnmnt['idtournament'])
        if len(t_results) > 0:
            result[tnmnt['name']] = t_results

    return result


def get_towns_by_country(country):
    enc_country = codecs.encode(country, encoding='cp1251')
    url = 'http://rating.chgk.info/geo.php?layout=town_list&country={}'.format(
        str(enc_country).strip('b\'').replace('\\x', '%')
    )
    with urlopen(url) as towns:
        page = BeautifulSoup(towns, 'html.parser')
    return [item.text.strip() for index, item in enumerate(
        page.tbody.find_all('a')) if not index % 4]


def get_country_results_on_tournament(country, t_id):
    country_teams = dict()
    for town in get_towns_by_country(country):
        country_teams.update(get_teams_by_town(town))
    return get_teams_results_on_tournaments(country_teams, t_id)

if __name__ == '__main__':
    # print(get_team_info(3166))
    # print(get_weekend_tournaments(datetime.date(2016,9,18)))
    # print(get_town_results_on_weekend('Берлин'))
    # print(get_town_results_on_tournament('Берлин', 3719))
    # print(get_teams_by_town('Берлин'))
    for item in sorted(get_country_results_on_tournament('Германия', 3792),
                       key=lambda x: float(x.get('position', 0))):
        print(item)

