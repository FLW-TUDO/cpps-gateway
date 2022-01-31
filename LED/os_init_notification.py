#!/usr/bin/python

import notification as n
import time

strip = n.initializeStrip()

# n.knight_rider(strip, 0x0000FF, 3)
n.blink(strip, 0x0000FF, 5, .05)
n.color1by1(strip, 0x0000FF, .1)
