from bs4 import BeautifulSoup
import requests
import sqlite3
import json

def get_populations(): #Gets Population for each state 
    url = "https://en.wikipedia.org/wiki/List_of_United_States_cities_by_population"

    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    table = soup.find('table', class_='sortable wikitable sticky-header-multi static-row-numbers sort-under col1left col2center') 

    rows = table.find_all('tr')

    city_data = {}

    for row in rows[1:]: 
        cols = row.find_all('td')
        if len(cols) >= 4: #used ChatGPT
            city_tag = cols[0].find('a')
            city = city_tag.get('title').strip().split(',')[0]
            state = cols[1].text.strip()
            population = int(cols[3].text.strip().replace(',', ''))
            longlat_full = cols[9].text.strip().split(' / ')
            cords = longlat_full[-1].split()
            long = float(cords[0].replace(';', ''))
            lat = float(cords[1].replace('\ufeff', ''))
        
            city_data[f"{city}, {state}"] = {
                "population": population,
                "coordinates": {
                    "longitude": long,
                    "latitude": lat
            }
        }

    print(city_data)

get_populations()