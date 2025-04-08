from bs4 import BeautifulSoup
import requests
import sqlite3
import json

# SCRAPING POPULATION DATA 

url = "https://en.wikipedia.org/wiki/List_of_United_States_cities_by_population"

r = requests.get(url)
soup = BeautifulSoup(r.content, 'html.parser')

table = soup.find('table', class_='sortable wikitable sticky-header-multi static-row-numbers sort-under col1left col2center') 

rows = table.find_all('tr')

city_data = {}

for row in rows[1:]: 
    cols = row.find_all('td')
    if len(cols) >= 4:
        city_tag = cols[0].find('a')
        city = city_tag.get('title').strip()
        state = cols[1].text.strip()
        population = int(cols[3].text.strip().replace(',', ''))
        longlat_full = cols[9].text.strip().split(' / ')
        cords = longlat_full[-1].split()
        long = float(cords[0].replace(';', ''))
        lat = float(cords[1].replace('\ufeff', ''))
        
        city_data[city] = {
            "population": population,
            "coordinates": {
                "longitude": long,
                "latitude": lat
            }
        }

with open("city_info.json", "w") as f:
    json.dump(city_data, f, indent=4)

print(json.dumps(city_data, indent=4))

# IMPORTING DATA INTO TABLE


