from pyfaf.hub.common.tests import SeleniumTest

class ReportDetailTest(SeleniumTest):
    def test_title(self):
        self.load('/reports/list/')
        reports = self.find('article table tr')
        report = reports[10]
        link = self.find('td a', report)
        target = link.text
        self.click(link)
        self.assertIn('Report #%s' % target, self.title)

    def test_menu_entries(self):
        self.load('/reports/%d/' % 50)
        menu_entries = self.find('nav li.active a')
        self.assertEqual(['Reports', 'Report #50'],
            map(lambda x: x.text, menu_entries))
