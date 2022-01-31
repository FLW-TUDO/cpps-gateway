#!/usr/bin/python

import notification as n
import time, random

strip = n.initializeStrip()

while True:
    sleep = round(random.uniform(0.5, 8), 2)
    blink_time = random.randint(1, 8)
    n.blink(strip, 0x0000FF, blink_time, .05)
    color_on = random.randint(0, 1)
    # if color == 1:
    n.color1by1(strip, 0x0000FF, .1)
    time.sleep(sleep)
