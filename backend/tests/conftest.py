"""
pytest configuration and fixtures for Selenium testing.
"""
import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


@pytest.fixture(scope="session")
def chrome_options():
    """Chrome browser options for testing."""
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    return options


@pytest.fixture(scope="session")
def firefox_options():
    """Firefox browser options for testing."""
    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    return options


@pytest.fixture(scope="session")
def chrome_driver_path():
    """Get Chrome driver path using webdriver-manager."""
    return ChromeDriverManager().install()


@pytest.fixture(scope="session")
def firefox_driver_path():
    """Get Firefox driver path using webdriver-manager."""
    return GeckoDriverManager().install()


@pytest.fixture
def chrome_driver(chrome_options, chrome_driver_path):
    """Chrome WebDriver instance."""
    service = ChromeService(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture
def firefox_driver(firefox_options, firefox_driver_path):
    """Firefox WebDriver instance."""
    service = FirefoxService(firefox_driver_path)
    driver = webdriver.Firefox(service=service, options=firefox_options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture
def browser_driver(request, chrome_driver, firefox_driver):
    """Parameterized browser driver fixture."""
    browser = getattr(request, 'param', 'chrome')
    if browser == 'firefox':
        return firefox_driver
    return chrome_driver


@pytest.fixture
def dual_chrome_drivers(chrome_options, chrome_driver_path):
    """Two Chrome WebDriver instances for multiplayer testing."""
    service = ChromeService(chrome_driver_path)
    
    # Create two separate Chrome instances
    driver1 = webdriver.Chrome(service=service, options=chrome_options)
    driver2 = webdriver.Chrome(service=service, options=chrome_options)
    
    driver1.implicitly_wait(10)
    driver2.implicitly_wait(10)
    
    yield driver1, driver2
    
    driver1.quit()
    driver2.quit()


@pytest.fixture
def live_server_url(live_server):
    """Get the live server URL."""
    return live_server.url


# Database settings for testing
@pytest.fixture(scope="session")
def django_db_setup():
    """Configure test database."""
    pass


# Override settings for testing
@pytest.fixture(autouse=True)
def test_settings():
    """Override Django settings for testing."""
    with override_settings(
        DEBUG=False,
        STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
        # Ensure consistent database for all test browsers
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
                'TEST': {
                    'NAME': ':memory:',
                },
            }
        }
    ):
        yield