#ifndef SFB_GATEWAY_DEFINES_H
#define SFB_GATEWAY_DEFINES_H

//#include "packethandler.h"
#include <iostream>
#include <fstream>
#include <wiringPi.h>
#include "CC1200_driver/CC1200.hpp"
#include "CC1200_driver/Queue.hpp"
#include "CC1200_driver/phy_channels.h"
#include <stdint.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <thread>
#include <unistd.h>
#include <string>
#include <ctime>
#include <chrono>
#include <map>
#include <signal.h>
#include <unistd.h>
#include <sys/stat.h>
#include "later.cpp"
#include "LPD8806.h"
#include <sys/types.h>  // mkfifo
#include <sys/stat.h>   // mkfifo
#include <fstream>
#include <iostream>
#include <unistd.h>

/******************************************************************************
* DEFINES
*/


#define CRC_OK_BIT  0x80
#define CRC_OK_BYTE(x) (x & CRC_OK_BIT)
#define PACKET_CRC_OK(x) (x.statusbyte2 & CRC_OK_BIT)

#define LED_DATA_PIN  RPI_V2_GPIO_P1_35
#define LED_CLK_PIN   RPI_V2_GPIO_P1_37

#define TX_FIFO_PATH  "/tmp/sfb_txfifo"
#define RX_FIFO_PATH  "/tmp/sfb_rxfifo"

#define DEBUG_STATES 1

typedef struct __attribute__((packed)) {
  uint8_t module_num;
  CCPHYPacket packet;      
} APPacket;

/******************************************************************************
* LOCAL VARIABLES
*/
Later timer;
LPD8806 strip(4, LED_DATA_PIN, LED_CLK_PIN);

bool use_m1 = false, use_m2 = false, use_m3 = false, use_m4 = false;

void exitHandler(int s);

void initLED();
void blinkLED(uint32_t color, int duration);
void ledOff();

bool gpioInit(void);
void initModules(void);
void radioLoop(void);

int initFifos(void);

void readFifoLoop();

void handlePacket(CCPHYPacket& packet, CC1200 &module);

module_t m1 = { 
  .cs = M1_CS, 
  .gpio0 = 27,// RPI_V2_GPIO_P1_36, //wiringPi pin = 27
  .gpio2 = 28,// RPI_V2_GPIO_P1_38, //wiringPi pin = 28
  .gpio3 = 6, // RPI_V2_GPIO_P1_22  //wiringPi pin = 6
  .channel = 12,
  .number = 1
 };

module_t m2 = { 
.cs = M2_CS, 
.gpio0 = 1,   //RPI_V2_GPIO_P1_12,   //wiringPi pin = 1
.gpio2 = 4,   //RPI_V2_GPIO_P1_16,   //wiringPi pin = 4
.gpio3 = 16,   //RPI_V2_GPIO_P1_10    //wiringPi pin = 16
.channel = 1,
.number = 2
};

module_t m3 = { 
.cs = M3_CS, 
.gpio0 = 9, //RPI_V2_GPIO_P1_05,    //wiringPi pin = 9
.gpio2 = 8, //RPI_V2_GPIO_P1_03,    //wiringPi pin = 8
.gpio3 = 7, //RPI_V2_GPIO_P1_07     //wiringPi pin = 7
.channel = 2,
.number = 3
};

module_t m4 = { 
.cs = M4_CS,    
.gpio0 = 3,   //RPI_V2_GPIO_P1_15,   //wiringPi pin = 3
.gpio2 = 2,   //RPI_V2_GPIO_P1_13,   //wiringPi pin = 2
.gpio3 = 21,  //RPI_V2_GPIO_P1_29    //wiringPi pin = 21
.channel = 3,
.number = 4
};

#endif /* SFB_GATEWAY_DEFINES_H */
