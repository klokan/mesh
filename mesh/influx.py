from influxdb import InfluxDBClient


class Influx:

    def __init__(self, mesh):
        config = mesh.config['influx']
        self.dsn = config['dsn']

    def client(self):
        return InfluxDBClient.from_dsn(self.dsn)
