'''
Created on Aug 18, 2015

@author: akrv
'''
import RPi.GPIO as GPIO
import time
 
class LPD8806:
    def __init__(self, count, dataPin, clkPin):
        self.d = dataPin
        self.c = clkPin
        self.count = count
        self.pixels = [0] * count * 3
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

    def begin(self):
        GPIO.setup(self.c, GPIO.OUT)
        GPIO.setup(self.d, GPIO.OUT)

    def numPixels(self):
        return self.count

    def color(self, r, g, b):
        #Take the lowest 7 bits of each value and append them end to end
        # We have the top bit set high (its a 'parity-like' bit in the protocol
        # and must be set!)

        x = g | 0x80
        x <<= 8
        x |= r | 0x80
        x <<= 8
        x |= b | 0x80

        return x

    def write8(self, d):
        # Basic, push SPI data out
        for i in range(8):
            GPIO.output(self.d, (d & (0x80 >> i)) <> 0)
            GPIO.output(self.c, True)
            GPIO.output(self.c, False)

    # This is how data is pushed to the strip. 
    # Unfortunately, the company that makes the chip didnt release the 
    # protocol document or you need to sign an NDA or something stupid
    # like that, but we reverse engineered this from a strip
    # controller and it seems to work very nicely!
    def show(self):
        # get the strip's attention
        self.write8(0)
        self.write8(0)
        self.write8(0)
        self.write8(0)

        # write 24 bits per pixel
        for i in range(self.count):
            self.write8(self.pixels[i*3])
            self.write8(self.pixels[i*3+1])
            self.write8(self.pixels[i*3+2])
  
        # to 'latch' the data, we send just zeros
        for i in range(self.count * 2):
            self.write8(0)
            self.write8(0)
            self.write8(0)

        # we need to have a delay here, 10ms seems to do the job
        # shorter may be OK as well - need to experiment :(
        time.sleep(0.005)

    # store the rgb component in our array
    def setPixelRGB(self, n, r, g, b):
        if n >= self.count: return
        self.pixels[n*3] = g | 0x80
        self.pixels[n*3+1] = r | 0x80
        self.pixels[n*3+2] = b | 0x80

    def setPixelColor(self, n, c):
        if n >= self.count: return

        self.pixels[n*3] = (c >> 16) | 0x80
        self.pixels[n*3+1] = (c >> 8) | 0x80
        self.pixels[n*3+2] = (c) | 0x80


# Chase a dot down the strip
# used from inside gateway.py   
def color1by1(strip, c, wait):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, c)
        #if i == 0:
        #    strip.setPixelColor(strip.numPixels() - 1, 0)
        strip.show()
        time.sleep(wait)
    # time.sleep(wait)

def blink(strip, c, duration, wait):
    for i in range(duration):
        strip.setPixelColor(0, 0x000000)
        strip.setPixelColor(1, 0x000000)
        strip.setPixelColor(2, 0x000000)
        strip.setPixelColor(3, 0x000000)
        strip.show()
        time.sleep(.1)
        strip.setPixelColor(0, c)
        strip.setPixelColor(1, c)
        strip.setPixelColor(2, c)
        strip.setPixelColor(3, c)
        strip.show()
        time.sleep(.1)
        strip.setPixelColor(0, 0x000000)
        strip.setPixelColor(1, 0x000000)
        strip.setPixelColor(2, 0x000000)
        strip.setPixelColor(3, 0x000000)
        strip.show()
        time.sleep(wait)


def knight_rider(strip, c, rounds):
    
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, 0x000000)
        strip.show()
        time.sleep(0.0005)
    time.sleep(0.1)
    for i in range(rounds):
        for i in range(strip.numPixels() + 1):
            if i == 0:
                strip.setPixelColor(i, c)
            elif i == 1:
                strip.setPixelColor(i, c)
                strip.setPixelColor(i - 1, 0x000000)
            elif i == 2:
                strip.setPixelColor(i, c)
                strip.setPixelColor(i - 1, 0x0000)
            elif i == 3:
                strip.setPixelColor(i, c)
                strip.setPixelColor(i - 1, 0x0000)
            elif i == 4:
                strip.setPixelColor(i - 1, 0x0000)
            strip.show()
            time.sleep(0.075)
        time.sleep(0.1)
        for i in range(strip.numPixels() - 1, -2 , -1):
            if i == -1:
                strip.setPixelColor(i + 1, 0x000000)
            elif i == 0:
                strip.setPixelColor(i, c)
                strip.setPixelColor(i + 1, 0x000000)
            elif i == 1:
                strip.setPixelColor(i, c)
                strip.setPixelColor(i + 1, 0x000000)
            elif i == 2:
                strip.setPixelColor(i, c)
                strip.setPixelColor(i + 1, 0x000000)
            elif i == 3:
                strip.setPixelColor(i, c)
            strip.show()
            time.sleep(0.075)
        time.sleep(0.5)
    
    
def initializeStrip():
    # Choose which 2 pins you will use for output.
    # Can be any valid output pins.
    dataPin     = 35
    clockPin    = 37
    numLeds     = 4
    # Set the first variable to the NUMBER of pixels. 32 = 32 pixels in a row
    # The LED strips are 32 LEDs per meter but you can extend/cut the strip
    strip = LPD8806(numLeds, dataPin, clockPin)
    strip.begin()
    # Update the strip, to start they are all 'off'
    strip.show()
    return strip
