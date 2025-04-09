from bs4 import BeautifulSoup
import requests
import sqlite3
import os

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
        
            city_data[f"{city}, {state}"] = population

    return city_data

def create_database(db_name): #Creates database
    
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/" + db_name)
    cur = conn.cursor()
    return cur, conn

def create_states_table(data, cur, conn): #Creates States table
    states = []
    for city, population in data.items():
        state = city.split(',')[1]
        if state not in states:
            states.append(state)

    cur.execute("CREATE TABLE IF NOT EXISTS States (id INTEGER PRIMARY KEY, state TEXT)")
    for i in range(len(states)):
        cur.execute("INSERT OR IGNORE INTO States (id, state) VALUES (?,?)", (i, states[i]))
    conn.commit()

def create_citybike_table(data, cur, conn): #Creates City_Bike Table
    cur.execute('DROP TABLE IF EXISTS City_Bike')
    cur.execute('''CREATE TABLE IF NOT EXISTS City_Bike (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                city TEXT, state_id INTEGER, long INTEGER, lat INTEGER, city_bike INTEGER, 
                pop INTEGER, weather INTEGER)''')
    
    for city, population in data.items():
        city_name = city.split(',')[0]
        state = city.split(',')[1]
        cur.execute("SELECT id FROM States WHERE state = ?", (state,))
        state_id = cur.fetchone()[0]
        long = None
        lat = None
        city_bike = None
        pop = data[city]
        weather = None
        
        cur.execute('''INSERT INTO City_Bike (city, state_id, long, lat, city_bike, pop, weather) 
                    VALUES (?,?,?,?,?,?,?)''',
                    (city_name,state_id,long,lat,city_bike, pop, weather))
        
        conn.commit()

data = get_populations()
cur, conn = create_database("citybike.db")
create_states_table(data, cur, conn)
create_citybike_table(data, cur, conn)


