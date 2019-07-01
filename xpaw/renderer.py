# coding=utf-8

import asyncio
from threading import Thread

from selenium.webdriver import Chrome, ChromeOptions

from .http import HttpResponse, HttpHeaders


class ChromeRenderer:
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
        driver = Chrome(options=self.make_chrome_options(request))
        driver.set_page_load_timeout(request.timeout)
        driver.set_script_timeout(request.timeout)
        driver.implicitly_wait(request.timeout)
        try:
            driver.get(request.url)
            response = HttpResponse(driver.current_url, 200, body=driver.page_source.encode('utf-8'),
                                    headers=HttpHeaders(), request=request)
            loop.call_soon_threadsafe(lock.set_result, response)
        except Exception as e:
            loop.call_soon_threadsafe(lock.set_result, e)
        finally:
            driver.quit()

    @classmethod
    def make_chrome_options(cls, request):
        render_options = request.render if isinstance(request.render, dict) else {}
        chrome_options = ChromeOptions()
        chrome_options.add_argument('--headless')
        # anonymous
        chrome_options.add_argument('--incognito')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        prefs = {}
        if not render_options.get('show_images'):
            # disable images
            prefs.setdefault('profile.managed_default_content_settings.images', 2)
        if prefs:
            chrome_options.add_experimental_option('prefs', prefs)
        if 'mobile_emulation' in render_options:
            mobile_emulation = render_options['mobile_emulation']
            if not isinstance(mobile_emulation, dict):
                mobile_emulation = {'deviceName': 'iPhone 8'}
            chrome_options.add_experimental_option('mobileEmulation', mobile_emulation)
        return chrome_options
