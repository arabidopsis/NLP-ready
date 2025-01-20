from __future__ import annotations

from io import StringIO

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

# doi = sys.argv[1]
doi = "10.1016/j.cell.2007.12.028"
# chrome = webdriver.PhantomJS()
# chrome.set_window_size(1120, 550)
options = webdriver.ChromeOptions()
options.add_argument("headless")
# https://blog.miguelgrinberg.com/post/using-headless-chrome-with-selenium
chrome = webdriver.Chrome(options=options)
chrome.get(f"http://doi.org/{doi}")
# time.sleep(3.)
# chrome.save_screenshot('screen.png')
print(dir(chrome))
h = chrome.find_element(by=By.TAG_NAME, value="html")
txt = h.get_attribute("outerHTML")

soup = BeautifulSoup(StringIO(txt), "lxml")
secs = soup.select("article div.Body section")
for sec in secs:
    print(sec)
