import time
from machine import Pin, SoftI2C, UART, WDT
import ssd1306
from a9g import A9G

ID="MAZAKOTE"
PHONE="606XXXXXX"

import config


#wdt = WDT(timeout=15000)

button = Pin(33, mode=Pin.IN, pull=Pin.PULL_UP)
last_buttonpress = 0

a9g = A9G(uart_id = 2)

# ESP32 Pin assignment 
i2c = SoftI2C(scl=Pin(21), sda=Pin(22))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)


def send_location_traccar():
    global a9g
    
    lat = a9g.gps.latitude[0]
    if a9g.gps.latitude[1] == 'S':
        lat = lat * -1
        
    lon = a9g.gps.longitude[0]
    if a9g.gps.longitude[1] == 'W':
        lon = lon * -1
        
    speed = a9g.gps.speed[0] # velocidad en nudos
    heading = a9g.gps.course
    
    url = "http://cloud.huelvayork.com:5055/?id={}&lat={}&lon={}&speed={}&course={}".format(ID, lat, lon, speed, heading)
    a9g.http_get(url)


def send_location_sms():
    global a9g
    if a9g.gps_fixed():
        sms_text = "Vehiculo: {}\n".format(ID)
        sms_text = sms_text + "Posicion: {} {}\n".format(a9g.gps.latitude_string(), a9g.gps.longitude_string())
        sms_text = sms_text + "https://www.google.com/maps/search/?api=1&query={}{}+{}{}".format(a9g.gps.latitude[0], a9g.gps.latitude[1], a9g.gps.longitude[0], a9g.gps.longitude[1])
        a9g.sms(PHONE, sms_text)


def display_data():
    global oled
    global a9g
    oled.fill(0) # clear screen
    oled.text("{} {}/{} Fix:{}".format(('C' if a9g.is_connected() else 'd'), a9g.gps.satellites_in_use, a9g.gps.satellites_in_view, a9g.gps.fix_type), 0, 00)
    oled.text("{:.4f}{} {:.4f}{}".format(a9g.gps.latitude[0], a9g.gps.latitude[1], a9g.gps.longitude[0], a9g.gps.longitude[1]), 0, 10)
    oled.text("Vel: {}".format(a9g.gps.speed_string("kmh")), 0, 20)
    oled.text("Rumbo:{}".format(a9g.gps.course), 0, 30)
    oled.text("{:02d}:{:02d}:{:02d}".format(a9g.gps.timestamp[0], a9g.gps.timestamp[1],int(a9g.gps.timestamp[2])),62,50)
    oled.show()


def on_buttonpress(pin=None):
    global last_buttonpress
    now=time.time()
    if last_buttonpress < now-1:
        last_buttonpress = now
        must_send_sms = True


a9g.conn_init()
a9g.gps.local_offset = 2
a9g.gps_init()
a9g.gps_periodic_update(1)

button.irq(on_buttonpress, trigger=Pin.IRQ_FALLING)

display_time = time.time()
traccar_time = time.time()

must_send_sms = False

while True:
#    wdt.feed()
    now = time.time()
    
    a9g.update()
    
    if now >= display_time:
        display_data()
        display_time = now + 1
        
    if now > traccar_time and a9g.gps_fixed() and a9g.is_connected():
            send_location_traccar()
            traccar_time = now + 10


    if must_send_sms:
        must_send_sms = False
        send_location_sms()

    
