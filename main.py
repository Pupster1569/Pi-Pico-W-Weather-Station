import machine, utime, ssd1306, _thread, configparser, ds3231, temperature, SDsave, server # import required libraries
last_log_time = utime.ticks_ms() # setup initial log output time so log time doesn't start at 2

"""
Error codes:
ERR - Unknown error, see 'error log.log' for more info
ERR: 0 - Error with temperature/humidity sensor. Usually means system cant see the temperature/humidity sensor
ERR: 1 - System doesn't see microSD card
ERR: 2 - Couldn't calculate rpm
ERR: 3 - Couldn't connect to network
ERR: 4 - RTC module error. Usually means system cant see the ds3231 module
ERR: 5 - No 'settings.ini' file
"""

debug = True # default debug toggle

# set up the display
i2c = machine.I2C(1, scl=machine.Pin(27), sda=machine.Pin(26))
oled = ssd1306.SSD1306_I2C(128, 32, i2c)
oled.fill(0) # clear the display

# set up the ds3231 rtc module
def dt_tuple(dt): return utime.localtime(utime.mktime(dt))  # type: ignore # Populate weekday field
i2c = machine.SoftI2C(scl=machine.Pin(15, machine.Pin.OPEN_DRAIN, value=1), sda=machine.Pin(14, machine.Pin.OPEN_DRAIN, value=1))
rtc_error = False
# check for errors
try: rtc = ds3231.DS3231(i2c)
except Exception as e:
    if debug: print(f"{e}, No rtc module")
    oled.text("ERR: 4", 0, 0)
    oled.show()
    rtc_error = True
if not rtc_error: # code doesn't run if an error is found with rtc module
    error = SDsave.initialise() # initialise the microSD card and assign error to it incase it returns an error
    if error: # code doesn't run if an error is found with microSD card
        if debug: print(f"{error[1]}, No mircoSD card")
        oled.text("ERR: 1", 0, 0)
        oled.show()
    else:
        _, error = temperature.read() # check if the dht11 sensor produces an error
        if type(error) == OSError:  # code doesn't run if an error is found with the temperature/humidity sensor
            time = rtc.get_time()
            SDsave.error(Exception(error), "Couldnt read temperature/humidity sensor", f"{time[3]}:{time[4]}:{time[5]}")
            if debug: print("Couldnt read temperature/humidity sensor")
            oled.fill(0)
            oled.text("ERR: 0", 0, 0)
            oled.show()
        else:
            try: # look for 'settings.ini' file
                open('settings.ini', "r").close()
                settings_error = False
            except Exception as e: # if no 'settings.ini' file found
                time = rtc.get_time()
                if debug: print(e, "No 'settings.ini' file")
                SDsave.error(Exception(error), "Couldnt read temperature/humidity sensor", f"{time[3]}:{time[4]}:{time[5]}")
                oled.fill(0)
                oled.text("ERR: 5", 0, 0)
                oled.show()
                settings_error = True
            if not settings_error: # code doesn't run there is no 'settings.ini' file found
                config = configparser.ConfigParser()
                config.read("settings.ini")

                debug = bool(config["Other"]["Debug"])

                # check if the webserver needs to be activated
                server_toggle = machine.Pin(21,machine.Pin.OUT).value()
                oled.text("Web Server: ", 0, 0)
                if server_toggle: oled.text("ACTIVE", 0, 10)
                else: oled.text("INACTIVE", 0, 10)
                oled.show()
                if not debug: utime.sleep(0.5)
                if server_toggle: addr,s,clients = server.initialise() # initialise the webserver if toggled

                anemometer = machine.ADC(machine.Pin(28)) # Configure the anemometer on GP28

                # Constants
                THRESHOLD = int(config["RPM"]["Threshold"])  # Threshold to distinguish between high and low values
                MAX_TIME_DIFF = int(config["RPM"]["Max Time Diff"])  # Maximum time difference (in milliseconds) to consider valid
                TIMEOUT = int(config["RPM"]["Timeout"])  # Timeout in milliseconds to reset RPM to 0 if no movement
                UPDATE_INTERVAL = int(config["RPM"]["Update Interval"]) # Interval between updating the display in milliseconds
                LOG_INTERVAL = int(config["RPM"]["Log Interval"]) # Interval in ms between each log output, 600000 ms = 10 min or 600 seconds

                # Variables for edge detection and timing
                last_output_time = utime.ticks_ms()
                last_value, last_edge_time, edge_times = 0, 0, []
                rpm, rpm_count, rpm_total, highest_rpm, avg_rpm, rotations = 0, 0, 0, 0, 0, 0

                def calculate_rpm() -> float|Exception:
                    """
                    Calculates current rpm using the time taken between each edge
                    """
                    try:
                        global edge_times, rpm
                        if len(edge_times) < 4:
                            return 0
                        
                        total_time = sum(edge_times[-4:])
                        if total_time > 0:
                            rpm = 60000 / total_time  # One rotation per 4 edges, 60000 milliseconds in a minute
                        return rpm
                    except Exception as e: return e

                temp,hum = 0,0
                def temperatureCore():
                    """
                    Calculates temperature and humidity on the second core as to not interfere with first cores calculations
                    """
                    global temp, hum
                    temp, hum = temperature.read()

                def main():
                    # set globals
                    global last_value, last_edge_time, edge_times, rpm, last_output_time, last_log_time, rpm_count, rpm_total, highest_rpm, rotations, addr, s, clients, rtc, config, debug
                    global UPDATE_INTERVAL, LOG_INTERVAL, THRESHOLD, MAX_TIME_DIFF, TIMEOUT
                    # rpm_values = []
                    try:
                        time = rtc.get_time()
                        while True:
                            if server_toggle: server.server(addr,s,clients) # run webserver code if toggled

                            current_value = anemometer.read_u16() # get anemometer analogue value
                            current_time = utime.ticks_ms()  # get current time in milliseconds
                            
                            if (current_value < THRESHOLD and last_value >= THRESHOLD) or \
                            (current_value >= THRESHOLD and last_value < THRESHOLD):
                                # edge detected
                                edge_time = utime.ticks_diff(current_time, last_edge_time)
                                rotations += 0.25
                                
                                if edge_time < MAX_TIME_DIFF:
                                    edge_times.append(edge_time)
                                    if len(edge_times) > 4:
                                        edge_times.pop(0)
                                    
                                    rpm = calculate_rpm()
                                    if type(rpm) == Exception:
                                        if debug: print(f"{rpm}, Error calculating rpm")
                                        time = rtc.get_time()
                                        SDsave.error(Exception(rpm), "Error calculating rpm", f"{time[3]}:{time[4]}:{time[5]}")
                                        oled.fill(0)
                                        oled.text("ERR: 2", 0, 0)
                                        oled.show()
                                        utime.sleep(1)
                                        break
                                last_edge_time = current_time  # update last_edge_time for every edge detection

                            # check for timeout
                            if utime.ticks_diff(current_time, last_edge_time) > TIMEOUT:
                                rpm = 0
                                edge_times = []

                            if utime.ticks_diff(current_time, last_output_time) >= UPDATE_INTERVAL:
                                _thread.start_new_thread(temperatureCore,())
                                if temp == None:
                                    if debug: print(f"{hum}, Error on temperature core")
                                    time = rtc.get_time()
                                    SDsave.error(Exception(hum), "Error on temperature core", f"{time[3]}:{time[4]}:{time[5]}")
                                    # oled.fill(0)
                                    # oled.text("ERR: 0", 0, 0)
                                    # oled.show()
                                    # utime.sleep(1)
                                    # break
                                
                                # alternate average method incase timeout is set above 4 seconds to stop average from being affected too heavily
                                # if len(rpm_values) >= (TIMEOUT/1000): rpm_values = []
                                # rpm_values.append(rpm)
                                # if len(rpm_values) - 2 >= 0 and rpm_values[-3] != rpm and rpm != 0:
                                #     rpm_count += 1
                                #     rpm_total += rpm
                                # else:
                                #     rpm_count += 1
                                #     rpm_total += rpm
                                
                                # set highest rpm
                                if rpm > highest_rpm: highest_rpm = rpm  # type: ignore
                                # add rpm values for average
                                if rpm != 0:
                                    rpm_count += 1
                                    rpm_total += rpm # type: ignore

                                if debug: time = rtc.get_time()
                                if debug: print(f"Current RPM: {rpm:.2f}, Temperature: {temp}°C, Humidity: {hum}%, Time: {time[3]}:{time[4]}:{time[5]}")
                                # output values to the display
                                oled.fill(0) # clear the display
                                oled.text(f"RPM: {rpm:.2f}", 0, 0)
                                oled.text(f"Temp: {temp}C", 0, 10)
                                oled.text(f"Hum: {hum}%", 0, 20)
                                # oled.text(f"{time[3]}:{time[4]}:{time[5]}", 0, 20)
                                oled.show()
                                # reset output time so this code runs the next second
                                last_output_time = current_time

                            if utime.ticks_diff(current_time, last_log_time) >= LOG_INTERVAL:
                                # save data to microSD card every 10 minutes

                                # calculate average rpm
                                if rpm_count > 0: avg_rpm = rpm_total/rpm_count
                                else: avg_rpm = 0

                                time = rtc.get_time() # get current date and time

                                txt_data = f'{highest_rpm:.2f}, {avg_rpm:.2f}, {rotations}, {temp}, {hum}'
                                if config["Other"]["File Type"] == "txt":
                                    txt_time = f'{time[0]}/{time[1]}/{time[2]}, {time[3]}:{time[4]}:{time[5]}'
                                    SDsave.data(txt_data, txt_time) # save data to txt
                                elif config["Other"]["File Type"] == "csv":
                                    csv_time = f'{time[0]}/{time[1]}/{time[2]} ;{time[3]}:{time[4]}:{time[5]}'
                                    csv_data = f'{highest_rpm:.2f};{avg_rpm:.2f};{rotations};{temp};{hum}'
                                    SDsave.data(csv_data, csv_time) # save data to csv

                                if debug: print(txt_data)

                                # reset values for next 10 minutes
                                rotations, rpm_count, rpm_total, highest_rpm = 0, 0, 0, 0
                                last_log_time = current_time

                            last_value = current_value
                            utime.sleep(0.005) # small delay so sensors can update correctly
                    except Exception as e:
                        # check for errors in the main loop
                        if debug: print(f'{e}, "Error in main loop"')
                        time = rtc.get_time()
                        SDsave.error(e, "Error in main loop", f"{time[3]}:{time[4]}:{time[5]}")
                        oled.fill(0)
                        oled.text("ERR", 0, 0)
                        oled.show()

                # start script
                try:
                    if __name__ == "__main__": main()
                except Exception as e:
                    # check for errors in the main loop
                    if debug: print(f'{e}, "Error in main loop"')
                    time = rtc.get_time()
                    SDsave.error(e, "Error in main loop", f"{time[3]}:{time[4]}:{time[5]}")
                    oled.fill(0)
                    oled.text("ERR", 0, 0)
                    oled.show()