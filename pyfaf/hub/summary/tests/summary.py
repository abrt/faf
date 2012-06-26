from pyfaf.hub.common.tests import SeleniumTest

class SummaryTest(SeleniumTest):
    def test_title(self):
        self.load('/summary/')
        self.assertIn('Summary', self.title)

    def test_menu_entry(self):
        self.load('/summary/')
        menu_entry = self.find('nav li.active a')
        self.assertEqual(menu_entry.text, 'Summary')

class SummaryGraphTest(SeleniumTest):
    def test_graph_labels(self):
        self.load('/summary/')
        legend = self.find('#placeholder .legend').text
        self.assertIn('Fedora 16', legend)
        self.assertIn('Fedora 17', legend)
        self.assertIn('RHEL 7', legend)
        self.assertIn('openSUSE', legend)

    def test_graph_present(self):
        self.load('/summary/')
        self.find('canvas.base')
        self.find('canvas.overlay')
