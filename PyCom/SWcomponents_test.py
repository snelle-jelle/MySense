# test kit with copy(<cntrl>shiftC)/paste(<cntrl>v) via REPL
# test suite helps to detect hw configuration and software problems
# one by one
# Copyright 2019, Teus Hagen, GPLV3
# xyz_test is operational test for xyz
# other parts are functional tests for MySense.py wrapper

# global settings
power = False       # use power management
doSleep = False     # use deepsleep function

from time import sleep

########## check I2C part
# basic functional test for hardware
import oled_test
import meteo_test

# I2C devices
# detect which devices Display
import whichI2C
I2Cobj = whichI2C.identifyI2C(identify=True,debug=True)

# check basic display init and functional tests
# Display = { 'use': None, 'enabled': False, 'fd': None}
I2Cobj.DISPLAY  # is display connected?
Display = I2Cobj.i2cDisplay
Display
print('Oled %s:' % Display['name'] + ' SDA~>%s, SCL~>%s, Pwr~>%s' % Display['pins'][:3], ' is %d' % I2Cobj.PwrI2C(Display['pins']))

import SSD1306 as DISPLAY # try display
Display['fd'] = DISPLAY.SSD1306_I2C(128,64,Display['i2c'], addr=Display['address'])
Display['fd'].fill(1); Display['fd'].show()
from time import sleep
sleep(1)
Display['fd'].fill(0); Display['fd'].show()
import sys
sys.exit() # reset

# I2C devices Meteo
import whichI2C
I2Cobj = whichI2C.identifyI2C(identify=True,debug=True)

# check basic meteo init and operational functions
# Meteo   = { 'use': None, 'enabled': False, 'fd': None}
I2Cobj.METEO
Meteo = I2Cobj.i2cMeteo
Meteo
print('Meteo %s:' % Meteo['name'] + ' SDA~>%s, SCL~>%s, Pwr~>%s' % Meteo['pins'][:3], ' is %d' % I2Cobj.PwrI2C(Meteo['pins']))

import BME_I2C as BME # try to get meteo data
Meteo['fd'] = BME.BME_I2C(Meteo['i2c'], address=Meteo['address'], debug=True, calibrate={})
# expect bus errors
Meteo['fd'].AQI
Meteo['fd'].temperature
import sys
sys.exit() # reset

########### check and test UART part
import dust_test
import gps_test

# UART devices which device is where connected
import whichUART
UARTobj = whichUART.identifyUART(identify=True,debug=True)
uarts = [None,'gps','dust']

# check dust device functions for MySense
# Dust = { 'use': None, 'enabled': False, 'fd': None}
Dust = UARTobj.devs['dust']
Dust
print('%s UART:' % Dust['name'] + ' SDA~>%s, SCL~>%s, Pwr~>%s' % Dust['pins'][:3], ' is ', UARTobj.PwrTTL(Dust['pins']))

from PMSx003 import PMSx003 as senseDust # get some data from device
sample_time = 60    # 60 seconds sampling for dust
# Dust['uart'] = UARTobj.openUART('dust') this does not work yet?
Dust['uart'] = uarts.index('dust')
Dust['fd'] = senseDust(port=Dust['uart'], debug=True, sample=sample_time, interval=0, pins=Dust['pins'][:2], calibrate={}, explicit=False)
UARTobj.PwrTTL(Dust['pins'],on=True) # power on
Dust['fd'].Normal() # fan on
Dust['fd'].Standby() # fan off
Dust['fd'].getData(debug=True)
UARTobj.PwrTTL(Dust['pins'],on=False)
import sys
sys.exit() # reset

# test with MySense, may see I2C errors
# depends on initDisplay(debug=True), will init display as well
import MySense  # has all functions
MySense.initDust(debug=True)
# ignore I2C bus errors
MySense.DoDust(debug=True)

# UART devices
import whichUART
UARTobj = whichUART.identifyUART(identify=True,debug=True) # all uart devices
uarts = [None,'gps','dust']

# check GPS functions for MySense
# Gps     = { 'use': None, 'enabled': False, 'fd': None}
Gps = UARTobj.devs['gps']
Gps
import GPS_dexter as GPS
print('%s UART:' % Gps['name'] + ' SDA~>%s, SCL~>%s, Pwr~>%s' % Gps['pins'][:3], ' is ', UARTobj.PwrTTL(Gps['pins']))
Gps['uart'] = uarts.index('gps')
Gps['fd'] = GPS.GROVEGPS(port=Gps['uart'],baud=9600,debug=True,pins=Gps['pins'][:2])
UARTobj.PwrTTL(Gps['pins'],on=True)
Gps['fd'].read() # get some valid records
Gps['fd'].date
Gps['fd'].timestamp
Gps['fd'].UpdateRTC()
round(float(Gps['fd'].longitude),5)
round(float(Gps['fd'].latitude),5)
round(float(Gps['fd'].altitude),1)
UARTobj.PwrTTL(Gps['pins'],on=False)

import sys
sys.exit() # reset

# test with MySense
# depends on initDisplay(debug=True)
import MySense
MySense.initGPS(debug=True)

######## LoRa tests
# Network = { 'use': None, 'enabled': False, 'fd': None}
import lora_test
import MySense
MySense.initNetwork(debug=True)
# depends on initNetwork(), initGps() and 'name' in Meteo and Dust dict
# Meteo = {'name':'','enabled': True} Dust = {'name':'None','enabled': True}
# Gps = {'enabled': True}
MySense.SendInfo(3) # send fake info

# to do
Accu    = { 'use': None, 'enabled': False, 'fd': None}

