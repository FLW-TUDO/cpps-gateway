#!/usr/bin/python

import notification as n

print('LED Test')

strip = n.initializeStrip()

n.color1by1(strip, 0x000000, 1)
n.color1by1(strip, 0x0000FF, 0)


