# coding=utf-8

import asyncio
from asyncio import Semaphore
from threading import Thread
from multiprocessing import cpu_count

from selenium.webdriver import Chrome, ChromeOptions

from .http import HttpResponse, HttpHeaders


class ChromeRenderer:
    def __init__(self, cores=None):
        if cores is None:
            cores = 4 * cpu_count()
        self._cores = cores
        self._cores_semaphore = Semaphore(cores)

    async def fetch(self, request):
        async with self._cores_semaphore:
            lock = asyncio.Future()
            t = Thread(target=self._run_fetch_thread, args=(asyncio.get_event_loop(), lock, request))
            t.start()
            await lock
            result = lock.result()
            if isinstance(result, Exception):
                raise result
            return result

    def _run_fetch_thread(self, loop, lock, request):
        driver = Chrome(options=self._make_chrome_options())
        driver.set_page_load_timeout(request.timeout)
        driver.set_script_timeout(request.timeout)
        driver.implicitly_wait(request.timeout)
        try:
            driver.get(request.url)
            if request.on_ready is not None:
                loop.call_soon_threadsafe(request.on_ready, driver)
            response = HttpResponse(driver.current_url, 200, body=driver.page_source.encode('utf-8'),
                                    headers=HttpHeaders(), request=request)
            loop.call_soon_threadsafe(lock.set_result, response)
        except Exception as e:
            loop.call_soon_threadsafe(lock.set_result, e)
        finally:
            driver.quit()

    def _make_chrome_options(self):
        chrome_options = ChromeOptions()
        # disable images
        prefs = {'profile.managed_default_content_settings.images': 2}
        chrome_options.add_experimental_option('prefs', prefs)
        chrome_options.add_argument('--headless')
        # anonymous
        chrome_options.add_argument('--incognito')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        return chrome_options
