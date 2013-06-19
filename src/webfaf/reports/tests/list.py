from webfaf.common.tests import SeleniumTest

class ReportsListTest(SeleniumTest):
    def test_title(self):
        self.load('/reports/list/')
        self.assertIn('Report list', self.title)

    def test_menu_entries(self):
        self.load('/reports/list')
        menu_entries = self.find('nav li.active a')
        self.assertEqual(['Reports', 'List'],
            map(lambda x: x.text, menu_entries))

    def test_entries(self):
        self.load('/reports/list')
        entries = self.find('article table tr')
        self.assertGreater(len(entries), 50)
