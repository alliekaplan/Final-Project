import requests

def city_bikes():
    networks = requests.get("http://api.citybik.es/v2/networks").json()['networks']
    us_networks = [n for n in networks if n['location']['country'] == 'US'] #get US cities only
    bike_availability = {}

    #get the number of available bikes
    for net in us_networks:
        network_id = net['id']
        city = net['location']['city']
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
    print(bike_availability)

#city_bikes()

def add_city_bikes(bike_data,cur,conn):
    for city, bike_data in bike_data.items():
        city_name = city.split(',')[0]
        bike_number = bikes
        cur.execute('''UPDATE City_Bike
                    SET city_bike = ?
                    WHERE city = ? ''', (bike_number, city_name))

    conn.commit()

bike_data = city_bikes()
add_city_bikes(bike_data,cur,conn) 



