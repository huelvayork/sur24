import time
from machine import Pin, SoftI2C, UART, WDT
import machine
import ssd1306
from a9g import A9G

import config

LIGHTS_OFF=0
LIGHTS_LEFT=-1
LIGHTS_RIGHT=1
LIGHTS_BOTH=3
lights_state=LIGHTS_OFF

LEFT_PIN=25
RIGHT_PIN=26
WARNING_PIN=33
SMS_PIN=32

left_button=Pin(LEFT_PIN, Pin.IN, Pin.PULL_UP)
right_button=Pin(RIGHT_PIN, Pin.IN, Pin.PULL_UP)
warning_button=Pin(WARNING_PIN, Pin.IN, Pin.PULL_UP)
sms_button=Pin(SMS_PIN, Pin.IN, Pin.PULL_UP)

left_relay=Pin(14, Pin.OUT)
right_relay=Pin(13, Pin.OUT)
left_relay.on()
right_relay.on()

lights_lasttime = 0
last_smsbuttonpress = 0

a9g = A9G(uart_id = 2)

# OLED display Pin assignment 
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
    
    url = "{}/?id={}&lat={}&lon={}&speed={}&course={}".format(config.TRACCAR_URL,config.ID, lat, lon, speed, heading)
    a9g.http_get(url)


def send_location_sms():
    global a9g
    if a9g.gps_fixed():
        sms_text = "Vehiculo: {}\n".format(config.ID)
        sms_text = sms_text + "Posicion: {} {}\n".format(a9g.gps.latitude_string(), a9g.gps.longitude_string())
        sms_text = sms_text + "https://www.google.com/maps/search/?api=1&query={}{}+{}{}".format(a9g.gps.latitude[0], a9g.gps.latitude[1], a9g.gps.longitude[0], a9g.gps.longitude[1])
        a9g.sms(config.PHONE, sms_text)


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

def display_text(text):
    global oled
    oled.fill(0)
    oled.text(text, 0,20)
    oled.show
    
def sms_buttonpress():
    global last_smsbuttonpress
    global must_send_sms
    
    now = time.time()
    if now > last_smsbuttonpress + 5:
        last_smsbuttonpress = now
        must_send_sms = True
    

on_buttonpress_lasttime=0
def on_buttonpress(pin=None):
    global lights_state
    global on_buttonpress_lasttime

    # Disable interrupts
    irq_state = machine.disable_irq()

    now = time.ticks_ms()
    if (now < on_buttonpress_lasttime + 500):
        print("{} paso".format(pin))
        # Enable interrupts
        machine.enable_irq(irq_state)
        return
    
    on_buttonpress_lasttime = now
    
    if pin==sms_button:
        lights_state = LIGHTS_BOTH
        sms_buttonpress()

    elif pin==left_button:
        if lights_state in (LIGHTS_OFF, LIGHTS_LEFT):
            lights_state = LIGHTS_LEFT
        else:
            lights_state = LIGHTS_OFF
     
    elif pin==right_button:
        if lights_state in (LIGHTS_OFF, LIGHTS_RIGHT):
            lights_state = LIGHTS_RIGHT
        else:
            lights_state = LIGHTS_OFF

    elif pin==warning_button:
        if lights_state == LIGHTS_BOTH:
            lights_state = LIGHTS_OFF
        else:
            lights_state = LIGHTS_BOTH
            
    # Enable interrupts
    machine.enable_irq(irq_state)        


def lights_off():
    left_relay.on()
    right_relay.on()


def lights_left():
    global lights_lasttime
    
    now = time.ticks_ms()
    if now < lights_lasttime + 400:
        return

    lights_lasttime = now

    if left_relay.value() == 1:
        left_relay.off()
    else:
        left_relay.on()


def lights_right():
    global lights_lasttime
    
    now = time.ticks_ms()
    if now < lights_lasttime + 400:
        return

    lights_lasttime = now

    if right_relay.value() == 1:
        right_relay.off()
    else:
        right_relay.on()
    

def lights_both():
    global lights_lasttime
    
    now = time.ticks_ms()
    if now < lights_lasttime + 400:
        return

    lights_lasttime = now

    if left_relay.value() == 1:
        right_relay.off()
        left_relay.off()
    else:
        right_relay.on()
        left_relay.on()



# Main proogram

display_text("boot...")
print("boot")
lights_off()


# Wait for  A9G module to booot
time.sleep(5)
a9g.conn_init()
a9g.gps.local_offset = 2
a9g.gps_init()
a9g.gps_periodic_update(1)

sms_button.irq(on_buttonpress, trigger=Pin.IRQ_FALLING)
left_button.irq(on_buttonpress, trigger=Pin.IRQ_FALLING)
right_button.irq(on_buttonpress, trigger=Pin.IRQ_FALLING)
warning_button.irq(on_buttonpress, trigger=Pin.IRQ_FALLING)

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

    if lights_state == LIGHTS_OFF:
        lights_off()
    elif lights_state == LIGHTS_LEFT:
        lights_left()
    elif lights_state == LIGHTS_RIGHT:
        lights_right()
    elif lights_state == LIGHTS_BOTH:
        lights_both()
        