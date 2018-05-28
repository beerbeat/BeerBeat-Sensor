import datetime, time
import argparse
from envirophat import light, motion, weather, leds
from influxdb import InfluxDBClient

def publish_data(client, activity_tot, temperature):

    """Publishes the total activity and temperature to the InfluxDB using the client connection"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    json_body = [
        {
            "time": timestamp,
            "fields": {
                "ActivityTot": activity_tot,
                "Temp": temperature
            }
        }
    ]
    client.write_points(json_body)

def run_measurements(client):

    """Measures accelerometer activity continously and stores an aggregated sum once per minute"""

    print_sample_time = 60  # How often data will be published to InfluxDB [seconds]
    last_print_time = datetime.datetime.now()
    limit = 350  # Minimum distance between two subsequent measurements to be counted as activity. [G]
    last_sample_x = 0
    last_sample_y = 0
    last_sample_z = 0
    activity_x = 0
    activity_y = 0
    activity_z = 0

    leds.on()  # Turn on LEDs to indicate measurement
    try:
        while True:
            x, y, z = motion.accelerometer()
            if x > limit:
                activity_x += x
            if y > limit:
                activity_y += y
            if z > limit:
                activity_z += z

            # Probably unnecessary
#            x_dist = x - last_sample_x
#            y_dist = y - last_sample_y
#            z_dist = z - last_sample_z
#
#            if x_dist > limit:
#                activity_x += x_dist
#            if y_dist > limit:
#                activity_y += y_dist
#            if z_dist > limit:
#                activity_z += z_dist

            time_dist = datetime.datetime.now() - last_print_time


            if time_dist.total_seconds() >= print_sample_time:
                last_print_time = datetime.datetime.now()
                activity_tot = activity_x + activity_y + activity_z
                temp = weather.temperature()
                publish_data(client, activity_tot, temp)
                activity_x = 0
                activity_y = 0
                activity_z = 0


    except KeyboardInterrupt:
        leds.off()  # Shut off LEDs
        out.close()  # Close log
        client.close()  # Close influx connection


def setup_database(host='localhost', port=8086, database='BeerBeat', measurement=str(datetime.date.today())):

    """Instantiate a connection to the InfluxDB. If no measurement name is given,
    the current date is chosen as measurement name"""
    user = 'root'
    password = 'root'
    dbname = database

    client = InfluxDBClient(host, port, user, password)  # connect to local InfluxDB
    databases = client.get_list_database()  # Get a list of available databases
    exist_database = False  # If provided database name exist, connect to that. Otherwise create new database
    for db in databases:
        if db['name'] is database:
            exist_database = True
            break

    if not exist_database:
        client.create_database(dbname)

    client = InfluxDBClient(host, port, user, password, dbname, measurement)

    return client


def parse_args():
    """Parse the args."""
    parser = argparse.ArgumentParser(
        description='Argument that can be parsed to the InfluxDB')
    parser.add_argument('--host', type=str, required=False,
                        default='localhost',
                        help='hostname of InfluxDB http API')
    parser.add_argument('--port', type=int, required=False, default=8086,
                        help='port of InfluxDB http API')
    parser.add_argument('--database', type=str, required=False, default='BeerBeat',
                        help='InfluxDB database name')
    parser.add_argument('--measurement', type=str, required=False, default=str(datetime.date.today()),
                        help='InfluxDB measurement')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    out = open('enviro.log', 'w')  # Open log
    client = setup_database(host=args.host, port=args.port, database = args.database, measurement = args.measurement)
    run_measurements(client)


