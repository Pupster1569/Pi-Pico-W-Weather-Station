import machine, sdcard, os, utime, configparser, ssd1306

spi = machine.SPI(0, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
cs = machine.Pin(17, machine.Pin.OUT)

i2c = machine.I2C(1, scl=machine.Pin(27), sda=machine.Pin(26))
oled = ssd1306.SSD1306_I2C(128, 32, i2c)
oled.fill(0) # clear the display

led = machine.Pin("LED", machine.Pin.OUT) # set up the onboard LED for a saving indicator

def make_readable(seconds): 
    """
    Format seconds into 00:00:00
    """
    return f"{0 if int((seconds/60)/60) < 10 else ''}{int(seconds/3600)}:{0 if int((seconds/3600-int(seconds/3600))*60) < 10 else ''}{int((seconds/3600-int(seconds/3600))*60)}:{0 if seconds-(60*int(seconds/60)) < 10 else ''}{seconds-(60*int(seconds/60))}"

def initialise():
    """
    Set up the microSD card
    """
    try:
        led.on()
        sd = sdcard.SDCard(spi, cs)

        vfs = os.VfsFat(sd) # type: ignore
        os.mount(vfs, "/sd") # type: ignore
        os.chdir("/sd")
        config = configparser.ConfigParser()
        config.read("settings.ini")

        if config["Other"]["File Type"] == "csv":
            try: open("data.csv", "r").close()
            except: 
                with open("data.csv","w") as file:
                    file.write("Date;Time;Max RPM;Avg RPM;Rotations;Temperature;Humidity\n")
        elif config["Other"]["File Type"] == "txt":
            try: open("data.txt", "r").close()
            except: open("data.txt","w").close()

        # save errors to log
        try: open("error.log", "r").close()
        except: open("error.log","w").close()

        # debug
        try: open("debug.log", "r").close()
        except: open("debug.log","w").close()
        led.off()
    except Exception as e:
        return [None, e]

# def data(data:str, time: str):
#     # highest_rpm, avg_rpm, total_rotations, temp, hum
#     """
#     Saves readings to the 'data.txt' file
#     """
#     with open("data.txt", "a") as file: file.write(f"{time}, {data}\n")

def data(data:str, time: str):
    # highest_rpm, avg_rpm, total_rotations, temp, hum
    """
    Saves readings to the 'data.txt' or the 'data.csv' file
    """
    try:
        config = configparser.ConfigParser()
        config.read("settings.ini")
        led.on()
        if config["Other"]["File Type"] == "csv": 
            with open("data.csv", "a") as file: file.write(f"{time};{data}\n")
        elif config["Other"]["File Type"] == "txt":
            with open("data.txt", "a") as file: file.write(f"{time}, {data}\n")
        led.off()
    except Exception as e:
        oled.fill(0)
        oled.text("ERR: 1", 0, 0)
        oled.show()
        raise e

def error(error:Exception, desc:str, time:str='N/A'):
    """
    Saves errors to the 'error log.txt' file
    """
    try:
        led.on()
        with open("error.log", "a") as file: file.write(f"Elapsed: [{make_readable(round(utime.ticks_ms()/1000))}], Time: {time}, {str(error)}, {desc}\n")
        led.off()
    except Exception as e:
        oled.fill(0)
        oled.text("ERR: 1", 0, 0)
        oled.show()
        raise e

def debug(data:str, time:str):
    """
    Saves debug statements to the 'debug log.txt' file
    """
    try:
        led.on()
        with open("debug.log", "a") as file: file.write(f"Elapsed: [{make_readable(round(utime.ticks_ms()/1000))}], Time: {time}, {data}\n")
        led.off()
    except Exception as e:
        oled.fill(0)
        oled.text("ERR: 1", 0, 0)
        oled.show()
        raise e