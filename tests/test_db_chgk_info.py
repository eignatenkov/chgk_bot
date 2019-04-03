import unittest

from xml_tools import tournament_info, q_and_a


class TournamentInfoTestCase(unittest.TestCase):
    def test_happy_pass(self):
        t_url = 'kra-fm17'
        t_info = tournament_info(t_url)
        # for k, v in t_info.items():
        #     print(k, v)
        self.assertTrue(isinstance(t_info, dict))


class QAndATestCase(unittest.TestCase):
    def test_happy_pass(self):
        t_url = 'kritik17'
        tour = 2
        question = 4
        output = q_and_a(t_url, tour, question)
        print(output)
        true_output = {
            'question': 'Внимание, колонка!\n\n\xa0\xa0\xa0\xa0\n\n\xa0\xa0\xa0\xa0Доктор Джон Сноу был одним из первых ученых, который приложил руку к выявлению источников холеры. На розданном вам фото — необычный памятник, на котором можно увидеть результат простых действий, предпринятых Сноу. Что именно сделал Сноу 7 сентября 1854 года, чтобы прекратить распространение эпидемии в лондонском районе Брод-стрит?',
            'question_image': 'http://db.chgk.info/images/db/20170189.jpg',
            'answer': 'Распорядился снять ручку с колонки.',
            'comments': 'Обследовав больных холерой и узнав, где они живут, доктор выяснил, что эпидемия распространяется через загрязненную воду, и центр очага холеры — эта самая колонка. Сноу распорядился снять с нее ручку, и локальная эпидемия остановилась. В память об этом в честь Сноу установили колонку без ручки.',
            'pass_criteria': 'Снял / приказал снять ручку и прочее по смыслу с упоминанием ручки/рычага/вентиля.',
            'sources': 'http://medportal.ru/mednovosti/news/2017/04/07/446queencolera/',
            'authors': 'Алена Повышева (Санкт-Петербург)'}
        self.assertDictEqual(output, true_output)


if __name__ == '__main__':
    unittest.main()
