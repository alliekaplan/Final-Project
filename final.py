from bs4 import BeautifulSoup
import requests
import sqlite3
import os
import json
import matplotlib
import matplotlib.pyplot as plt

#MAYA'S:
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

#ALLIE'S:
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

#MAKE GRAPH FOR AVERAGE CITY BIKES PER STATE - Maya and Allie
#Step 1: Load data in database
def add_city_bikes(bike_data,cur,conn): #Used ChatGPT to help the function run when the API hits too many requests
    if isinstance(bike_data, dict):
        for city, bike_number in bike_data.items():
            city_name = city.split(',')[0]  
            cur.execute('''UPDATE City_Bike
                        SET city_bike = ?
                        WHERE city = ? ''', (bike_number, city_name))
            
    elif isinstance(bike_data, str) and os.path.isfile(bike_data):
        with open(bike_data, "r") as f:
            bike_data = json.load(f)  

        for city, bike_number in bike_data.items():
            city_name = city.split(',')[0]  
            cur.execute('''UPDATE City_Bike
                        SET city_bike = ?
                        WHERE city = ? ''', (bike_number, city_name))

    conn.commit()

#Step 2: Join tables and calculate AVG
def avg_bikes_by_state(cur, conn): #Used ChatGPT to help use SQLlite AVG() function
    cur.execute('''
        SELECT States.state, AVG(City_Bike.city_bike) AS avg_bikes
        FROM City_Bike
        JOIN States ON City_Bike.state_id = States.id
        GROUP BY States.state
    ''')

    return cur.fetchall()

#Step 3: Make Graph
def avg_bike_by_state_graph(cur, conn):
    data = avg_bikes_by_state(cur, conn)
    states = []
    avgs = []
    for state, avg in data:
        states.append(state)
        if avg == None:
            avg = 0
            avgs.append(avg)
        else:
            avgs.append(avg)
    plt.figure(figsize=(10, 5))
    plt.bar(states, avgs, color='blue')
    plt.xlabel('States')
    plt.ylabel('Average Number of City Bikes')
    plt.title('Average City Bikes Per State')
    plt.xticks(rotation=90)
    plt.show()

#MAKE GRAPH FOR AVERAGE POP PER STATES W/ BIKES - Maya and Allie
#Step 1: JOIN tables and calculate AVG
def avg_pop_per_state(cur, conn):
    cur.execute('''SELECT States.state, AVG(City_Bike.pop) AS avg_pop
                FROM City_Bike
                JOIN States on City_Bike.state_id = States.id
                WHERE City_Bike.city_bike IS NOT NULL
                GROUP BY States.state''')

    return cur.fetchall()

#Step 2: Make Graph
def avg_pop_per_state_graph(cur, conn):
    data = avg_pop_per_state(cur, conn)
    states = []
    pops = []
    for state, pop in data:
        states.append(state)
        pops.append(pop)
    plt.figure(figsize=(10, 5))
    plt.bar(states, pops, color='blue')
    plt.xlabel('States')
    plt.ylabel('Average Population')
    plt.title('Average Population Per State with City Bikes')
    plt.xticks(rotation=90)
    plt.show()

#MAKE GRAPH FOR AVG POPULATION BY NUMBER OF BIKES - Maya and Allie
#Step 1: JOIN tables and calculate AVG
def avg_pop_and_bikes_per_state(cur, conn):
    cur.execute('''
        SELECT States.state, AVG(City_Bike.pop) AS avg_pop, AVG(City_Bike.city_bike) AS avg_bikes
        FROM City_Bike
        JOIN States ON City_Bike.state_id = States.id
        GROUP BY States.state
    ''')
    return cur.fetchall()

#Step 2: Make Graph
def avg_pop_bikes_scatter_plot(cur, conn):
    data = avg_pop_and_bikes_per_state(cur, conn)
    states = []
    avg_pops = []
    avg_bikes = []
    for state, avg_pop, avg_bike in data:
        states.append(state)
        avg_pops.append(avg_pop)
        avg_bikes.append(avg_bike)

    plt.figure(figsize=(10, 6))
    plt.scatter(avg_pops, avg_bikes, color='blue')
    plt.xlabel('Average Population of State')
    plt.ylabel('Average Number of City Bikes')
    plt.title('Scatter Plot: Population vs. Average City Bikes per State')
    plt.show()


#SAMY'S:
def get_temperature(lon, lat):
    key = 'd446d3fd963499d305ca3dfd1cbd1910'
    url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=imperial'
    response = requests.get(url)
    data = response.json() 
    temp = data['main']['temp']
    return temp

def insert_weather(data):
    weather_info = {}
    for city,info in data.items():
        lon = str(info['longitude'])
        lat = str(info['latitude'])
        weather_info[city] = get_temperature(lon, lat)
    
    for city, weather in weather_info.items():
            city_name = city.split(',')[0]  
            cur.execute('''UPDATE City_Bike
                        SET weather = ?
                        WHERE city = ? ''', (weather, city_name))

    conn.commit()
    
#Function Calls
data = get_populations()
cur, conn = create_database("citybike.db")
create_states_table(data, cur, conn)
create_citybike_table(data, cur, conn)
insert_weather(data)

bike_data = city_bikes()  
if bike_data is not None:
    add_city_bikes(bike_data, cur, conn)
else:
    base_path = os.path.abspath(os.path.dirname(__file__))
    full_path = os.path.join(base_path, "city_bike_data.json")
    add_city_bikes(full_path, cur, conn)

# avg_weather(data, bike_data)
# avg_bikes_by_state(cur, conn)
# avg_bike_by_state_graph(cur, conn)
# avg_pop_per_state_graph(cur, conn)
# avg_pop_bikes_scatter_plot(cur, conn)