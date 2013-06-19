from webfaf.common.tests import SeleniumTest

class ReportsSummaryTest(SeleniumTest):
    def test_title(self):
        self.load('/reports/')
        self.assertIn('Reports summary', self.title)

    def test_menu_entries(self):
        self.load('/reports/')
        menu_entries = self.find('nav li.active a')
        self.assertEqual(['Reports', 'Overview'],
            map(lambda x: x.text, menu_entries))

class ReportsGraphTest(SeleniumTest):
    def test_graph_labels(self):
        self.load('/reports/')
        legend = self.find('#placeholder .legend').text
        self.assertIn('Fedora 16', legend)
        self.assertIn('Fedora 17', legend)
        self.assertIn('RHEL 7', legend)
        self.assertIn('openSUSE', legend)

    def test_graph_present(self):
        self.load('/reports/')
        self.find('canvas.base')
        self.find('canvas.overlay')
