import selenium
from selenium import webdriver
from platform import platform
import os
from selenium.webdriver.common.by import By
from diffenator.utils import gen_gifs


class ScreenShotter:
    """Use selenium to take screenshots from local browsers"""
    def __init__(self, width=1280):

        self.browsers = self._get_browsers()
        self.width = width

    def _file_prefix(self, browser):
        meta = browser.capabilities
        plat = platform()
        browser = meta['browserName']
        browser_version = meta['browserVersion']
        return f'{plat}_{browser}_{browser_version}'.replace(" ", "-")

    def take(self, url, dst_dir):
        for browser in self.browsers:
            browser.get(url)

            try:
                diff_toggle = browser.find_element(By.ID, "font-toggle")
            except selenium.common.exceptions.NoSuchElementException:
                diff_toggle = None
            
            if diff_toggle:
                self.take_gif(url, dst_dir)
            else:
                self.take_png(url, dst_dir)

    def take_png(self, url, dst_dir, javascript=""):
        for browser in self.browsers:
            file_prefix = self._file_prefix(browser)
            filename = os.path.join(dst_dir, f"{file_prefix}.png")
            browser.set_window_size(
                self.width,
                1000
            )
            browser.get(url)
            if javascript:
                browser.execute_script(javascript)
            # recalc since image size since we now know the height
            body_el = browser.find_element(By.TAG_NAME, "html")
            browser.set_window_size(
                self.width,
                body_el.size['height']
            )
            browser.save_screenshot(filename)
    
    def take_gif(self, url, dst_dir):
        before_fp = os.path.join(dst_dir, "before")
        if not os.path.exists(before_fp):
            os.mkdir(before_fp)

        after_fp = os.path.join(dst_dir, "after")
        if not os.path.exists(after_fp):
            os.mkdir(after_fp)

        self.take_png(url, before_fp)
        self.take_png(url, after_fp, javascript="switchFonts();")
        gen_gifs(before_fp, after_fp, dst_dir)

    def set_width(self, width):
        # we don't care about setting height since we will always return a
        # full height screenshot
        self.width = width

    def _get_browsers(self):
        """Determine which browsers we can screenshot which exist on the system"""
        # We can add more webdrivers if needed. Let's focus on these first
        supported = ["Chrome", "Firefox", "Safari"]
        has = []
        driver = webdriver
        for browser in supported:
            try:
                # TODO customise more browsers. We should aim for at least Safari and FF
                if browser == "Chrome":
                    # Using headless mode enables us to set the window size
                    # to any arbitrary value which means we can use to capture
                    # the full size of the body elem
                    options = webdriver.ChromeOptions()
                    options.add_argument("--headless")
                    options.add_argument("--hide-scrollbars")
                    browser_driver = getattr(driver, browser)(options=options)
                elif browser == "Firefox":
                    options = webdriver.FirefoxOptions()
                    options.add_argument("--headless")
                    options.add_argument("--hide-scrollbars")
                    browser_driver = getattr(driver, browser)(options=options)
                else:
                    browser_driver = getattr(driver, browser)()
                has.append(browser_driver)
            except:
                pass
        return has

    def __del__(self):
        for browser in self.browsers:
            browser.quit()