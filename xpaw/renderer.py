# coding=utf-8

import asyncio
from threading import Thread
from collections import deque
import logging

from selenium.webdriver import Chrome, ChromeOptions

from .http import HttpResponse, HttpHeaders

log = logging.getLogger(__name__)


class ChromeRenderer:
    default_arguments = ['--headless', '--incognito', '--ignore-certificate-errors', '--ignore-ssl-errors',
                         '--disable-gpu', '--no-sandbox']
    default_prefs = {'profile.managed_default_content_settings.images': 2}

    def __init__(self, options=None):
        self.options = {'default': self.make_chrome_options()}
        if options:
            for k, v in options.items():
                self.options[k] = self.make_chrome_options(arguments=v.get('arguments'),
                                                           experimental_options=v.get('experimental_options'))
        self.available_drivers = {}
        for name in self.options.keys():
            self.available_drivers[name] = deque()

    async def fetch(self, request):
        lock = asyncio.Future()
        t = Thread(target=self._run_fetch_thread, args=(asyncio.get_event_loop(), lock, request))
        t.start()
        await lock
        result = lock.result()
        if isinstance(result, Exception):
            raise result
        return result

    def _run_fetch_thread(self, loop, lock, request):
        driver_instance = None
        try:
            driver_instance = self.get_driver_instance(request)
            driver = driver_instance.driver
            driver.get(request.url)
            response = HttpResponse(driver.current_url, 200, body=driver.page_source.encode('utf-8'),
                                    headers=HttpHeaders(), request=request)
            self.push_driver_instance(driver_instance)
            loop.call_soon_threadsafe(lock.set_result, response)
        except Exception as e:
            if driver_instance:
                driver_instance.destroy_driver()
            loop.call_soon_threadsafe(lock.set_result, e)

    def make_chrome_options(self, arguments=None, experimental_options=None):
        chrome_options = ChromeOptions()
        if arguments is None:
            arguments = []
        for a in self.default_arguments:
            if a not in arguments:
                arguments.append(a)
        for a in arguments:
            chrome_options.add_argument(a)
        if experimental_options is None:
            experimental_options = {}
        if 'prefs' not in experimental_options:
            experimental_options['prefs'] = self.default_prefs
        else:
            for k, v in self.default_prefs.items():
                experimental_options['prefs'].setdefault(k, v)
        for k, v in experimental_options.items():
            chrome_options.add_experimental_option(k, v)
        return chrome_options

    def create_driver_instance(self, name):
        driver = Chrome(options=self.options[name])
        self._set_navigator(driver)
        return DriverInstance(name, driver)

    def _set_navigator(self, driver):
        source = """Object.defineProperties(navigator,{webdriver:{get:()=> undefined}});"""
        add_script_to_evaluate_on_new_document(source, driver)

    def get_driver_name(self, request):
        if isinstance(request.render, str):
            name = request.render
        else:
            name = 'default'
        return name

    def get_driver_instance(self, request):
        name = self.get_driver_name(request)
        try:
            driver_instance = self.available_drivers[name].popleft()
        except IndexError:
            driver_instance = self.create_driver_instance(name)
        driver = driver_instance.driver
        try:
            driver.set_page_load_timeout(request.timeout)
            driver.set_script_timeout(request.timeout)
            driver.implicitly_wait(request.timeout)
        except Exception:
            driver_instance.destroy_driver()
            raise
        return driver_instance

    def reset_driver(self, driver):
        driver.execute_script('window.open();')
        handles = driver.window_handles
        for i in range(0, len(handles) - 1):
            driver.switch_to.window(handles[i])
            driver.close()
        driver.switch_to.window(handles[-1])

    def push_driver_instance(self, driver_instance):
        try:
            self.reset_driver(driver_instance.driver)
            self.available_drivers[driver_instance.name].append(driver_instance)
        except Exception:
            driver_instance.destroy_driver()
            raise

    def close(self):
        for q in self.available_drivers.values():
            while True:
                try:
                    driver_instance = q.popleft()
                except IndexError:
                    break
                else:
                    driver_instance.destroy_driver()


def add_script_to_evaluate_on_new_document(source, driver):
    return driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': source})


class DriverInstance:
    def __init__(self, name, driver):
        self.name = name
        self.driver = driver

    def destroy_driver(self):
        try:
            self.driver.quit()
        except Exception as e:
            log.warning('Cannot quit driver: %s', e)
