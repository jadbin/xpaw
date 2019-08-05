# coding=utf-8

from threading import Thread, Semaphore
from collections import deque

from selenium.webdriver import Chrome, ChromeOptions

from benchmarks.utils import log_time

TEST_URL = 'https://www.baidu.com/'


def make_chrome_options():
    chrome_options = ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--incognito')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    prefs = {'profile.managed_default_content_settings.images': 2}
    chrome_options.add_experimental_option('prefs', prefs)
    return chrome_options


def create_chrome_driver():
    driver = Chrome(options=make_chrome_options())
    driver.set_page_load_timeout(10)
    driver.set_script_timeout(10)
    driver.implicitly_wait(10)
    return driver


def reopen_chrome_thread(sem):
    driver = None
    try:
        driver = create_chrome_driver()
        driver.get(TEST_URL)
    except Exception as e:
        print(e)
    finally:
        if driver:
            driver.quit()
        sem.release()


@log_time('reopen chrome')
def reopen_chrome(times, clients):
    sem = Semaphore(clients)
    for i in range(times):
        sem.acquire()
        t = Thread(target=reopen_chrome_thread, args=(sem,))
        t.start()


class DriverManager:
    def __init__(self):
        self.available_drivers = deque()

    def get_driver(self):
        try:
            driver = self.available_drivers.popleft()
        except IndexError:
            driver = create_chrome_driver()
        return driver

    def push_driver(self, driver):
        self.available_drivers.append(driver)

    def close(self):
        try:
            while True:
                driver = self.available_drivers.popleft()
                try:
                    driver.quit()
                except Exception:
                    pass
        except IndexError:
            pass


def reset_driver(driver):
    assert isinstance(driver, Chrome)
    driver.execute_script('window.open();')
    handles = driver.window_handles
    for i in range(0, len(handles) - 1):
        driver.switch_to.window(handles[i])
        driver.close()
    driver.switch_to.window(handles[-1])


def manage_chrome_tabs_thread(sem, manager):
    driver = None
    try:
        driver = manager.get_driver()
        driver.get(TEST_URL)
        reset_driver(driver)
    except Exception as e:
        print(e)
        if driver is not None:
            driver.quit()
            driver = None
    finally:
        if driver is not None:
            manager.push_driver(driver)
        sem.release()


@log_time('manage chrome tabs')
def manage_chrome_tabs(times, clients):
    sem = Semaphore(clients)
    manager = DriverManager()
    for i in range(times):
        sem.acquire()
        t = Thread(target=manage_chrome_tabs_thread, args=(sem, manager))
        t.start()
    manager.close()


if __name__ == '__main__':
    print('------------------------')
    print('Reopen Chrome every time')
    print('------------------------')
    reopen_chrome(times=50, clients=5)
    print('------------------')
    print('Manage Chrome tabs')
    print('------------------')
    manage_chrome_tabs(times=50, clients=5)
