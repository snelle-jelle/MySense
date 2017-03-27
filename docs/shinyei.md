# Shinyei PPD42NS (Grove) dust sensor
## Hardware
Grove Shinyei PPD42NS dust sensor (€ 18.- Kiwi Electronics) is a PM10/PM2.5 particals counter. The module is 5VDC and output is also 5 VDC.
* Use Grove shield or volt regulator to coonect the module with the Pi.
Disadvantage: the Grove driver software will show zero counts without a resistor to tune the thresholt and fan to force a higher air stream.
Make sure you use the latest firmware of the GrovePi for this module: https://www.dexterindustries.com/GrovePi/get-started-with-the-grovepi/updating-firmware/
* Use Arduino as special dust controller with the Pi (the MySense choice). Advantage: the particle counter is more precise (no interrupts). The MySense software is using this approach.

Attach a fourth cable (white) to the cable sockets in order to use both dust sensing outputs. For wiring instrctions see the sketch MyArduino.ino.

## literature
There are many references as the Shinyei dust sensor is very popular. Mostly in compination with the Arduino controller.

* http://www.sca-shinyei.com/pdf/PPD42NS.pdf
* https://github.com/opendata-stuttgart/
* http://irq5.io/2013/07/24/testing-the-shinyei-ppd42ns/
* http://andypi.co.uk/2016/08/19/weather-monitoring-part-2-air-quality-sensing-with-shinyei-ppd42ns/ Pi+ug/m3 algorithm
* https://github.com/opendata-stuttgart/sensors-software/blob/master/BeginnersGuide/Guide.md
* https://openhomeautomation.net/connect-esp8266-raspberry-pi/
* https://oshlab.com/esp8266-raspberry-pi-gpio-wifi/
* https://github.com/aqicn/shinyei-lpo
* https://www.raspberrypi.org/forums/viewtopic.php?t=120926
* https://software.intel.com/en-us/iot/hardware/sensors/ppd42ns-dust-sensor
* http://iotdk.intel.com/docs/master/upm/python/_modules/pyupm_ppd42ns.html#PPD42NS
* https://github.com/intel-iot-devkit/upm/blob/master/examples/python/ppd42ns.py
import time, sys, signal, atexit

## Artduino firmware
Use the Arduino IDE (GUI) or commandline inotool http://inotool.org/ to compile, build and install the sketch MyArduino.ino into the Arduino controller. The Arduino controller is conneted with the PI via an normal USB cable.

For other controllers
* [ESP8266]https://www.raspberrypi.org/forums/viewtopic.php?f=32&t=122298&p=824523

## Shinyei PPD42 connector
You won't need the Grove board, the Shinyei sensor has digital outputs that the Pi can monitor

```
    1 : COMMON(GND)
    2 : OUTPUT(P2)
    3 : INPUT(5VDC 90mA)
    4 : OUTPUT(P1)
    5 : INPUT(T1)･･･FOR THRESHOLD FOR [P2] unused
```
The output is stated to be at 4V so a voltage divider is highly recommended to bring those down to 3V3 if you connect it to the Pi board!.

Connect as follows (you may need a breadboard)
```
Pi Pin 2 (or 4) (5V) connects to Shinyei pin 3 (5V input).
Pi Pin Gnd connects to Shinyei pin 1 (Common).
output uses voltage divider (or use a special V3.3-V5 converter (€ 1.25).
Pi Pin 6 (or 9, 14, 20, 25, 30, 34, 39) (Gnd) connects to a 3k3 resistor (voltage divider) the other end of which connects to Pi pin 16 (GPIO 23) (or any other GPIO pin of your choice) and to a 1k2 resistor, the other end of which is connected to Shinyei Pin 2 (output 2).
Pi Pin 6 (or 9, 14, 20, 25, 30, 34, 39) (Gnd) connects to a 3k3 resistor (voltage divider) the other end of which connects to Pi pin 18 (GPIO 24) (or any other GPIO pin of your choice) and to a 1k2 resistor, the other end of which is connected to Shinyei Pin 4 (output 1).
Pi Pin 6 (or 9, 14, 20, 25, 30, 34, 39) (Gnd) connects to a Variable resistor, the other end of which connectors to Pi pin 2 (or 4) (5V) and the wiper of which is connected to Shinyei Pin 5 (P2 threshold setting). Adjust the variable resistor to adjust the size of dust particle which triggers P2.
```
## MyArduino.ino firmware
The firware will output via USB to the Pi in string format as a json value:
```
{"version": "1.05","type": "PPD42NS","pm25_count":391645,"pm25_ratio":1.20,"pm25_pcs/0.01cf":623,"pm25_ug/m3":0.97,"pm10_count":2035010,"pm10_ratio":6.68,"pm10_pcs/0.01cf":3634,"pm10_ug/m3":5.67}
```
If the ratio is found 0 `null` values will be printed.
The firmware will provide per PM type three classes of values per sample time:
1. dust count and low ratio (0-100%).
2. count per sample time as particals per 0.01 square foot (count).
3. count per sample time as particles in ug/m3 (weight).

Default timings: The output will be on every `interval` secs time frame (default 60 seconds).
The samples are taken synchronously at every `sample time` frame (default 15 seconds).

The interval time can be on *request* timings: the Arduino will delay till a return is sent from the Pi.

Sending a string `C interval sample R<return>` to the Arduino will change the Arduino default configuration: interval in seconds, sample in seconds, R (use request interval timings). The Arduino will respond with an empty line if the configuration change has been succeeded. This allow to change interval and sample timings from the Pi at will.

## calibration
Literature show that the Shinyei sensor can be improved via the threshold resistor, using a fan to increase the air stream.
Literature shows also that humidity play a role in the dust size countings. So measure the temperature and huminity in the sensor box.

Make sure to calibrate the sensor against other dust sensors of a higher quality as eg a Dylos dust sensor. Make sure you clean up the dustsensor once an a while.

The MySense Shinyei/Arduino plugin will provaide handles to calibarte the sensor measurements.
