from webfaf.common.tests import SeleniumTest

class LongtermProblemsTest(SeleniumTest):
    def test_title(self):
        self.load('/problems/longterm/')
        self.assertIn('Long-term problems', self.title)

    def test_menu_entries(self):
        self.load('/problems/longterm/')
        menu_entries = self.find('nav li.active a')
        self.assertEqual(['Problems', 'Long-term Problems'],
            map(lambda x: x.text, menu_entries))
