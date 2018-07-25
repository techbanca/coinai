import threading, codecs, os
import requests, datetime
from bs4 import BeautifulSoup

domain_url = 'https://coinmarketcap.com'
down_url = 'https://coinmarketcap.com/zh/all/views/all/'
search_url = "historical-data/?start=%s&end=%s"

current_path = os.path.realpath(__file__)
output_path = current_path.split("crawler")[0] + "data/"

def get_one_page(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content

def bs4_paraser(html):
    
    all_value = []
    value = {}
    soup = BeautifulSoup(html, 'html.parser')
    all_a_item = soup.find_all(name="a", attrs={"class": "currency-name-container"})
    for r in all_a_item:
        url = r['href']
        value['url'] = url
        all_value.append(value)
        value = {}
    return all_value


def down_paraser_item(pre_item):

    value_dict = {}
    now = datetime.datetime.now()
    delta = datetime.timedelta(days=-365)
    n_days = now + delta
    start_day = n_days.strftime('%Y%m%d')
    end_day = now.strftime('%Y%m%d')
    bitcoin_name = pre_item["url"].split("/")[-2]
    value_dict[bitcoin_name] = ""
    
    url = domain_url + pre_item["url"] + search_url%(start_day, end_day)
    html = get_one_page(url)
    
    soup = BeautifulSoup(html, 'html.parser')
    all_div_item = soup.find_all(name="div", attrs={"class": "tab-header"})
    
    for div in all_div_item:
        trs = div.find_all(name="tr", attrs={"class": "text-right"})
        for tr in trs:
            tds = tr.find_all(name="td")
            
            date_str = tds[0].text[:4] + "-" + tds[0].text[5:6] + "-" + tds[0].text[8:-1]
            td_str = date_str + "," + tds[4].text + "\n"
            value_dict[bitcoin_name] += td_str
            
    file = codecs.open(output_path + '^%s.csv'%bitcoin_name, 'w', encoding='utf-8')
    file.write(value_dict[bitcoin_name])

def main():

    html = get_one_page(down_url)
    all_value = bs4_paraser(html)
    pre_20_value = all_value[:20]
    ss = ""
    for d in pre_20_value:
        ss += "^"+d['url'].split("/")[-2]+", "
    for pre_item in pre_20_value:
        t = threading.Thread(target=down_paraser_item, args=(pre_item,))
        t.start()
        t.join()

if __name__ == '__main__':
    main()
