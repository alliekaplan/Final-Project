from bs4 import BeautifulSoup
import requests
import sqlite3
import os
import json
import matplotlib
import matplotlib.pyplot as plt

""" MAYA: USES WEB-SCRAPPING TO GET POPULATION OF CITY AND THEIR COORDINATES """
def get_populations(): 
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

""" MAYA: CREATES CITY BIKE DATABASE """
def create_database(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/" + db_name)
    cur = conn.cursor()
    return cur, conn

""" MAYA: CREATES STATES TABLE """
def create_states_table(data, cur, conn): 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS States (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT UNIQUE
        )
    """)
    for city_key in data:
        state = city_key.split(',')[1].strip()  
        cur.execute("INSERT OR IGNORE INTO States (state) VALUES (?)", (state,))
    
    conn.commit()

""" MAYA: CREATES CITY_BIKE TABLE """
def create_citybike_table(data, cur, conn): 
    cur.execute('''CREATE TABLE IF NOT EXISTS City_Bike (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                city TEXT, state_id INTEGER, long REAL, lat REAL, city_bike INTEGER, 
                pop INTEGER, weather INTEGER)''')
    conn.commit()

    #Used ChatGPT to learn how to count current # of rows
    cur.execute("SELECT COUNT(*) FROM City_Bike")
    current_count = cur.fetchone()[0]

    data_items = list(data.items())

    if current_count >= len(data_items):
        return

    #Used ChatGPT to count 25 rows at a time
    new_entries = data_items[current_count: current_count + 25]
    for city_key, info in new_entries:
        parts = city_key.split(',')
        city_name = parts[0].strip()
        state = parts[1].strip()
        
        
        cur.execute("SELECT id FROM States WHERE state = ?", (state,))
        row = cur.fetchone()
        if row is None:
            continue
        state_id = row[0]
        
        long_val = info["longitude"]
        lat_val = info["latitude"]
        pop_val = info["population"]
        
        cur.execute('''INSERT INTO City_Bike (city, state_id, long, lat, city_bike, pop, weather)
                       VALUES (?,?,?,?,?,?,?)''',
                    (city_name, state_id, long_val, lat_val, None, pop_val, None))
    
    conn.commit()

""" ALLIE: USES API TO FIND # OF CITY BIKES IN DIFFERENT CITIES """
def city_bikes():
    networks = requests.get("http://api.citybik.es/v2/networks").json()
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

    #Saves info as json in case of failed requests
    with open("city_bike_data.json", "w") as f:
        json.dump(bike_availability, f, indent=4)

    return bike_availability

""" MAYA + ALLIE:: LOADS CITY BIKE INFO INTO DATABASE """
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

""" MAYA + ALLIE: JOINS CITY BIKE AND STATES TABLE TO CALCULATE AVG # OF CITY BIKES PER STATE """
def avg_bikes_by_state(cur, conn): #Used ChatGPT to help use SQLlite AVG() function
    cur.execute('''
        SELECT States.state, AVG(City_Bike.city_bike) AS avg_bikes
        FROM City_Bike
        JOIN States ON City_Bike.state_id = States.id
        GROUP BY States.state
    ''')

    return cur.fetchall()

""" ALLIE + MAYA: MAKES GRAPH FOR AVERAGE CITY BIKES PER STATE """
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

""" MAYA + ALLIE: JOINS CITY BIKE AND STATES TABLE TO CALCULATE TOTAL POP PER STATES W/ CITY BIKES """
def pop_per_state(cur, conn):
    cur.execute('''SELECT States.state, SUM(City_Bike.pop) AS total_pop
                FROM City_Bike
                JOIN States on City_Bike.state_id = States.id
                WHERE City_Bike.city_bike IS NOT NULL
                GROUP BY States.state''')

    return cur.fetchall()

""" ALLIE + MAYA: MAKES GRAPH FOR TOTAL POP PER STATES W/ CITY BIKES"""
def pop_per_state_graph(cur, conn):
    data = pop_per_state(cur, conn)
    states = []
    pops = []
    for state, pop in data:
        states.append(state)
        pops.append(pop)
    plt.figure(figsize=(10, 5))
    plt.bar(states, pops, color='blue')
    plt.xlabel('States')
    plt.ylabel('Total Population')
    plt.title('Total Population Per State with City Bikes')
    plt.xticks(rotation=90)
    plt.show()

""" MAYA + ALLIE: JOINS STATES AND CITY BIKE TABLES TO TOTAL POP AND AVG # OF CITY BIKES"""
def pop_and_bikes_per_state(cur, conn):
    cur.execute('''
        SELECT States.state, SUM(City_Bike.pop) AS total_pop, AVG(City_Bike.city_bike) AS avg_bikes
        FROM City_Bike
        JOIN States ON City_Bike.state_id = States.id
        GROUP BY States.state
    ''')

    return cur.fetchall()

""" MAYA + ALLIE: MAKES GRAPH FOR TOTAL POPULATION BY AVG # OF CITY BIKES PER STATE"""
def pop_bikes_scatter_plot(cur, conn):
    data = pop_and_bikes_per_state(cur, conn)
    states = []
    avg_pops = []
    avg_bikes = []
    for state, avg_pop, avg_bike in data:
        states.append(state)
        avg_pops.append(avg_pop)
        avg_bikes.append(avg_bike)

    plt.figure(figsize=(10, 6))
    plt.scatter(avg_pops, avg_bikes, color='blue')
    plt.xlabel('Total Population of State')
    plt.ylabel('Average Number of City Bikes')
    plt.title('Population vs. Average City Bikes per State')
    plt.show()

""" SAMY: USES API TO ACESS CURRENT WEATHER OF SPECIFIED LOCATION """
def get_temperature(lon, lat):
    key = 'd446d3fd963499d305ca3dfd1cbd1910'
    url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=imperial'
    response = requests.get(url)
    data = response.json() 
    temp = data['main']['temp']
    return temp

""" SAMY: INSERTS CURRENT WEATHER FOR ALL THE CITYS IN CITY BIKE TABLE"""
def insert_weather(data, cur, conn):
    weather_info = {}
    for city,info in data.items():
        lon = str(info['longitude'])
        lat = str(info['latitude'])
        weather_info[city] = get_temperature(lon, lat)

    #saves data to json in case of request failure
    with open("weather_data.json", "w") as f:
        json.dump(weather_info, f, indent=4)

    for city, weather in weather_info.items():
            city_name = city.split(',')[0]  
            cur.execute('''UPDATE City_Bike
                        SET weather = ?
                        WHERE city = ? ''', (weather, city_name))

    conn.commit()

""" MAYA + ALLIE: JOIN STATES AND CITY BIKE TABLES TO CALCULATE AVG WEATHER AND AVG # OF CITY BIKES """
def avg_weather_bikes_by_state(cur, conn):
    cur.execute('''
        SELECT States.state, AVG(City_Bike.weather) AS avg_weather, AVG(City_Bike.city_bike) AS avg_bikes
        FROM City_Bike
        JOIN States ON City_Bike.state_id = States.id
        GROUP BY States.state
    ''')
    
    return cur.fetchall()

""" SAMY: CREATES GRAPH FOR AVG WEATHER BY AVG # OF CITY BIKES IN EACH STATE """
def avg_weather_bikes_by_state_plot(cur, conn):
    data = avg_weather_bikes_by_state(cur, conn)
    states = []
    avg_weather_list = []
    avg_bikes = []
    for state, avg_weather, avg_bike in data:
        states.append(state)
        avg_weather_list.append(avg_weather)
        avg_bikes.append(avg_bike)

    plt.figure(figsize=(10, 6))
    plt.scatter(avg_weather_list, avg_bikes, color='blue')
    plt.xlabel('Average Weather of State')
    plt.ylabel('Average Number of City Bikes')
    plt.title('Weather vs. Average City Bikes per State')
    plt.show()


""" MAYA: CALCULATES TOTAL POP, AVG WEATHER, AVG # OF CITY BIKES PER STATE AND SAVES CALCS TO A TXT FILE """
def calculations(cur, conn):
    cur.execute('''SELECT States.state, AVG(City_Bike.weather) AS avg_weather, AVG(City_Bike.city_bike) AS avg_bikes, 
            SUM(City_Bike.pop) AS total_pop
            FROM City_Bike
            JOIN States ON City_Bike.state_id = States.id
            GROUP BY States.state''')
    
    results = cur.fetchall()

    with open('calculations.txt', 'w') as f:
        f.write("State, Average Weather, Average Bikes, Total Population\n")
        for state, avg_weather, avg_bikes, total_pop in results:
            if avg_bikes is not None:
                f.write(f"{state},{avg_weather},{avg_bikes:.2f},{total_pop}\n")
            else:
                f.write(f"{state},{avg_weather},None,{total_pop}\n")

def main():
    data = get_populations()
    cur, conn = create_database("citybike.db")
    create_states_table(data, cur, conn)
    create_citybike_table(data, cur, conn)
    insert_weather(data, cur, conn)

    try:
        bike_data = city_bikes()  
        add_city_bikes(bike_data, cur, conn)
    except:
        base_path = os.path.abspath(os.path.dirname(__file__))
        full_path = os.path.join(base_path, "city_bike_data.json")
        add_city_bikes(full_path, cur, conn)

    avg_weather_bikes_by_state(cur, conn)
    avg_weather_bikes_by_state_plot(cur, conn)
    avg_bikes_by_state(cur, conn)
    avg_bike_by_state_graph(cur, conn)
    pop_per_state(cur, conn)
    pop_per_state_graph(cur, conn)
    pop_and_bikes_per_state(cur, conn)
    pop_bikes_scatter_plot(cur, conn)
    calculations(cur, conn)

if __name__ == "__main__":
    main()