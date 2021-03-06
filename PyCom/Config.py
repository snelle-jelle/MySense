# Replace with your own OTAA keys,
# obtainable through the "files" widget in Managed IoT Cloud.

# TTN register:
#          app id  ???, dev id ???
Network = 'TTN' # or 'WiFi'
# OTAA keys
dev_eui = "AAAAAA" # will be completed by dev hex serial nr
app_eui = "70123412341234D3"
app_key = "7912341234123412341234123412345B"
# ABP keys
# dev_addr  = "261234EF"
# nwk_swkey = "46123412341234123412341234123426"
# app_swkey = "27123412341234123412341234123404"

# wifi AP or Node
W_SSID = 'MySense-69F4'
W_PASS = 'GreenTechLab'

# power mgt of ttl/uarts OFF/on, i2c OFF/on and deep sleep minutes, 0 off
# Power = { 'ttl': False, 'i2c': False, 'sleep': 0 }
#  interval = { 'sample': 60,    # dust sample in secs
#             'interval': 15,     # sample interval in minutes
#             'gps':      3*60,  # location updates in minutes
#             'info':     24*60, # send kit info in minutes
#             'gps_next': 0,     # next gps update 0 OFF, 0.1 on
#  }

# MySense conf start modes: dflt: create configuration in flash on cold start
#    and will auto detect devices on ttl and i2c bus
#    nvs RAM is permanent in PyCom mem: change it with import pycom, and
#    pycom.nvs_set('modus',1) will reset ttl/i2c configurion, and force auto detect
#    pycom.nvs_set('modus',2) the archived configuratioin will be used
# device power management dflt: do not unless pwr pins defined
# power mgt of ttl/uarts OFF/on, i2c OFF/on and deep sleep minutes, 0 off
# display: None (always on), False: always off, True on/off during sleep
# Power = { 'ttl': False, 'i2c': False, 'sleep': 0, 'display': None }
# less energy use next

# define None if GPS is not used
# thisGPS = [0.0,0.0,0.0] # (LAT,LON,ALT) # GPS may overwrite this on startup
# Power = { 'ttl': True, 'i2c': True, 'sleep': True, 'display': False }

# calibration Taylor factors
# calibrate = None # or e.g. { 'temperature': [-6.2,1], 'pm1': [-20.0,0.5], ...}
# uncomment if calibration is known
# calibrate = {
#     "temperature": [0,1],
#     "humidity": [0,1],
#     "pressure": [0,1],
#     "gas": [0,1],
#     "gas base": 0+1.0*178644.6, # use gas calibration
#     "pm1": [0,1],
#     "pm25": [0,1],
#     "pm10": [0,1],
#}

# auto detect I2C address if module is wired/connected
# Meteo: BME280, BME680, SHT31
# meteo module is auto detected
# useMeteo = 'I2C'# I2C bus, None: disabled
M_gBase = 245343.0 # BME680 gas base line (dflt None or missing: recalculate)

# use oled display None: disabled
# useDisplay = True  # or 'I2C' enable display, dflt auto detect
# useDisplay = 'SPI' # if not on I2C bus
#  SPI pins, deprecated
# S_CLKI = 'P19'  # brown D0
# S_MOSI = 'P18'  # white D1
# S_MISO = 'P16'  # NC
#  SSD pins on GPIO
# S_DC   = 'P20'  # purple DC
# S_RES  = 'P21'  # gray   RES
# S_CS   = 'P17'  # blew   CS

# SDA wire is white, SCL wire is yellow
I2Cpins = [('P23','P22','P21')] # I2C pins [(SDA,SC,Pwr), ...]
# I2Cdevices = [ # dflt sensor I2C address for identification
#         ('BME280',0x76),('BME280',0x77), # BME serie Bosch incl 680
#         ('SHT31',0x44),('SHT31',0x45),   # Sensirion serie
#         ('SSD1306',0x3c)                 # oled display
#    ]

# uart allocations number from 0 (0,1,2) PCB label (TTL3,TTL2,TTL1)
# device/module: (yellow Rx, white Tx, red Pwr optional deflt None)
# UARTpins=[('P1','P0','P20'),('P4','P3',None),('P11','P10',None)] # default UART pins used by auto detect device
# omit to use P1/P0, used for console
UARTpins=[('P4','P3','P19'),('P11','P10','P9')] # default UART pins used by auto detect device

# useGPS = 'UART'      # None or False if not present, dflt True
# Dflt GPS dev wiring: Rx = 'P11' yellow, Tx = 'P10' white

# useDust = 'UART'     # UART, use False if not present, dflt True
# dust module uart: Rx = 'P4' yellow, Tx 'P3' white
# Dext = '' # only Plantower/Sensirion: '_cnt' for pcs/0.1 dm3 (dflt: ug/m3)
Dext = True   # send PM count PMnn_cnt to database server
# Dexplicit = True     # default, limited range, Sensirion count style
#             False      Plantower count style, PM count > size
