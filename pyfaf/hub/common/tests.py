from django.conf import settings
from django.test import LiveServerTestCase
from django.test.utils import override_settings
from django.utils.unittest import SkipTest

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait

@override_settings(DEBUG=True)
class SeleniumTest(LiveServerTestCase):
    ''' Class handling configuration and setup-up of selenium
    tests. Providing few shorthand functions for simplifying
    common tasks.

    Configuration:
      settings.SELENIUM_BROWSER - one of the supported browsers
      settings.SELENIUM_TIMEOUT - page load time-out
      settings.SELENIUM_REMOTE  - True/False, use remote selenium server
      settings.SELENIUM_HUB_URL - selenium server url (only for remote testing)

    '''

    def get(self, url):
        ''' Load url in the browser window. '''
        self.driver.get('%s%s' % (self.live_server_url, url))

    def click(self, element):
        element.click()
        self.body = self.wait_for_body()
        self.set_shortcuts()

    def wait_for_body(self):
        ''' Wait for body tag to be loaded, return body element. '''
        WebDriverWait(self.driver, self.timeout).until(
            lambda driver: driver.find_element_by_tag_name('body'))
        return self.driver.find_element_by_tag_name('body')

    def load(self, url):
        ''' Call get & wait_for_body on given url. For easy access also store
        body, title and page as attributes of current class.
        '''
        self.get(url)
        self.body = self.wait_for_body()
        self.set_shortcuts()

    def find(self, expression, element=None):
        if not element:
            element = self.body
        elems = element.find_elements_by_css_selector(expression)
        if len(elems) == 1:
            return elems[0]
        return elems

    def set_shortcuts(self):
        self.title = self.driver.title
        self.page = self.driver.page_source

    @classmethod
    def setUpClass(cls):
        ''' Setup selenium driver according to the configuration. '''
        if not hasattr(settings, 'SELENIUM_BROWSER'):
            raise SkipTest('Selenium not configured')

        driver_name = settings.SELENIUM_BROWSER
        cls.timeout = settings.SELENIUM_TIMEOUT
        cls.remote = settings.SELENIUM_REMOTE

        if cls.remote:
            cls.url = settings.SELENIUM_HUB_URL
            if hasattr(webdriver.DesiredCapabilities,
                    driver_name.upper()):
               cls.caps = getattr(webdriver.DesiredCapabilities,
                    driver_name.upper())
            else:
                raise SkipTest('Selenium capabilities for "%s" not '
                'found.' % driver_name)

        else:
            if hasattr(webdriver, driver_name):
                driver = getattr(webdriver, driver_name)
            else:
                raise SkipTest('Selenium webdriver "%s" not installed or not'
                'operational.' % driver_name)

        if cls.remote:
            cls.driver = webdriver.Remote(cls.url, cls.caps)
        else:
            cls.driver = driver.webdriver.WebDriver()
        super(SeleniumTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        ''' Quit selenium driver. '''
        super(SeleniumTest, cls).tearDownClass()
        cls.driver.quit()
