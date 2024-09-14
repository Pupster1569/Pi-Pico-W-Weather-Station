# Raspberry Pi Pico W Weather Station
---

This is a simple weather station developed for the raspberry Pi Pico W micro controller. This project was made for a commission. 

The system uses a ssd1306 oled display, a standard micro sd card module, a dht11 temperature and humidity sensor, a 3 cup anemometer, a simple switch, and a ds3231 rtc module

Data is saved onto a microSD card (<=16GB) by default every 10 minutes (configurable in settings.ini) as either a .txt file or a .csv file (configurable in settings.ini). Errors are logged to an error.log file, and debug info (if enabled) saves to a debug.log file

The system uses the onboard Wi-Fi module to host a webserver on a network specified in the settings.ini file. The webserver is very simple, 
consisting only of a button to download the data file (nothing more was required for the commission). The webserver can be toggled on the fly using the switch. Please note that the system must be turned off before enabling or disabling the webserver as the switch does nothing during runtime. This is because Wi-Fi modules can be finnicky, so to stop any Wi-Fi weirdness the system must be off before toggling the webserver

RPM, temperature, and humidity are all displayed on the oled display which by default updates once every second (configurable in settings.ini)

RPM is calculated by measuring the time between each edge/detection (4 total for my sensor). These values are then added together and used in the following calculation: ```60000 / total_time```. This gives a relatively accurate reading in my testing with no need for any rolling average/smoothing so RPM updates very quickly. There is a maximum time that is read between each edge, this is by default set to 4 seconds (configurable in settings.ini). There is also a maximum time before the rpm gets set to 0, this is by default set to 4 seconds (configurable in settings.ini). With the default values, the lowest rpm the system can read is ~7rpm. The higher the values, the lower rpm the system can read however it also increases the time it takes for the system to zero (zero'ing is when the system realizes the anemometer is no longer moving and therefore setting the rpm to 0). As it stands I would not recommend setting the timeout to more than 4 seconds as this can affect the average rpm reading as it would save a lot of junk data (for example if the anemometer stops moving, the system will keep logging the values which haven't been zero'd yet). I have included some code that should fix it however I have not tested it so use it at your own risk

The dht11 temperature and humidity sensor is very simple. All the code does is request the current temperature and humidity from the sensor and uses the data it receives. This request however was causing some issues in the past. The request generates an interrupt which messes up the timings of the onboard rtc module which is used for the timings of things like the display update and saving data to the data file. This caused a lot of issues, especially with the rpm calculations (im not sure exactly why but my best guess is due to the rpm calculation method using timings which get messed up by the interrupt). To fix this im using the Pi Pico's second core to send and receive the request. This way, even if the request causes an interrupt, no timings will get messed up/de-synced. This works very well, be careful however when changing update interval in settings.ini below 1 second as this can cause some issues with the multi threading. This is because after the code has received the data, it closes the thread and opens a new one at the next update interval. If you've used a Pico with multithreading before, you'll know just how finnicky multithreading is. The ~1 second delay between each time the thread opens and closes is a good way to stop any potential bugs with creating a new thread

The oled also displays various error codes if an error occurs during runtime. These errors are:
* ERR - Unknown error, see 'error log.log' for more info
* ERR: 0 - Error with temperature/humidity sensor. Usually means system cant see the temperature/humidity sensor
* ERR: 1 - System doesn't see microSD card
* ERR: 2 - Couldn't calculate rpm
* ERR: 3 - Couldn't connect to network
* ERR: 4 - RTC module error. Usually means system cant see the ds3231 module
* ERR: 5 - No 'settings.ini' file

The system was designed and tested using a 10000mAh battery bank which powers the Pico via micro usb for anywhere from 5-8 days when the webserver is not running (Results may vary). I have not tested how long the system lasts while the webserver is active, I do not however recommend leaving the webserver running while the system is in use as the Wi-Fi module uses a lot of power. It is recommended that you only enable the webserver when you want to download the data. Please remember that to start or stop the webserver, the system must be off first

The ds3231 rtc module is synced to the ntp every time the system is connected to Wi-Fi (when the webserver is toggled), make sure to change the time zone offset in the settings to . The module im using seems to be a bit finnicky, re-setting after not having power for a period of time. Because of this it is recommended to start the webserver briefly so it can sync and then turning the webserver off before leaving the system to run

Overall the code is'nt the prettiest, its also most likely not the best way to approach this task. However it works and gets the job done while keeping the power consumption to a minimum(to the best of my abilities)

The pins used for the system are:
* #### DS3231 RTC PINS
  * sda: 14
  * scl: 15
* #### MIRCOSD CARD READER PINS
  * miso: 16
  * cs: 17
  * sck: 18
  * mosi: 19
* #### SWITCH PINS
  * data: 21
* #### DHT11 PINS
  * data: 22
* #### OLED PINS
  * sda: 26
  * scl: 27
* #### ANEMOMETER PINS
  * data: 28
Power is supplied to the modules via the Pico's 3.3V pin and ground is supplied by any of the Pico's ground pins

---
# Settings.ini Documentation
[setting] - input type

#### Wi-Fi Settings
* Wi-Fi SSID - string
  * Name of the network the pico will connect to when the server is toggled
* Wi-Fi Pass - string
  * Password for aforementioned network name

#### NTP Settings
* Time Zone Offset - integer
  * Sets your current time zone, for example my time zone is GMT+2 therefore my offset will be 2
* NTP Server - string
  * Sets the server to get the current network protocol time (ntp). This should'nt need to be changed as [pool.ntp.org](pool.ntp.org) is the standard

#### RPM
* Threshold - integer
  * Changes the threshold for the edge detection
* Max Time Diff - integer
  * Sets the maximum allowed time between each edge, the higher the value the lower the rpm that the system can detect. Not to be confused with Timeout
* Timeout - integer
  * Sets the time that it takes with no edge updates before the rpm gets set to 0
* Update Interval - integer
  * Sets the delay between each display update
* Log Interval - integer
  * Sets the delay between each log to the data file

#### Other
* Debug - boolean
  * Toggles extra info for debugging (recommended set to false)
* File Type - string
  * Sets the file type of the data log output. Supported file types are: txt, csv

---
⚠️You are free to use these files as you wish. I do however ask that if you decide to re-upload it, please credit it me :)⚠️