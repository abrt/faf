from webfaf.common.tests import SeleniumTest

class HotProblemsTest(SeleniumTest):
    def test_title(self):
        self.load('/problems/hot/')
        self.assertIn('Hot problems', self.title)

    def test_menu_entries(self):
        self.load('/problems/hot/')
        menu_entries = self.find('nav li.active a')
        self.assertEqual(['Problems', 'Hot Problems'],
            map(lambda x: x.text, menu_entries))
