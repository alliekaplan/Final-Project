from bs4 import BeautifulSoup
import requests
import sqlite3
import os
import json

#MAYAS:

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
            lat = float(cords[0].replace(';', ''))
            long = float(cords[1].replace('\ufeff', ''))
        
            city_data[f"{city}, {state}"] = {
            "population": population,
            "longitude": long,
            "latitude": lat
        }

    return city_data

def create_database(db_name): #Creates database
    
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/" + db_name)
    cur = conn.cursor()
    return cur, conn

def create_states_table(data, cur, conn): #Creates States table
    states = []
    for city, info in data.items():
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
                city TEXT, state_id INTEGER, long REAL, lat REAL, city_bike INTEGER, 
                pop INTEGER, weather INTEGER)''')
    for city, info in data.items():
        city_name = city.split(',')[0]
        state = city.split(',')[1]
        cur.execute("SELECT id FROM States WHERE state = ?", (state,))
        state_id = cur.fetchone()[0]
        long = info["longitude"]
        lat = info["latitude"]
        city_bike = None
        pop = info["population"]
        weather = None
        
        cur.execute('''INSERT INTO City_Bike (city, state_id, long, lat, city_bike, pop, weather) 
                    VALUES (?,?,?,?,?,?,?)''',
                    (city_name,state_id,long,lat,city_bike, pop, weather))
        
        conn.commit()

#ALLIES:

def city_bikes():
    networks = requests.get("http://api.citybik.es/v2/networks").json()
    #print(networks)
    if "networks" not in networks:
       print("Too many requests")
       return None
    networks = networks["networks"]
    us_networks = [n for n in networks if n['location']['country'] == 'US'] #get US cities only
    bike_availability = {}

    #get the number of available bikes
    for net in us_networks:
        network_id = net['id']
        city = net['location']['city']
        if city == "New York, NY":
            city = "New York City, NY"
        url = f"http://api.citybik.es/v2/networks/{network_id}"
        data = requests.get(url).json()
        #print(data)
        stations = data['network']['stations']
        #print(stations)
        total_bikes = 0
        for station in stations:
            free = station.get('free_bikes') or 0
            empty = station.get('empty_slots') or 0
            total_capacity = free + empty
            total_bikes += total_capacity
        bike_availability[city] = total_bikes

    with open("city_bike_data.json", "w") as f:
        json.dump(bike_availability, f, indent=4)

    return bike_availability

def add_city_bikes(bike_data,cur,conn):
    for city, bike_data in bike_data.items():
        city_name = city.split(',')[0]
        bike_number = bike_data
        cur.execute('''UPDATE City_Bike
                    SET city_bike = ?
                    WHERE city = ? ''', (bike_number, city_name))

    conn.commit()

#SAMYS:

def get_temperature(latitude, longitude):
    headers = {
        'User-Agent': 'MyWeatherApp (mayagordon6@gmail.com)'
    }

    weather_url = f"https://api.weather.gov/points/{latitude},{longitude}"
    response = requests.get(weather_url, headers=headers)

    if response.status_code != 200:
        print("Could not load data")
        return None

    data = response.json()
    forecast_url = data['properties']['forecast']
    forecast_response = requests.get(forecast_url, headers=headers)
    forecast_data = forecast_response.json()
    
    current_weather = forecast_data['properties']['periods'][0]
    temperature = current_weather['temperature']
    name = current_weather['name']
    
    # Step 8: Print and return the weather
    #print(f"{name}: {temperature}")
    return temperature

def get_weather(data):
    weather_info = {}
    for city, info in data.items():
        long = info["longitude"]
        lat = info["latitude"]
        weather_info[city] = get_temperature(lat, long)
    print(weather_info)


data = get_populations()
cur, conn = create_database("citybike.db")
create_states_table(data, cur, conn)
create_citybike_table(data, cur, conn)
get_weather(data)
bike_data = city_bikes()
if bike_data is not None:
    add_city_bikes(bike_data,cur,conn) 
