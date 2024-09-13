import machine, ssd1306, utime, network, socket, ntptime, configparser, ds3231

# set up the display
i2c = machine.I2C(1, scl=machine.Pin(27), sda=machine.Pin(26))
oled = ssd1306.SSD1306_I2C(128, 32, i2c)
oled.fill(0) # clear the display

# set up the ds3231 rtc module
def dt_tuple(dt): return utime.localtime(utime.mktime(dt))  # type: ignore # Populate weekday field
i2c = machine.SoftI2C(scl=machine.Pin(15, machine.Pin.OPEN_DRAIN, value=1), sda=machine.Pin(14, machine.Pin.OPEN_DRAIN, value=1))
# rtc is declared in initialise to not pause code at start incase of error

def adjust_time_zone(time_tuple):
    config = configparser.ConfigParser()
    TIME_ZONE_OFFSET = int(config["NTP Settings"]["Time Zone Offset"])
    year, month, day, hours, minutes, seconds, weekday, yearday = time_tuple
    hours += TIME_ZONE_OFFSET
    # Handle day rollover
    if hours >= 24:
        hours -= 24
        day += 1
    elif hours < 0:
        hours += 24
        day -= 1
    # Simple month length approximation (ignoring leap years for simplicity)
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # Handle month rollover
    if day > days_in_month[month - 1]:
        day = 1
        month += 1
        if month > 12:
            month = 1
            year += 1
    elif day < 1:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        day = days_in_month[month - 1]
    return (year, month, day, hours, minutes, seconds, weekday, yearday)


def sync_time():
    config = configparser.ConfigParser()
    config.read("settings.ini")
    TIME_ZONE_OFFSET = int(config["NTP Settings"]["Time Zone Offset"])
    NTP_SERVER = config["NTP Settings"]["NTP Server"]
    ntptime.host = NTP_SERVER
    ntptime.settime()
    current_time = adjust_time_zone(utime.localtime(ntptime.time()))
    return current_time

def serve_index():
    try:
        with open('/sd/index.html', 'r') as file:
            return file.read()
    except OSError as e:
        print(f"Error reading index.html from SD card: {e}")
        return "Error: Could not read index.html from SD card"

def handle_request(request):
    if b'GET / ' in request:
        return serve_index(), 'text/html'
    elif b'GET /download ' in request:
        try:
            config = configparser.ConfigParser()
            config.read("settings.ini")

            if config["Other"]["File Type"] == "txt":
                with open('/sd/data.txt', 'r') as file:
                    content = file.read()
                return content, 'text/plain', 'data.txt'
            
            elif config["Other"]["File Type"] == "csv":
                with open('/sd/data.csv', 'r') as file:
                    content = file.read()
                return content, 'text/plain', 'data.csv'
            
        except OSError as e:
            print(f"Error reading data.txt from SD card: {e}")
            return "Error: Could not read data.txt from SD card", 'text/plain'
    else:
        return "404 Not Found", 'text/plain'

def send_response(client, response, content_type, filename=None):
    try:
        if filename:
            client.send(f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\nContent-Disposition: attachment; filename="{filename}"\r\nConnection: close\r\n\r\n')
        else:
            client.send(f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\nConnection: close\r\n\r\n')
        if isinstance(response, str):
            client.sendall(response.encode('utf-8'))
        else:
            client.sendall(response)
    except Exception as e:
        print(f"Error sending response: {e}")

def initialise():
    """
    Connect to network and open a socket
    """
    config = configparser.ConfigParser()
    config.read("settings.ini")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config["Wi-Fi Settings"]["Wi-Fi SSID"], config["Wi-Fi Settings"]["Wi-Fi Pass"])

    # Wait for connection
    max_wait = 120
    count = 0
    while max_wait > 0:
        if count == 3: count = 0
        count += 1
        
        oled.fill(0)
        oled.text("Web Server: ", 0, 0)
        if count == 1: oled.text("Waiting.", 0, 10)
        elif count == 2: oled.text("Waiting..", 0, 10)
        elif count == 3: oled.text("Waiting...", 0, 10)
        oled.show()
        
        if wlan.status() < 0 or wlan.status() >= 3: break
        max_wait -= 1
        print('waiting for connection...')
        utime.sleep(1)

    # Handle connection error
    if wlan.status() != 3:
        oled.fill(0)
        oled.text("ERR: 3", 0, 0)
        oled.show()
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print('IP address:', status[0])
        oled.fill(0)
        oled.text("Web Server: ", 0, 0)
        oled.text("Connected! ", 0, 10)
        oled.text(f"{status[0]}", 0, 20)
        oled.show()
        utime.sleep(2)

        rtc = ds3231.DS3231(i2c) # declare rtc here incase of error which can be handled by main
        rtc.set_time(sync_time()) # sync ds3231 rtc module with network time protocol (ntp)

        # Open socket
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(5)
        s.setblocking(False)  # Set the socket to non-blocking
        print('listening on', addr)
        clients = []
        return [addr,s,clients]

def server(addr,s,clients):
    """
    Main webserver code
    """
    # Accept new connections
    try:
        cl, addr = s.accept()
        cl.setblocking(False)
        clients.append(cl)
    except OSError:
        pass  # No new connection, continue
    
    for client in clients[:]:
        try:
            request = client.recv(1024)
            if request:
                response, content_type, *extra = handle_request(request) # type: ignore
                filename = extra[0] if extra else None
                send_response(client, response, content_type, filename)
                client.close()
                clients.remove(client)
            else:
                client.close()
                clients.remove(client)
        except OSError:
            pass  # No data, continue