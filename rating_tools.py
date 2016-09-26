import requests
import json


def api_call(url):
    with requests.Session() as session:
        session.get("http://rating.chgk.info")
        response = session.get(url)
        return json.loads(response.content.decode('UTF-8'))


def get_tournament_results_by_id(tournament_id):
    url = 'http://rating.chgk.info/api/tournaments/{}/list.json'.format(
        tournament_id)
    return api_call(url)


def get_tournaments():
    url = 'http://rating.chgk.info/api/tournaments.json'
    return api_call(url)

if __name__ == '__main__':
    print(get_tournaments())

