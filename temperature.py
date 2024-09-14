import machine, dht, SDsave
dht_sensor = dht.DHT11(machine.Pin(22)) # define temperature & humidity sensor
def read() -> list[int]|list:
    """
    Returns the current temperature and humidity as [Temp,Hum]. Returns [None, e] if an error occurred
    """
    try:
        # Trigger a measurement
        dht_sensor.measure()
        return [dht_sensor.temperature(), dht_sensor.humidity()]
    except Exception as e:
        SDsave.error(e, "Error reading temperature and humidity")
        return [None,e]