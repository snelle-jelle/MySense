# PyCom Micro Python / Python 3
# Copyright 2018, Teus Hagen, ver. Behoud de Parel, GPLV4
# some code comes from https://github.com/TelenorStartIoT/lorawan-weather-station
# $Id: MySense.py,v 5.6 2019/05/01 19:22:01 teus Exp teus $
#
__version__ = "0." + "$Revision: 5.6 $"[11:-2]
__license__ = 'GPLV4'

import sys
from time import time, sleep
# Turn off hearbeat LED
from pycom import heartbeat, nvs_set, nvs_get
heartbeat(False)
import os
PyCom = 'PyCom %s' % os.uname().nodename
del os
LED = None
try:
  import led
  LED = led.LED()
except: pass
debug = True
wokeUP = False
StartUpTime = 0   # until RTC clock adjustment

MyConfig = None      # handle to ConfigJson object
MyConfiguration = {} # configuration stable between deepsleeps and power cycle
MyDevices = {} # dyn. part, has bus refs to device dict with conf
MyTypes = {}   # dyn. part, has type refs to device dict with conf
MyNames = [('meteo','i2c'),('display','i2c'),('dust','ttl'),('GPS','ttl'),('accu','pin'),('deepsleep','pin')]

from time import sleep_ms, time
import struct
from micropython import const
import _thread
# _thread.stack_size(6144)
NoThreading = False

LAT = const(0)
LON = const(1)
ALT = const(2)
# LoRa ports
# data port 2 old style and ug/m3, 4 new style grain, pm4/5 choice etc
Dprt = (2,4)    # data ports
Iprt = const(3) # info port, meta data

# oled is multithreaded
STOP = False
STOPPED = False
HALT = False  # stop by remote control

# return bus or if bus [type(s)]
def Type2Bus(atype): # and visa versa
  global MyNames
  rts = []
  for item in MyNames:
    if (atype == item[1]) and (not atype in rts): rts.append(item[0])
    elif atype == item[0]: return item[1]
  return rts
def Type2Dev(atype):
  global MyTypes, MyDevices
  try: return MyDevices[Type2Bus(atype)][atype]
  except: return None

def PrintDict(adict = None, header=''):
  if not debug: return
  global MyConfiguration, MyDevices
  if adict != None:
    print("dict '%s'->" % header)
    for item in adict.items():
      try: print("    '%s'-> %s" % (item[0], str(item[1])))
      except: pass
  else:
    PrintDict(MyConfiguration,'MyConfiguration')
    PrintDict(MyDevices,'MyDevices')

# identity PyCom SN
def getSN():
  from machine import unique_id
  import binascii
  SN = binascii.hexlify(unique_id()).decode('utf-8')
  return SN

# Read accu voltage out
def getVoltage(): # range 0 (None) and 11.4 (low) - 12.5 (high)
  global MyDevices, MyConfig, MyDevices, MyTypes
  if not MyConfig: initConfig(); atype = 'accu'
  try:
    if not 'accuPin' in MyConfiguration.keys():
      accuPin = 'P17'
      try: from Config import accuPin
      except: pass
      MyConfig.dump('accuPin',accuPin)
      MyConfiguration['accupin'] = accuPin
    else: accuPin = MyConfiguration['accuPin']
    if not atype in MyDevices.keys():
      from machine import ADC
      MyTypes['accu'] = MyDevices['accu'] = { 'lib': ADC(0).channel(pin=accuPin, attn=ADC.ATTN_11DB)}
    rts =  MyDevices[atype]['lib'].value()*0.004271845
    return (rts if rts > 0.1 else 0)
  except: return 0

# sleep phases all active till config done after cold start, then:
#    sleep pin not set & power sleep False: sleep, rgb led, wifi
#    pin set & power sleep False: deepsleep, while active: rgb led, wifi on
#    pin set & power sleep True: deepsleep, while active: no rgb led, wifi off
# clear config in flash on: cold start & no accu attached & no sleep pin

# get deepsleep pin value
def deepsleepMode():
  global MyDevices, MyConfig, MyConfiguration, MyTypes
  if not MyConfig: initConfig(); atype = 'deepsleep'
  try:
    if not 'sleepPin' in MyConfiguration.keys():
      sleepPin = 'P18'
      try: from Config import sleepPin
      except: pass
      MyConfig.dump('sleepPin',sleepPin)
      MyConfiguration['sleepPin'] = sleepPin
    else: sleepPin = MyConfiguration['sleepPin']
    if not atype in MyDevices.keys():
      from machine import Pin
      MyTypes[atype] = MyDevices[atype] = { 'lib': Pin(sleepPin,mode=Pin.IN), 'type': atype}
    return not MyDevices[atype]['lib'].value()
  except: return False

## configuration from flash
def initConfig(debug=False):
  global MyConfiguration, MyConfig
  global wokeUp

  if MyConfig: return
  import ConfigJson
  MyConfig = ConfigJson.MyConfig(debug=debug)
  MyConfiguration = MyConfig.getConfig()

  from machine import deepsleep, wake_reason, PWRON_WAKE
  wokeUp = wake_reason()[0] != PWRON_WAKE

## CONF pins
def getPinsConfig(debug=False):
  global MyConfiguration, MyConfiguration
  global MyConfig
  if not MyConfig: initConfig()
  ## CONF accu
  deepsleepMode() # pins init
  ## CONF clear
  if (not getVoltage()) and deepsleepMode():
    if not wokeUp: # cold restart
      # no accu & deepsleep pin present
      print("Clear config in flash")
      MyConfig.clear; MyConfig = None; MyConfiguration = {}
      initConfig(debug=debug) 
      MyDevices = {}
      getVoltage(); deepsleepMode();

## CONF busses
def getBusConfig(busses=['i2c','ttl'], devices=None, debug=False):
  global MyConfig
  global MyConfiguration, MyDevices, MyTypes

  if not MyConfig: initConfig()
  if debug:
    PrintDict(MyConfiguration,'Start: Archived configuration')
    PrintDict(MyDevices,'My Devices')
  for abus in busses:
    if not abus in MyConfiguration.keys(): MyConfiguration[abus] = {}
    FndDevices = []
    if devices == None: busdevices = Type2Bus(abus) # use dflt
    else: busdevices = devices
    if debug: print("bus %s with devices: %s" % (abus, str(busdevices)))
    for dev in MyConfiguration[abus].keys():
      if not dev in busdevices: continue
      FndDevices.append(dev)
      if debug: print("Reuse dev %s config: %s" % (dev, str(MyConfiguration[abus][dev]))) 
    if abus == 'i2c': import whichI2C as which
    elif abus == 'ttl': import whichUART as which
    # PrintDict(MyConfiguration[abus],'MyConfiguration[%s]' % abus)
    which = which.identification(identify=True, config=MyConfiguration[abus], debug=debug)
    for atype in MyConfiguration[abus].keys():
      if not atype in busdevices: continue
      if not atype in FndDevices:
        if debug: print("New dev %s config: %s" % (atype, str(MyConfiguration[abus][atype])))
        MyConfig.dump(atype, MyConfiguration[abus][atype],abus=abus)
      if not abus in MyDevices.keys(): MyDevices[abus] = {}
      MyDevices[abus][atype] = which.getIdent(atype=atype)
      MyDevices[abus][atype]['type'] = atype
      MyTypes[atype] = MyDevices[abus][atype]
      # PrintDict(MyDevices[abus][atype],'MyDevices[%s][%s]' % (abus,atype))
      if 'conf' in MyDevices[abus].keys():
        print("WARNING found 'conf' in MyDevices[%s]" % abus)
        del MyDevices[abus] # strange

## CONF network
def getNetConfig(debug=False):
  global MyConfiguration, MyConfig, MyDevices, MyTypes
  global wokeUp

  if not MyConfig: initConfig()
  Network = 'TTN' # dflt
  if 'LoRa' in MyConfiguration.keys(): Network = 'TTN'
  if not wokeUp:
    try: from Config import Network
    except: pass
  if not Network in ['TTN', None]: raise ValueError("%s not supported" % Network)
  
  if Network == 'TTN':
    atype = 'lora'; MyDevices[atype] = { 'name': Network, 'type': atype }
    from lora import LORA
    MyDevices[atype]['lib'] = LORA()
    MyDevices[atype]['init'] = not wokeUp
    # 'LoRa' in config: use lora.vram
    if MyConfig.getConfig('LoRa') in ['ABP','OTAA']:
      if debug: print("ABP LoRa info should be present in vram")
      MyDevices[atype]['init'] = False
    #else: MyDevices[atype]['lib'].cleanup # will clear LoRa
  
    info = None
    MyDevices[atype]['method'] = {}
    if not MyDevices[atype]['init']: # no keys in vram or set them
      try: # OTAA keys preceeds ABP
        from Config import dev_eui, app_eui, app_key
        MyDevices[atype]['method']['OTAA'] = (dev_eui, app_eui, app_key)
        MyConfig.dump('LoRa','OTAA')
      except: pass
      try: # ABP keys
        from Config import dev_addr, nwk_swkey, app_swkey
        MyDevices[atype]['method']['ABP'] = (nwk_swkey, nwk_swkey, app_swkey)
        MyConfig.dump('LoRa','ABP')
      except: pass
      if not len(MyDevices[atype]['method']):
        raise ValueError("No LoRa keys configured or LoRa config error")
      if debug: print("Init LoRa methods: %s." % ', '.join(MyDevices[atype]['method'].keys()))
      MyConfiguration['LoRa'] = MyConfig.restore('LoRa')
    elif debug: print("Using LoRa info from vram")
    MyTypes['network'] = MyDevices[atype]
    if wokeUp: info = True # no need to send meta data
  else: None # no output
  
def getGlobals(debug=False):
  global MyConfiguration, MyConfig
  if not MyConfig: initConfig()
  ## CONF interval
  if not 'interval' in MyConfiguration:
    try: from Config import interval
    except:
      MyConfiguration['interval'] = { 'sample': 60,    # dust sample in secs
             'interval': 15,     # sample interval in minutes
             'gps':      3*60,  # location updates in minutes
             'info':     24*60, # send kit info in minutes
      }
    finally:
      for item in ['interval','gps','info']:
        MyConfiguration['interval'][item] *= 60
        MyConfiguration['interval']['interval'] -= MyConfiguration['interval']['sample']
        if MyConfiguration['interval']['interval'] <= 0:
          MyConfiguration['interval']['interval'] = 0.1
    MyConfig.dump('interval',MyConfiguration['interval'])
  # item for next time to send info
  for item in ['gps_next','info_next']:
    if not wokeUp:
      MyConfiguration['interval'][item] = 0
      nvs_set(item,0)
    else:
      value = nvs_get(item)
      if value == None:
        nvs_set(item,0); value = 0
      MyConfiguration['interval'][item] = value
  
  ## CONF power mgt
  # device power management dflt: do not unless pwr pins defined
  # power mgt of ttl/uarts OFF/on, i2c OFF/on and deep sleep minutes, 0 off
  # display: None (always on), False: always off, True on and off during sleep
  # To Do: sleep pin P18 use deep sleep or delete config json file
  if not 'power' in MyConfiguration.keys():
    try: from Config import Power
    # deflt: no power mgt on ttl, i2c, display power mngt is used
    except:
      if deepsleepMode():
        MyConfiguration['power'] = { 'ttl': True, 'i2c': True, 'sleep': True, 'display': None }
      else:
        MyConfiguration['power'] = { 'ttl': False, 'i2c': False, 'sleep': False, 'display': None }
    if not wokeUp: MyConfig.dump('power', MyConfiguration['power'])
  # sleep dflt True: listen to pin mode
  
  ## CONF calibrate
  if not 'calibrate' in MyConfiguration.keys():
    # calibrate dict with lists for sensors { 'temperature': [0,1], ...}
    try: from Config import calibrate
    except: MyConfiguration['calibrate'] = {}      # sensor calibration Tayler array
    if not wokeUp: MyConfig.dump('calibrate',MyConfiguration['calibrate'])
  
  ## CONF dflt location
  if not 'thisGPS' in MyConfiguration.keys():
    try: from Config import thisGPS # predefined GPS coord
    # location
    except: MyConfiguration['thisGPS'] = [0.0,0.0,0.0] # completed by GPS
    finally:
      MyConfig.dump('thisGPS',MyConfiguration['thisGPS'])
      thisGPS = MyConfiguration['thisGPS']
      lastGPS = thisGPS[0:]
      if MyConfiguration['interval']['gps_next']:
        MyConfiguration['interval']['gps_next'] = 0.1

## oled display routines
def oledShow():
  global MyTypes
  try:
    Display = MyTypes['display']
    if not Display['lib']: return
    if not Display['conf']['use'] or not Display['enabled']: return
  except: return
  for cnt in range(0,4):
    try:
      Display['lib'].show()
      break
    except OSError as e: # one re-show helps
      if cnt: print("show err %d: " % cnt,e)
      sleep_ms(500)

nl = 16 # line height
LF = const(13)
# text display, width = 128; height = 64  # display sizes
def display(txt,xy=(0,None),clear=False, prt=True):
  global MyTypes, nl
  if not MyTypes: getMyConfig()
  try:
    Display = MyTypes['display']
    if not Display['lib']: initDisplay()
  except: return
  if Display['enabled'] and Display['conf']['use'] and Display['lib']:
    offset = 0
    if xy[1] == None: y = nl
    elif xy[1] < 0:
      if -xy[1] < LF:
        offset = xy[1]
        y = nl - LF
    else: y = xy[1]
    x = 0 if ((xy[0] == None) or (xy[0] < 0)) else xy[0]
    if clear:
      Display['lib'].fill(0)
    if y > 56:
      nl =  y = 16
    if (not offset) and (not clear):
      rectangle(x,y,128,LF,0)
    Display['lib'].text(txt,x,y+offset)
    oledShow()
    if y == 0: nl = 16
    elif not offset: nl = y + LF
    if nl >= (64-13): nl = 16
  if prt: print(txt)

def rectangle(x,y,w,h,col=1):
  global MyTypes
  try: Display = MyTypes['display']
  except: return
  if not Display['conf']['use'] or not Display['enabled']: return
  dsp = Display['lib']
  if not dsp: return
  ex = int(x+w); ey = int(y+h)
  if ex > 128: ex = 128
  if ey > 64: ey = 64
  for xi in range(int(x),ex):
    for yi in range(int(y),ey):
      dsp.pixel(xi,yi,col)

def ProgressBar(x,y,width,height,secs,blink=0,slp=1):
  global LED, STOP
  if x+width >= 128: width = 128-x
  if y+height >= 64: height = 64-y
  rectangle(x,y,width,height)
  if (height > 4) and (width > 4):
    rectangle(x+1,y+1,width-2,height-2,0)
    x += 2; width -= 4;
    y += 2; height -= 4
  elif width > 4:
    rectangle(x+1,y,width-2,height,0)
    x += 2; width -= 4;
  else:
    rectangle(x,y,width,height,0)
  step = width/(secs/slp); xe = x+width; myslp = slp
  if blink: myslp -= (0.1+0.1)
  for sec in range(int(secs/slp+0.5)):
    if STOP:
      return False
    if blink:
      if LED: LED.blink(1,0.1,blink,l=False)
    sleep_ms(int(myslp*1000))
    if x > xe: continue
    rectangle(x,y,step,height)
    oledShow()
    x += step
  return True

def showSleep(secs=60,text=None,inThread=False):
  global nl, STOP, STOPPED
  global MyTypes
  try:
    Display = MyTypes['display']
    ye = y = nl
    if text:
      display(text)
      ye += LF
    if Display['lib'] and Display['enabled'] and Display['conf']['use']:
      ProgressBar(0,ye-3,128,LF-3,secs,0x004400)
      nl = y
      rectangle(0,y,128,ye-y+LF,0)
      oledShow()
    else: raise ValueError()
  except: sleep_ms(int(secs*1000))
  if inThread:
    STOP = False
    STOPPED = True
    _thread.exit()
  return True

def SleepThread(secs=60, text=None):
  global STOP, NoThreading
  if NoThreading:
    display('waiting ...')
    raise OSError
  STOP = False; STOPPED = False
  try:
    _thread.start_new_thread(showSleep,(secs,text,True))
  except Exception as e:
    print("threading failed: %s" % e)
    STOPPED=True
    NoThreading = True
  sleep_ms(1000)
# end of display routines

# check/set power on device
def PinPower(atype=None,on=None,debug=False):
  global MyConfiguration
  if not atype: return False
  if type(atype) is list:
    for item in atype: PinPower(atype=item, on=on, debug=debug)
  else:
    abus = Type2Bus(atype)
    try:
      pins = MyConfiguration[abus][atype]['pins']
      len(pins) == 3
      if debug: print("Use %s power pins %s" % (atype,pins))
    except: raise ValueError("Power pin %s missing" % atype)
    if not type(pins[2]) is str: return None
    from machine import Pin
    pin = Pin(pins[2], mode=Pin.OUT)
    if on:
      if pin.value(): return True
      if debug: print("Activate %d chan (Tx,Rx,Pwr)=%s: " % (abus,str(pins)))
      pin.value(1); sleep_ms(200); return False
    elif on == None: return pin.value()
    elif pin.value():
      if debug: print("Deactivate %d chan (Tx,Rx,Pwr)=%s: " % (abus,str(pins)))
      pin.value(0); return True
      pin.value(0); return True
    else: return False

## I2C devices
## DISPLAY
# tiny display Adafruit SSD1306 128 X 64 oled driver
def initDisplay(debug=False):
  global MyTypes
  atype = 'display'
  if not MyTypes: getMyConfig()
  try: Display = MyTypes[atype]
  except: return False
  abus = Type2Bus(atype)
  if Display['lib']: return True
  try:
    if not Display[abus]: return False
    if not Display['conf']['name'][:3] in ['SSD',]: return False
  except: return False
  if PinPower(atype=atype,on=True, debug=debug) == None: return False
  if not Display['conf']['use']: return True  # initialize only once
  Display['enable'] = False
  try:
      import SSD1306 as DISPLAY
      width = 128; height = 64  # display sizes
      # display may flicker on reload
      Display['lib'] = DISPLAY.SSD1306_I2C(width,height,
                             Display['i2c'], addr=Display['conf']['address'])
      if debug:
        print('Oled %s: (SDA,SCL,Pwr)=%s pwr is %s' % (Display['conf']['name'],str(Display['conf']['pins'][:3]),PinPower('display')))
      #elif 'spi' in Display.keys(): # for fast display This needs rework for I2C style
      #  global spi, spiPINS
      #  try:
      #    from Config import S_CLKI, S_MOSI, S_MISO  # SPI pins config
      #  except:
      #    S_SCKI = 'P10'; S_MOSI = 'P11'; S_MISO = 'P14'  # SPI defaults
      #  if not len(spi): from machine import SPI
      #  try:
      #    from Config import S_DC, S_RES, S_CS      # GPIO SSD pins
      #  except:
      #    S_DC = 'P5'; S_RES = 'P6'; S_CS = 'P7'    # SSD defaults
      #  nr = SPIdevs(spiPINs,(S_DC,S_CS,S_RES,S_MOSI,S_CLKI))
      #  if spi[nr] == None:
      #    spi[nr] = SPI(nr,SPI.MASTER, baudrate=100000,
      #                  pins=(S_CLKI, S_MOSI, S_MISO))
      #  Display['lib'] = DISPLAY.SSD1306_SPI(width,height,spi[nr],
      #                  S_DC, S_RES, S_CS)
      #  if debug: print('Oled SPI %d: ' % nr + 'DC ~> %s, CS ~> %s, RES ~> %s,
      #                   MOSI/D1 ~> %s,
      #                   CLK/D0 ~> %s ' % spiPINs[nr] + 'MISO ~> %s' % S_MISO)
      else:
        Display['lib'] = None; Display['conf']['use'] = False
        print("No SSD display or bus found")
      if Display['lib']:
        Display['enabled'] = True
        Display['lib'].fill(1); oledShow(); sleep_ms(200)
        Display['lib'].fill(0); oledShow()
  except Exception as e:
      Display['lib'] = None
      print('Oled display failure: %s' % e)
      return False
  return True

## METEO
# oled on SPI creates I2C bus errors
#  display('BME280 -> OFF', (0,0),True)

# start meteo sensor
def initMeteo(debug=False):
  global MyTypes, MyConfiguration
  if not MyTypes: getMyConfig()
  try:
    atype = 'meteo'
    Meteo = MyTypes[atype]
    abus = Type2Bus(atype)
    if Meteo['lib']: return True
    if not Meteo[abus]: return False
    if not Meteo['conf']['name'][:3] in ['BME','SHT']: return False
    if not Meteo['conf']['use']: return False
  except: return False
  try:
    if Meteo['lib']: return True
  except: pass
  if debug: print("Try %s" % Meteo['conf']['name'])
  Meteo['enabled'] = False
  try: # get lib
    if Meteo['conf']['name'][:3] == 'BME':
      if Meteo['conf']['name'] == 'BME280':
        import BME280 as BME
        Meteo['lib'] = BME.BME_I2C(Meteo[abus], address=Meteo['conf']['address'], debug=debug, calibrate=MyConfiguration['calibrate'])
      elif Meteo['conf']['name'] == 'BME680':
        import BME_I2C as BME
        Meteo['lib'] = BME.BME_I2C(Meteo[abus], address=Meteo['conf']['address'], debug=debug, calibrate=MyConfiguration['calibrate'])
        if not 'gas_base' in Meteo['conf'].keys():
          try:
            from Config import M_gBase
            Meteo['conf']['gas_base'] = int(M_gBase)
          except: pass
          if 'gas_base' in Meteo['conf'].keys():
            Meteo['lib'].gas_base = Meteo['conf']['gas_base']
          if not Meteo['lib'].gas_base:
            global MyConfig
            display('AQI wakeup')
            Meteo['lib'].AQI # first time can take a while
            Meteo['gas_base'] = Meteo['lib'].gas_base
            MyConfig.dump(atype,MyConfiguration[atype],abus=abus)
          display("Gas base: %0.1f" % Meteo['lib'].gas_base)
          # Meteo['lib'].sea_level_pressure = 1011.25
      else: return False
    elif Meteo['conf']['name'][:3] == 'SHT':
      import Adafruit_SHT31 as SHT
      Meteo['lib'] = SHT.SHT31(address=Meteo['address'], i2c=Meteo[abus], calibrate=MyConfiguration['calibrate'])
    else: # DHT serie deprecated
      if LED: LED.blink(5,0.3,0xff0000,l=True,force=True)
      raise ValueError("Unknown meteo %s type" % meteo)
    Meteo['enabled'] = True
    if debug:
      print('Meteo %s: (SDA,SCL,Pwr)=%s, Pwr %s' % (Meteo['conf']['name'],Meteo['conf']['pins'][:3], PinPower(atype=atype)))
  except Exception as e:
    Meteo['conf']['use'] = False
    display("meteo %s failure" % Meteo['conf']['name'], (0,0), clear=True)
    print(e)
  if (not Meteo['enabled']) or (not Meteo['conf']['use']):
    display("No meteo in use")
    return False
  return True

TEMP = const(0)
HUM  = const(1)
PRES = const(2)
GAS  = const(3)
AQI  = const(4)
def DoMeteo(debug=False):
  global MyTypes, LED
  global nl, LF
  if not MyTypes:
    getMyConfig(debug=debug)
    initMeteo(debug=debug)
  atype = 'meteo'
  try: Meteo = MyTypes[atype]
  except: return

  def convertFloat(val):
    return (0 if val is None else float(val))

  mData = [None,None,None,None,None]
  if Meteo['lib'] == None: initMeteo(debug=debug)
  if (not Meteo['conf']['use']) or (not Meteo['enabled']): return mData

  # Measure BME280/680: temp oC, rel hum %, pres pHa, gas Ohm, aqi %
  if LED: LED.blink(3,0.1,0x002200,l=False); prev = 1
  try:
    prev = PinPower(atype=atype,on=True, debug=debug)
    if (Meteo['conf']['name'] == 'BME680') and (not Meteo['lib'].gas_base): # BME680
      display("AQI base: wait"); nl -= LF
    #Meteo['i2c'].init(nr, pins=Meteo['conf']['pins']) # SPI oled causes bus errors
    #sleep_ms(100)
    mData = []
    for item in range(0,5):
        mData.append(0)
        for cnt in range(0,5): # try 5 times to avoid null reads
            try:
                if item == TEMP: # string '20.12'
                    mData[TEMP] = convertFloat(Meteo['lib'].temperature)
                elif item == HUM: # string '25'
                    mData[HUM] = convertFloat(Meteo['lib'].humidity)
                elif Meteo['conf']['name'][:3] != 'BME': break
                elif item == PRES: # string '1021'
                    mData[PRES] = convertFloat(Meteo['lib'].pressure)
                elif Meteo['conf']['name'] == 'BME680':
                    if item == GAS: mData[GAS] = convertFloat(Meteo['lib'].gas)
                    elif item == AQI:
                        mData[AQI] = round(convertFloat(Meteo['lib'].AQI),1)
                        if not 'gas_base' in Meteo.keys():
                            Meteo['gas_base'] = Meteo['lib'].gas_base
                break
            except OSError as e: # I2C bus error, try to recover
                print("OSerror %s on data nr %d" % (e,item))
                Meteo['i2c'].init(I2C.MASTER, pins=Meteo['conf']['pins'])
                if LED: LED.blink(1,0.1,0xff6c00,l=False,force=True)
    # work around if device corrupts the I2C bus
    # Meteo['i2c'].init(I2C.MASTER, pins=Meteo['conf']['pins'])
    sleep_ms(500)
    rectangle(0,nl,128,LF,0)
  except Exception as e:
    display("%s ERROR: " % Meteo['conf']['name'])
    print(e)
    if LED: LED.blink(5,0.1,0xff00ff,l=True,force=True)
    return [None,None,None,None,None]

  if LED: LED.off
  # display results
  nl += 6  # oled spacing
  if Meteo['conf']['name'] == 'BME680':
    title = "  C hum% pHa AQI"
    values = "% 2.1f %2d %4d %2d" % (round(mData[TEMP],1),round(mData[HUM]),round(mData[PRES]),round(mData[AQI]))
  elif Meteo['conf']['name'] == 'BME280':
    title = "    C hum%  pHa"
    values = "% 3.1f  % 3d % 4d" % (round(mData[TEMP],1),round(mData[HUM]),round(mData[PRES]))
  else:
    title = "    C hum%"
    values = "% 3.1f  % 3d" % (round(mData[TEMP],1),round(mData[HUM]))
  display(title)
  display("o",(12,-5),prt=False)
  display(values)
  if not prev: PinPower(atype=atype,on=prev,debug=debug)
  return mData # temp, hum, pres, gas, aqi

# UART devices
## DUST
def initDust(debug=False):
  global MyConfig, MyConfiguration
  global MyTypes
  if not MyTypes: getMyConfig()
  atype = 'dust'; abus = Type2Bus(atype)
  try: Dust = MyTypes[atype]
  except: return False

  try:
    if Dust['lib']: return True
    if not Dust[abus]: return False
    if not Dust['conf']['name'][:3] in ['SDS','PMS','SPS']: return False
  except: return False
  try: sample = MyConfiguration['interval']['sample']
  except: sample = 60
  Dust['enabled'] = False
  if Dust['conf']['use']:
    # initialize dust: import dust library module
    try:
      if Dust['conf']['name'][:3] == 'SDS':    # Nova
        from SDS011 import SDS011 as senseDust
      elif Dust['conf']['name'][:3] == 'SPS':  # Sensirion
        from SPS30 import SPS30 as sensedust
      elif Dust['conf']['name'][:3] == 'PMS':  # Plantower
        from PMSx003 import PMSx003 as senseDust
      else:
        if LED: LED.blink(5,0.3,0xff0000,l=True,force=True)
        raise ValueError("Unknown dust sensor")
      for item in ['Dext','explicit']:
        Dust[item] = False # dflt do show PM cnt
        try: Dust[item] = Dust['conf'][item]
        except:
          try:
            if item == 'Dext': from Config import Dext as value
            elif item == 'explicit': from Config import Dexplicit as value
            else: continue
            Dust[item] = Dust['conf'][item] = value
            if value != None:
              MyConfig.dump(atype=atype,avalue=MyConfiguration[abus][atype],abus=abus)
          except: Dust[item] = True
      # #pcs=range(PM0.3-PM) + average grain size, True #pcs>PM
      if Dust[abus] == None: return False
      Dust['lib'] = senseDust(port=Dust[abus], debug=debug, sample=sample, interval=0, pins=Dust['conf']['pins'][:2], calibrate=MyConfiguration['calibrate'], explicit=Dust['explicit'])
      if debug:
        print('Dust %s: (Tx,Rx,Pwr)=%s, Pwr %s' % (Dust['conf']['name'],Dust['conf']['pins'][:3], PinPower(atype=atype)))
    except Exception as e:
      display("%s failure" % Dust['conf']['name'], (0,0), clear=True)
      print(e)
      Dust['conf']['name'] = ''
    if debug: print('dust: %s' % Dust['conf']['name'])
  elif debug: print("No dust in use")
  if Dust['lib']: Dust['enabled'] = True
  return Dust['conf']['use']

# PM weights
PM1 = const(0)
PM25 = const(1)
PM10 = const(2)
# PM count >= size
PM03c = const(3)
PM05c = const(4)
PM1c = const(5)
PM25c = const(6)
PM5c = const(7)
PM10c = const(8)
def DoDust(debug=False):
  global nl, STOP, STOPPED, Gps, lastGPS
  global MyConfiguration, MyTypes
  atype = 'dust'
  if not MyTypes:
    getMyConfig(debug=debug)
    initDust(debug=debug)
  try: Dust = MyTypes[atype]
  except: return


  dData = {}; rData = [None,None,None]
  if Dust['lib'] == None: initDust(debug=debug)
  if (not Dust['conf']['use']) or (not Dust['enabled']): return rData

  display('PM sensing',(0,0),clear=True,prt=False)
  prev = False
  if Dust['enabled']:
    prev = PinPower(atype='dust',on=True, debug=debug)
    if not prev:
        sleep_ms(1000)
        Dust['lib'].Standby()
    if Dust['lib'].mode != Dust['lib'].NORMAL:
      Dust['lib'].Normal()
      if not showSleep(secs=15,text='starting up fan'):
        display('stopped SENSING', (0,0), clear=True)
        if LED: LED.blink(5,0.3,0xff0000,l=True,force=True)
        return rData
      else:
        if Gps['enabled']:
          display("G:%.4f/%.4f" % (lastGPS[LAT],lastGPS[LON]))
        display('measure PM')
  if Dust['enabled']:
    if LED: LED.blink(3,0.1,0x005500)
    # display('%d sec sample' % interval['sample'],prt=False)
    try:
      STOPPED = False
      try:
        SleepThread(interval['sample'],'%d sec sample' % MyConfiguration['interval']['sample'])
      except:
        STOPPED = True
        display('%d sec sample' % MyConfiguration['interval']['sample'])
      dData = Dust['lib'].getData()
      for cnt in range(10):
        if STOPPED: break
        STOP = True
        print('waiting for thread')
        sleep_ms(2000)
      STOP = False
    except Exception as e:
      display("%s ERROR" % Dust['conf']['name'])
      print(e)
      if LED: LED.blink(3,0.1,0xff0000)
      dData = {}
    if LED: LED.blink(3,0.1,0x00ff00)
    if MyConfiguration['power'][abus]: PinPower(atype='dust',on=prev,debug=debug)

  if len(dData):
    for k in dData.keys():
        if dData[k] == None: dData[k] = 0
    try:
      if 'pm1' in dData.keys():   #  and dData['pm1'] > 0:
        display(" PM1 PM2.5 PM10", (0,0), clear=True)
        display("% 2.1f % 5.1f% 5.1f" % (dData['pm1'],dData['pm25'],dData['pm10']))
      else:
        display("ug/m3 PM2.5 PM10", (0,0), clear=True)
        display("     % 5.1f % 5.1f" % (dData['pm25'],dData['pm10']))
        dData['pm1'] = 0
    except:
      dData = {}
  if (not dData) or (not len(dData)):
    display("No PM values")
    if LED: LED.blink(5,0.1,0xff0000,l=True,force=True)
  else:
    rData = []
    for k in ['pm1','pm25','pm10']:
      rData.append(round(dData[k],1) if k in dData.keys() else None)

    if Dust['cnt']:
      cnttypes = ['03','05','1','25','5','10']
      if Dust['conf']['name'][:3] == 'SPS': cnttypes[4] = '4'
      for k in cnttypes:
        if 'pm'+k+'_cnt' in dData.keys():
            rData.append(round(dData['pm'+k+'_cnt'],1))
        else: rData.append(0.0) # None
      if not Dust['expl']:  # PM0.3 < # pcs <PMi
        rData[3] = round(dData['grain'],2) # PM0.3 overwritten
        # print('pm grain: %0.2f' % dData['grain'])
    if LED: LED.off
  return rData

## GPS
# initialize GPS: GPS config tuple (LAT,LON,ALT)
def initGPS(debug=False):
  global lastGPS, thisGPS
  global MyTypes
  if not MyTypes: getMyConfig()
  atype = 'gps'; abus = Type2Bus(atype)
  try: Gps = MyTypes[atype]
  except: return False

  try:
    if Gps['lib']: return True
    if not Gps[abus]: return False
    if not Gps['conf']['use']:
      display('No GPS'); return False
    if not Gps['conf']['name'][:3] in ['GPS','NEO',]: return False
  except: return False

  Gps['enabled'] = False; Gps['lib'] = None; Gps['rtc'] = None
  try:
      import GPS_dexter as GPS
      Gps['lib'] = GPS.GROVEGPS(port=Gps[abus],baud=9600,debug=debug,pins=Gps['conf']['pins'][:2])
      if debug:
        print('GPS %s: (Tx,Rx,Pwr)=%s, Pwr %s' % (Gps['conf']['name'],Gps['conf']['pins'][:3], PinPower(atype='gps')))
      Gps['enabled'] = True
      myGPS = DoGPS(debug=debug)
      if myGPS != None: lastGPS = myGPS
      Gps['rtc'] = None
  except Exception as e:
      display('GPS failure', (0,0), clear=True)
      print(e)
      Gps['enabled'] = False; Gps[abus].ser.deinit(); Gps['lib'] = None
  return Gps['enabled']

# returns distance in meters between two GPS coodinates
# hypothetical sphere radius 6372795 meter
# courtesy of TinyGPS and Maarten Lamers
# should return 208 meter 5 decimals is diff of 11 meter
# GPSdistance((51.419563,6.14741),(51.420473,6.144795))
def GPSdistance(gps1,gps2):
  global LAT, LON
  from math import sin, cos, radians, pow, sqrt, atan2
  delta = radians(gps1[LON]-gps2[LON])
  sdlon = sin(delta)
  cdlon = cos(delta)
  lat = radians(gps1[LAT])
  slat1 = sin(lat); clat1 = cos(lat)
  lat = radians(gps2[LAT])
  slat2 = sin(lat); clat2 = cos(lat)

  delta = pow((clat1 * slat2) - (slat1 * clat2 * cdlon),2)
  delta += pow(clat2 * sdlon,2)
  delta = sqrt(delta)
  denom = (slat1 * slat2) + (clat1 * clat2 * cdlon)
  return int(round(6372795 * atan2(delta, denom)))

def LocUpdate(debug=False):
  global Gps, UARTobj
  global Gps, lastGPS, thisGPS
  if not DoGPS(debug=debug): return lastGPS[0:]
  if GPSdistance(thisGPS,lastGPS) <= 50.0:
    return None
  lastGPS = thisGPS[0:]
  return thisGPS

def DoGPS(debug=False):
  global thisGPS
  global MyConfiguration, MyConfig, MyTypes
  global StartUpTime
  if not MyTypes:
    getMyConfig(debug=debug)
    initGPS(debug=debug)
  atype = 'gps'; abus = Type2Bus(atype)
  try: Gps = MyTypes[atype]
  except: return

  if not MyTypes: getMyConfig(debug=debug)
  interval = MyConfiguration['interval']

  if Gps['lib'] == None: initGPS(debug=debug)
  if not Gps['lib'] or not Gps['enabled']: return None
  from time import localtime, timezone
  if (time()-StartUpTime) <= interval['gps_next']:
    if debug: print("No GPS update")
    return None
  if debug: print("Try date/RTC update")
  myGPS = [0.0,0.0,0.0]; prev = None
  try:
    prev = PinPower(atype=atype,on=True,debug=True)
    if Gps['lib'].quality < 1: display('wait GPS')
    for cnt in range(1,5):
      Gps['lib'].read()
      if Gps['lib'].quality > 0: break
      if debug: print("GPS %d try" % cnt)
    if Gps['lib'].satellites > 3:
      correction = time()
      Gps['lib'].UpdateRTC()
      StartUpTime += (time() - correction)
      for item in ['gps_next','info_next']:
        interval[item] += (time() - correction)
      if Gps['rtc'] == None: Gps['rtc'] = True
    else:
      if (Gps['lib'] == None) or debug: display('no GPS')
      return None
    if Gps['rtc'] == True:
      now = localtime()
      if 3 < now[1] < 11: timezone(7200) # simple DST
      else: timezone(3600)
      display('%d/%d/%d %s' % (now[0],now[1],now[2],('mo','tu','we','th','fr','sa','su')[now[6]]))
      display('time %02d:%02d:%02d' % (now[3],now[4],now[5]))
      Gps['rtc'] = False
    if Gps['lib'].longitude > 0:
      if debug: print("Update GPS coordinates")
      myGPS[LON] = round(float(Gps['lib'].longitude),5)
      myGPS[LAT] = round(float(Gps['lib'].latitude),5)
      myGPS[ALT] = round(float(Gps['lib'].altitude),1)
      if thisGPS[0] < 0.1:
        thisGPS = myGPS[0:] # home location
        if interval['info'] < 60: interval['info_next'] = interval['info'] = 1 # force
    else: myGPS = None
    if MyConfiguration['power'][abus]:
      PinPower(atype=atype,on=prev,debug=debug)
    if debug and (myGPS != None):
      print("GPS: lon %.5f, lat %.5f, alt %.2f" % (myGPS[LON],myGPS[LAT],myGPS[ALT]))
  except:
    Gps['enabled'] = False; Gps['lib'].ser.deinit(); Gps['lib'] = None
    display('GPS error')
    return None
  if interval['gps_next']: interval['gps_next'] = time()+interval[atype]
  return myGPS

## Pin devices
def initAccu():
  global MyDevices, MyConfig
  if not MyConfig: initConfig()
  if not 'accu' in MyDevices.keys(): return (getVoltage() != 0)
  else: return True

def DoAccu(debug=False):
  if not 'accu' in MyDevices.keys(): initAccu()
  try:
    if MyDevices['accu']: return getVoltage()
  except: return 0

## LoRa
# called via TTN response
# To Do: make the remote control survive a reboot
def CallBack(port,what):
  global HALT
  global Display, Dust, Meteo
  def ChangeConfig(atype,key,value):
    global MyConfiguration, MyConfig
    try:
      MyConfiguration[atype][key] = value
      MyConfig.dump(atype=atype,avalue=MyConfiguration[atype])
      MyConfig.store
    except: return True
    return True

  if not len(what): return True
  if len(what) < 2:
    if what == b'?':
      SendInfo(port); return True
    elif what == b'O':
      if Display['conf']['use']:
        Display['lib'].poweroff()
        ChangeConfig('power','display',False)
    elif what == b'o':
      if Display['conf']['use']:
        Display['lib'].poweron()
        ChangeConfig('power','display',None)
    elif what == b'S':
      ChangeConfig('interval','sleep',True)
    elif what == b's':
      ChangeConfig('interval','sleep',False)
    #elif what == b'd':
    #  if Dust['conf']['use']:
    #    ChangeConfig('dust','raw',True)
    #    Dust['raw'] = True # try: Dust['lib'].gase_base = None
    #elif what == b'D':
    #  if Dust['conf']['use']:
    #    Dust['raw'] = False # try: Dust['lib'].gase_base = None
    #elif what == b'm':
    #    if Meteo['conf']['use']: Meteo['raw'] = True
    #elif what == b'M':
    #    if Meteo['conf']['use']: Meteo['raw'] = False
    elif what == b'S': HALT = True
    #elif what == b'#':  # send partical cnt
    #    if Dust['conf']['name'][:3] != 'SDS': Dust['cnt'] = True
    #elif what == b'w': # send partical weight
    #    Dust['cnt'] = False
    else: return False
    return True
  cmd = None; value = None
  try:
    cmd, value = struct.unpack('>BH',what)
  except:
    return False
  if cmd == b'i':  # interval
    if value*60 > MyConfiguration['interval']['sample']:
      value = value*60 - MyConfiguration['interval']['sample']
    ChangeConfig('interval','interval',value)

# LoRa setup
def initNetwork(debug=False):
  global Network, LED
  if not Network: getMyConfig()

  def whichNet(debug=False):
    global Network
    Network['use'] = False
    Network['enabled'] = False
    if (Network['name'] == 'TTN') and (Network['lib']):
      return True
    print("No network found")
    return False

  if Network['enabled']: return True   # init only once
  if not whichNet(debug=debug): return False
  if Network['lib'].connect(method, ports=(len(Dprt)+1), callback=CallBack, resume=(not Network['init']), myLED=LED):
     display("Using LoRaWan")
     Network ['enabled'] = True
  else:
     display("NO LoRaWan")
     Network['lib'] = None
     Network ['enabled'] = False
  sleep_ms(10*1000)
  return Network ['enabled']

# denote a null value with all ones
# denote which sensor values present in data package
def DoPack(dData,mData,gps=None,wData=[],aData=None,debug=False):
  global Dust
  t = 0
  for d in dData, mData:
    for i in range(1,len(d)):
      if d[i] == None: d[i] = 0
  if mData[0] == None: mData[0] = 0
  if dData[PM1] == None: # PM2.5 PM10 case
    d = struct.pack('>HH',int(dData[PM25]*10),int(dData[PM10]*10))
    # print("PM 2.5, 10 cnt: ", dData[1:3])
  else:
    d = struct.pack('>HHH',int(dData[PM1]*10),int(dData[PM25]*10),int(dData[PM10]*10))
    t += 1
  if ('cnt' in Dust.keys()) and Dust['cnt']: # add counts
    # defeat: Plantower PM5c == Sensirion PM4c: to do: set flag in PM5c
    flg = 0x8000 if Dust['conf']['name'][:3] in ['SPS',] else 0x0
    try:
      if Dust['expl']:
        # 9 decrementing bytes, may change this
        d += struct.pack('>HHHHHH',
          int(dData[PM10c]*10+0.5),
          int(dData[PM05c]*10+0.5),
          int(dData[PM1c]*10+0.5),
          int(dData[PM25c]*10+0.5),
          int(dData[PM5c]*10+0.5)|flg,
          int(dData[PM03c]*10+0.5))
      else:
        # 9 bytes, ranges, average grain size  >0.30*100
        d += struct.pack('>HHHHHH',
          int((dData[PM10c]-dData[PM5c])*10+0.5)|0x8000,
          int(dData[PM05c]*10+0.5),
          int((dData[PM1c]-dData[PM05c])*10+0.5),
          int((dData[PM25c]-dData[PM1c])*10+0.5),
          int((dData[PM5c]-dData[PM25c])*10+0.5)|flg,
          int(dData[PM03c]*100+0.5))
    except:
      d += struct.pack('>HHHHHH',0,0,0,0,0,0)
      display("Error dust fan",clear=True)
      if LED: LED.blink(5,0.2,0xFF0000,l=False,force=True)
    t += 2
  m = struct.pack('>HHH',int(mData[TEMP]*10+300),int(mData[HUM]*10),int(mData[PRES]))
  if len(mData) > 3:
    m += struct.pack('>HH',int(round(mData[GAS]/100.0)),int(mData[AQI]*10))
    t += 4
  if (type(gps) is list) and (gps[LAT] > 0.01):
    l = struct.pack('>lll', int(round(gps[LAT]*100000)),int(round(gps[LON]*100000)),int(round(gps[ALT]*10)))
    t += 8
  else: l = ''
  w = ''
  if len(wData) == 2: # wind = [speed,direction]
    wData[1] = int(round(wData[1]))/3
    if not (0 <= wData[1] <= 360): wData[1] = 0 
    else: wData += 3
    if wData[1] >= 360: wData[1] = 359
    w = struct.pack('>H', (int(round(wData[0])*10)<<7) | int(round(wData[1]))/3)
    t += 16
  a = ''
  if aData > 0: # accu
    a = struct.pack('>B', int(round(aData) *10))
    t += 32
  # return d+m+l+w+a
  t = struct.pack('>B', t | 0x80) # flag the package
  return t+d+m+l+w+a # flag the package

# send kit info to LoRaWan
def SendInfo(port=Iprt):
  global Meteo, Dust, Network, LED
  global Gps, lastGPS, thisGPS
  meteo = ['','DHT11','DHT22','BME280','BME680','SHT31','WASP']
  dust = ['None','PPD42NS','SDS011','PMSx003','SPS30']
  if Network['lib'] == None: return False
  print("meteo: %s, dust: %s" %(Meteo['conf']['name'],Dust['conf']['name']))
  if (not Meteo['enabled']) and (not Dust['enabled']) and (not Gps['enabled']):
    return True
  sense = ((meteo.index(Meteo['conf']['name'])&0xf)<<4) | (dust.index(Dust['conf']['name'])&0x7)
  gps = 0
  LocUpdate()
  sense |= 0x8
  version = int(__version__[0])*10+int(__version__[2])
  data = struct.pack('>BBlll',version,sense, int(thisGPS[LAT]*100000),int(thisGPS[LON]*100000),int(thisGPS[ALT]*10))
  Network['lib'].send(data,port=port)
  if LED: LED.blink(1,0.2,0x0054FF,l=False) # blue
  return None

# startup info
def initDevices(debug=False):
  global MyConfiguration, MyTypes
  global STOP
  if not len(MyConfiguration): getMyConfig()

  try:
    # connect I2C devices
    initDisplay(debug=debug)

    if initDust(debug=debug):
        if Dust['cnt']: display("PM pcs:" + Dust['conf']['name'])
        else: display("PM   : " + Dust['conf']['name'])
    else: display("No dust sensor")

    if initMeteo(debug=debug):
        display("meteo: " + Meteo['conf']['name'])
    else: display("No meteo sensor")

    sleep_ms(15000)
    if not initGPS(debug=debug):
        display("No GPS")
    display('G:%.4f/%.4f' % (lastGPS[LAT],lastGPS[LON]))

    if initNetwork(debug=debug):
        display('Network: %s' % Network['conf']['name'])
    else: display("No network")
    if Network['enabled']: SendInfo()
  except Exception as e:
    # pycom.rgbled(0xFF0000)
    display("ERROR %s" % e)
    return False

  if debug:
    for item in Meteo, Display, Dust, Gps, Network:
      print("MyDevices[bus] ", end='')
      PrintDict(item,item['type'])
  return True

def getMyConfig(debug=False):
  global Meteo,Display,Dust,Gps,Accu,Network,Deepsleep
  global MyDevices

  ## INIT config
  initConfig(debug=False)
  getPinsConfig(debug=False)
  getBusConfig(debug=False)
  if debug: PrintDict(MyDevices,'MyDevices:')
  getNetConfig(debug=debug)
  getGlobals(debug=debug)
  ## CONF archive all if dirty
  if MyConfig.dirty:
    print("Flash updated config")
    MyConfig.store
    MyConfiguration = MyConfig.getConfig()
    if LED: LED.blink(5,0.3,0x00ff00,l=False)
  #if debug:
  #  PrintDict(MyConfiguration,'MyConfiguration: ')
  #  PrintDict(MyDevices,'MyDevices: ')

  if debug:
    for item in MyTypes.keys():
      print("MyDevices[bus] ", end='')
      PrintDict(MyTypes[item],'MyTypes[%s]' % item)

########   main loop
def runMe(debug=False):
  global MyConfiguration, MyTypes
  global wokeUp # power cycle
  global StartUpTime

  if not MyTypes:
    getMyConfig(debug=debug) 
    # short cuts
    interval = MyConfiguration['interval']
    Power = MyConfiguration['power']

    if not initDevices(debug=debug): # initialize devices and show initial info
      print("FATAL ERROR")
      if LED: LED.blink(25,0.2,0xFF0000,l=True,force=True)
      return False
    for item in ['info_next','gps_next']:
      if not item in interval.keys(): interval[item] = 0

    if debug:
      global MyConfig
      if MyConfig.dirty: print("Configuration is dirty")
  Dust = None
  try: Dust = MyTypes['dust']
  except: pass
  Network = None
  try: Network = MyTypes['network']
  except: pass

  if not wokeUp: # cold restart
    import os
    display('%s' % PyCom, (0,0),clear=True)
    display("MySense %s" % __version__[:8], (0,0), clear=True)
    display("s/n " + getSN())
    display("probes: %ds/%dm" % (interval['sample'], (interval['interval']+interval['sample'])/60))
  elif wokeUp and LED: LED.disable

  while True: # LOOP forever
    if LED: LED.blink(1,0.2,0x00FF00,l=False,force=True)
    toSleep = time()
    if interval['info'] and ((toSleep-StartUpTime) > interval['info_next']): # send info update
       SendInfo()
       if interval['info'] < 60: interval['info'] = 0 # was forced
       toSleep = time()
       interval['info_next'] = toSleep + interval['info']
    # Power management ttl is done by DoXYZ()
    if Display['enabled'] and Power['display']: Display['lib'].poweron()

    dData = DoDust(debug=debug)
    if Dust and Dust['conf']['use']:
        Dust['lib'].Standby()   # switch off laser and fan
        PinPower(atype='dust',on=False,debug=debug)

    mData = DoMeteo(debug=debug)

    aData = DoAccu(debug=debug)

    # Send packet
    if Network and Network['enabled']:
        if (Network['name'] == 'TTN'):
          if ('cnt' in Dust.keys()) and Dust['cnt']: port=Dprt[1]
          else: port=Dprt[0]
          if  Network['lib'].send(DoPack(dData,mData,LocUpdate(),aData=aData, debug=debug),port=port):
            if LED: LED.off
          else:
            display(" LoRa send ERROR")
            if LED: LED.blink(5,0.2,0x9c5c00,l=False)
        elif LED: LED.blink(2,0.2,0xFF0000,l=False,force=True)

    if STOP:
      sleep_ms(60*1000)
      Display['lib'].poweroff()
      PinPower(atype=['dust','gps','meteo','display'],on=False,debug=debug)
      # and put ESP in deep sleep: machine.deepsleep()
      return False

    toSleep = interval['interval'] - (time() - toSleep)
    if Dust and Dust['enabled']:
      if toSleep > 30:
        toSleep -= 15
        Dust['lib'].Standby()   # switch off laser and fan
      elif toSleep < 15: toSleep = 15
    PinPower(atype=['gps','dust'],on=False,debug=debug) # auto on/off next time
    if Display['enabled'] and (Power['display'] != None):
       Display['lib'].poweroff()
    elif not Power['i2c']:
      if not ProgressBar(0,62,128,1,toSleep,0xebcf5b,10):
        display('stopped SENSING', (0,0), clear=True)
        if LED: LED.blink(5,0.3,0xff0000,l=True)
      continue
    PinPower(atype=['display','meteo'],on=False,debug=debug)
    if Power['sleep'] and sleepMode():
      # save config and LoRa
      if MyConfig.dirty: MyConfig.store
      MyDevices['lora']['lib'].dump
      if toSleep > 60:
        deepsleep(toSleep-1) # deep sleep
        # will never arrive here
      else: sleep(toSleep)
      # restore config and LoRa
    elif LED: LED.blink(10,int(toSleep/10),0x748ec1,l=False)
    PinPower(atype=['display','meteo'],on=True,debug=debug)

if __name__ == "__main__":
  runMe(debug=True)
  sys.exit() # reset
