import unittest

from rating_tools import find_team_by_name, get_tournament_results_by_id


class FindTeamByNameTestCase(unittest.TestCase):
    def test_happy_pass(self):
        pp_name = 'Понты Пилата'
        output = find_team_by_name(pp_name)
        self.assertTrue(set(output.keys()) == {'items', 'total_items', 'current_items'})
        self.assertTrue(int(output['total_items']) >= 7)
        output_team = output['items'][0]
        self.assertTrue(set(output_team.keys()) == {'idteam', 'name', 'town',
                                                    'region_name', 'country_name'})
        self.assertEqual(output_team['name'], pp_name)

    def test_team_not_found(self):
        crazy_name = '123321'
        output = find_team_by_name(crazy_name)
        self.assertTrue(set(output.keys()) == {'items', 'total_items', 'current_items'})
        self.assertEqual(output['total_items'], '0')


class GetTournamentResultsByIdTestCase(unittest.TestCase):
    def test_happy_pass(self):
        t_id = 4435
        output = get_tournament_results_by_id(t_id)
        self.assertEqual(len(output), 130)
        first_team = output[0]
        self.assertEqual(first_team['idteam'], '407', msg='results are not sorted by team id!')
        expected_first_team = {
            'idteam': '407',
            'current_name': 'Тачанка',
            'base_name': 'Тачанка',
            'position': '1.5',
            'questions_total': '27',
            'mask': '101111100111000101111001111111111111',
            'bonus_a': '2297',
            'diff_bonus': '62',
            'd_bonus_a': '2297',
            'bonus_b': '1487',
            'tech_rating': '5767',
            'predicted_position': '3',
            'd_bonus_b': '1487',
            'd_diff_bonus': '62',
            'included_in_rating': '1'}
        self.assertDictEqual(first_team, expected_first_team)

    def test_stress_test(self):
        bb_overall = 3780
        output = get_tournament_results_by_id(bb_overall)
        self.assertEqual(len(output), 1883)


if __name__ == '__main__':
    unittest.main()
