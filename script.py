import pandas as pd
import requests
import json
from simplejson import JSONDecodeError
import warnings
import psycopg2
import yaml

airports_spain = pd.read_csv('./data/airports_spain.csv')[['ICAO', 'City']]

#https://avwx.rest/

# PREPARATION AND INIT

with open('./keys/keys.yml') as file:
    keys = yaml.load(file)

headers = {
  'Authorization': keys['key1'],
  'Content-Type': 'application/json'
}

headers2 = {
  'Authorization': keys['key2'],
  'Content-Type': 'application/json'
}

reporting = "true"
formatting = "json"
onfail = "error"

conn = psycopg2.connect(
    host=keys['pghost'],
    database="metar",
    port=35728,
    user=keys['pguser'],
    password=keys['pgpass'])

# MAIN TASK

def parseo (url, city):
    
    #Request
    response = requests.get( url, headers = headers, verify=False )
    if response.status_code == 400 or response.status_code == 204:
        return None
    else:
        json_response = json.loads(response.text)

        #Parsing
        metar = json_response['raw']
        station = json_response['station']
        pressure = json_response['altimeter']['value']
        pressure_unit = json_response['units']['altimeter']
        wind_direction = json_response['wind_direction']['value']
        wind_unit = 'º'
        wind_speed = json_response['wind_speed']['value'] 
        wind_speed_unit = json_response['units']['wind_speed']
        visibility_str = json_response['visibility']['repr']
        visibility_number = json_response['visibility']['value']
        visibility_unit = json_response['units']['visibility']
        temperature = json_response['temperature']['value'] 
        temperature_unit = json_response['units']['temperature']
        remarks = json_response['remarks']
        flight_rules = json_response['flight_rules']
        time = json_response['time']['dt']

        clouds = []
        if not json_response['clouds']:
            clouds = ["No clouds"]
        else:
            for element in json_response['clouds']:
                clouds.append(element['repr'])
        if json_response['wind_gust'] == None:
            json_response['wind_gust'] = 0
        wind_gust = json_response['wind_gust']
        wind_gust_unit = json_response['units']['wind_speed']
        try: 
            wind_direction_var_1 = json_response['wind_variable_direction'][0]['value']
            wind_direction_var_1_unit = 'º'
        except:
            wind_direction_var_1 = None
            wind_direction_var_1_unit = None
        try: 
            wind_direction_var_2 = json_response['wind_variable_direction'][1]['value']
            wind_direction_var_2_unit = 'º'
        except:
            wind_direction_var_2 = None
            wind_direction_var_2_unit = None

        readyforinsertion = (metar, time, station, city, pressure, pressure_unit, clouds, wind_direction, wind_unit, 
                             wind_speed, wind_speed_unit, wind_direction_var_1, wind_direction_var_1_unit, 
                             wind_direction_var_2, wind_direction_var_2_unit, visibility_str, visibility_number, 
                             visibility_unit, temperature, temperature_unit, remarks, flight_rules)
        return readyforinsertion

# EXECUTION

with open('./sql.yml') as file:
    sql_sentences = yaml.load(file)

try:
    cur = conn.cursor()
    cur.execute(sql_sentences['create_table'])
    conn.commit()
    cur.close()
except:
    print("Rollback")
    conn.rollback()

warnings.simplefilter("ignore")

for airport in airports_spain.itertuples():
    url = "https://avwx.rest/api/metar/" + airport[1] + "?reporting=" + reporting + "&format=" + formatting + "&onfail=" + onfail
    data = parseo(url, airport[2])
    if data == None:
        continue
    else:
        print(data)
        try:
            cur = conn.cursor()
            cur.execute(sql_sentences['insert_table'], data)
            conn.commit()
            cur.close()
        except Exception as e:
            print(e)
            conn.rollback()

conn.close()