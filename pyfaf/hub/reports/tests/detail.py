from pyfaf.hub.common.tests import SeleniumTest

class ReportDetailTest(SeleniumTest):
    def test_title(self):
        self.load('/reports/%d/' % 50)
        self.assertIn('Report #50', self.title)

    def test_menu_entries(self):
        self.load('/reports/%d/' % 50)
        menu_entries = self.find('nav li.active a')
        self.assertEqual(['Reports', 'Report #50'],
            map(lambda x: x.text, menu_entries))
