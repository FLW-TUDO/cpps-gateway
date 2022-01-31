CC      = g++
CFLAGS  = -std=c++11
LDFLAGS = -lwiringPi -lbcm2835 -lpthread
SOURCE = sfb_gateway.cpp CC1200_driver/Queue.cpp CC1200_driver/CC1200.cpp CC1200_driver/semaphore.cpp later.cpp LPD8806.cpp
OUT = SFBGateway.app

TARGET = SFBGateway

all: 
	$(CC) $(CFLAGS) $(SOURCE) -o $(OUT) $(LDFLAGS)

SFB_great_again: all

.PHONY: clean cleanest

clean:
	rm *.app

cleanest: clean
	rm sfb_gateway
