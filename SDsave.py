import machine, sdcard, os, utime, configparser

spi = machine.SPI(0, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
cs = machine.Pin(17, machine.Pin.OUT)

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
    config = configparser.ConfigParser()
    config.read("settings.ini")

    if config["Other"]["File Type"] == "csv": 
        with open("data.csv", "a") as file: file.write(f"{time};{data}\n")
    elif config["Other"]["File Type"] == "txt":
        with open("data.txt", "a") as file: file.write(f"{time}, {data}\n")

def error(error:Exception, desc:str, time: str):
    """
    Saves errors to the 'error log.txt' file
    """
    with open("error.log", "a") as file: file.write(f"Elapsed: [{make_readable(round(utime.ticks_ms()/1000))}], Time: {time}, {str(error)}, {desc}\n")

def debug(data:str, time: str):
    """
    Saves debug statements to the 'debug log.txt' file
    """
    with open("debug.log", "a") as file: file.write(f"Elapsed: [{make_readable(round(utime.ticks_ms()/1000))}], Time: {time}, {data}\n")