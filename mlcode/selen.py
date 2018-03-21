from selenium import webdriver
from bs4 import BeautifulSoup
from io import StringIO
import sys
import time
#doi = sys.argv[1]
doi = '10.1016/j.cell.2007.12.028'
# chrome = webdriver.PhantomJS()
# chrome.set_window_size(1120, 550)
chrome = webdriver.Chrome()
chrome.get('http://doi.org/{}'.format(doi))
# time.sleep(3.)
# chrome.save_screenshot('screen.png')
h = chrome.find_element_by_tag_name('html')
txt = h.get_attribute('outerHTML')

soup = BeautifulSoup(StringIO(txt), 'lxml')
secs = soup.select('article div.Body section')
for sec in secs:
    print(sec)

