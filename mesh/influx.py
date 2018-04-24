from influxdb import InfluxDBClient


class Influx:

    def __init__(self, mesh):
        self.dsn = mesh.config['INFLUX_DSN']

    def client(self):
        return InfluxDBClient.from_dsn(self.dsn)
