from io import StringIO

from bs4 import BeautifulSoup
from selenium import webdriver

# doi = sys.argv[1]
doi = "10.1016/j.cell.2007.12.028"
# chrome = webdriver.PhantomJS()
# chrome.set_window_size(1120, 550)
options = webdriver.ChromeOptions()
options.add_argument("headless")
# https://blog.miguelgrinberg.com/post/using-headless-chrome-with-selenium
chrome = webdriver.Chrome(chrome_options=options)
chrome.get("http://doi.org/{}".format(doi))
# time.sleep(3.)
# chrome.save_screenshot('screen.png')
h = chrome.find_element_by_tag_name("html")
txt = h.get_attribute("outerHTML")

soup = BeautifulSoup(StringIO(txt), "lxml")
secs = soup.select("article div.Body section")
for sec in secs:
    print(sec)
