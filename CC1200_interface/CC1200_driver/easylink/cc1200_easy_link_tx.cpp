//******************************************************************************
//! @file       cc120x_easy_link_tx.c
//! @brief      This program sets up an easy link between two trxEB's with
//!             CC112x EM's connected.
//!             The program can take any recomended register settings exported
//!             from SmartRF Studio 7 without any modification with exeption
//!             from the assumtions decribed below.
//
//              Notes: The following asumptions must be fulfilled for
//              the program to work:
//
//                  1.  GPIO2 has to be set up with GPIO2_CFG = 0x06
//                      PKT_SYNC_RXTX for correct interupt
//                  2.  Packet engine has to be set up with status bytes enabled
//                      PKT_CFG1.APPEND_STATUS = 1
//
//  Copyright (C) 2013 Texas Instruments Incorporated - http://www.ti.com/
//
//  Redistribution and use in source and binary forms, with or without
//  modification, are permitted provided that the following conditions
//  are met:
//
//      Redistributions of source code must retain the above copyright
//      notice, this list of conditions and the following disclaimer.
//
//      Redistributions in binary form must reproduce the above copyright
//      notice, this list of conditions and the following disclaimer in the
//      documentation and/or other materials provided with the distribution.
//
//      Neither the name of Texas Instruments Incorporated nor the names of
//      its contributors may be used to endorse or promote products derived
//      from this software without specific prior written permission.
//
//  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
//  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
//  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
//  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
//  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
//  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
//  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
//  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
//  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
//  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
//  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//*****************************************************************************/


/*******************************************************************************
* INCLUDES
*/
//#include "msp430.h"
//#include "lcd_dogm128_6.h"
//#include "hal_spi_rf_trxeb.h"
//#include "cc120x_spi.h"
//#include "stdlib.h"
#include <wiringPi.h>

#include "CC1200.hpp"

#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
//#include "bsp.h"
//#include "bsp_key.h"
//#include "io_pin_int.h"
//#include "bsp_led.h"
#include <iostream>

using namespace std;

/*******************************************************************************
* DEFINES
*/
#define ISR_ACTION_REQUIRED 1
#define ISR_IDLE            0

#define PKTLEN              30 // 1 < PKTLEN < 126

#define GPIO0   0
#define GPIO2   2
//#define GPIO3               0x04
//#define GPIO2               0x08
//#define GPIO0               0x80


/*******************************************************************************
* LOCAL VARIABLES
*/
static uint8_t  packetSemaphore;
static uint32_t packetCounter = 0;


/*******************************************************************************
* STATIC FUNCTIONS
*/
//static void initMCU(void);
//static void registerConfig(void);
static void runTX(CC1200);
static void createPacket(uint8_t randBuffer[]);
static void radioTxISR(void);
static void updateLcd(void);
//for interrupts
//static void IntDisable(int);
//static void IntEnable(int);

/*******************************************************************************
*   @fn         main
*
*   @brief      Runs the main routine
*
*   @param      none
*
*   @return     none
*/
int main(void) {

    // Initialize MCU and peripherals
    //initMCU();

    CC1200 cc1200;

    cc1200.init();
    
    if (wiringPiSetup () < 0)
    {
        fprintf (stderr, "Unable to setup wiringPi: %s\n", strerror (errno)) ;
        return 1 ;
    }

    cc1200.registerConfig();

    // Enter runTX, never coming back
    runTX(cc1200);
}

/*static void IntDisable(int pin){
    string _pin = to_string(pin);
    string execute = "/usr/local/bin/gpio edge "+_pin+" none";
    system(execute);
}
static void IntEnable(int){
    string _pin = to_string(pin);
    string execute = "/usr/local/bin/gpio edge "+_pin+" falling";
    system(execute);
}*/
/*******************************************************************************
*   @fn         runTX
*
*   @brief      Continuously sends packets on button push until button is pushed
*               again. After the radio has gone into TX the function waits for
*               interrupt that packet has been sent. Updates packet counter and
*               display for each packet sent.
*
*   @param      none
*
*   @return    none
*/
static void runTX(CC1200 cc1200) {

    // Initialize packet buffer of size PKTLEN + 1
    uint8_t txBuffer[PKTLEN+1] = {0};

    // Connect ISR function to GPIO2
    //ioPinIntRegister(IO_PIN_PORT_1, GPIO2, &radioTxISR);

    // Interrupt on falling edge
    //ioPinIntTypeSet(IO_PIN_PORT_1, GPIO2, IO_PIN_FALLING_EDGE);
    wiringPiISR(GPIO0, INT_EDGE_FALLING, &radioTxISR);
    // Clear ISR flag
    //ioPinIntClear(IO_PIN_PORT_1, GPIO2);

    // Enable interrupt
    //ioPinIntEnable(IO_PIN_PORT_1, GPIO2);

    // Update LCD
    updateLcd();

    // Infinite loop
    while(TRUE) {
            int a = 0;
            cout<<"0:continue, 1:exit"<<endl;
            cout<<"input: "<<endl;
            cin>>a;
            // Continiously sent packets until button is pressed
            do {

                // Update packet counter
                packetCounter++;

                // Create a random packet with PKTLEN + 2 byte packet
                // counter + n x random bytes
                createPacket(txBuffer);

                // Write packet to TX FIFO
                //cc120xSpiWriteTxFifo(txBuffer, sizeof(txBuffer));
                cc1200.ccWriteTxFifo(txBuffer, sizeof(txBuffer));
                
                // Strobe TX to send packet
                //trxSpiCmdStrobe(CC120X_STX);
                cc1200.SendStrobe(STX);
                // Wait for interrupt that packet has been sent.
                // (Assumes the GPIO connected to the radioRxTxISR function is
                // set to GPIOx_CFG = 0x06)
                while(packetSemaphore != ISR_ACTION_REQUIRED);

                // Clear semaphore flag
                packetSemaphore = ISR_IDLE;

                // Update LCD
                updateLcd();
           }  while (a!=1);
        
    }
}


/*******************************************************************************
*   @fn         radioTxISR
*
*   @brief      ISR for packet handling in TX. Sets packet semaphore
*               and clears ISR flag
*
*   @param      none
*
*   @return     none
*/
static void radioTxISR(void) {

    // Set packet semaphore
    packetSemaphore = ISR_ACTION_REQUIRED;

    // Clear ISR flag
    //ioPinIntClear(IO_PIN_PORT_1, GPIO2);
}


/*******************************************************************************
*   @fn         initMCU
*
*   @brief      Initialize MCU and board peripherals
*
*   @param      none
*
*   @return     none
*/
/*static void initMCU(void) {

    // Init clocks and I/O
    bspInit(BSP_SYS_CLK_8MHZ);

    // Init LEDs
    bspLedInit();

    // Init buttons
    bspKeyInit(BSP_KEY_MODE_POLL);

    // Initialize SPI interface to LCD (shared with SPI flash)
    bspIoSpiInit(BSP_FLASH_LCD_SPI, BSP_FLASH_LCD_SPI_SPD);

    // Init LCD
    lcdInit();

    // Instantiate transceiver RF SPI interface to SCLK ~ 4 MHz
    // Input parameter is clockDivider
    // SCLK frequency = SMCLK/clockDivider
    trxRfSpiInterfaceInit(2);

    // Enable global interrupt
    _BIS_SR(GIE);
}*/


/*******************************************************************************
*   @fn         registerConfig
*
*   @brief      Write register settings as given by SmartRF Studio found in
*               cc120x_easy_link_reg_config.h
*
*   @param      none
*
*   @return     none
*/



/*******************************************************************************
*   @fn         createPacket
*
*   @brief      This function is called before a packet is transmitted. It fills
*               the txBuffer with a packet consisting of a length byte, two
*               bytes packet counter and n random bytes.
*
*               The packet format is as follows:
*               |--------------------------------------------------------------|
*               |           |           |           |         |       |        |
*               | pktLength | pktCount1 | pktCount0 | rndData |.......| rndData|
*               |           |           |           |         |       |        |
*               |--------------------------------------------------------------|
*                txBuffer[0] txBuffer[1] txBuffer[2]            txBuffer[PKTLEN]
*
*   @param       Pointer to start of txBuffer
*
*   @return      none
*/
static void createPacket(uint8_t txBuffer[]) {

    txBuffer[0] = PKTLEN;                           // Length byte
    txBuffer[1] = (uint8_t) (packetCounter >> 8);     // MSB of packetCounter
    txBuffer[2] = (uint8_t)  packetCounter;           // LSB of packetCounter

    // Fill rest of buffer with random bytes
    for(uint8_t i = 3; i < (PKTLEN + 1); i++) {
        //txBuffer[i] = (uint8_t)rand();
        txBuffer[i] = 0;
    }
}


/*******************************************************************************
*   @fn         updateLcd
*
*   @brief      Updates LCD buffer and sends buffer to LCD module
*
*   @param      none
*
*   @return     none
*/
static void updateLcd(void) {

    // Update LDC buffer and send to screen.
    /*lcdBufferClear(0);
    lcdBufferPrintString(0, "EasyLink Test", 0, eLcdPage0);
    lcdBufferSetHLine(0, 0, LCD_COLS-1, 7);
    lcdBufferPrintString(0, "Sent packets:", 0, eLcdPage3);
    lcdBufferPrintInt(0, packetCounter, 70, eLcdPage4);
    lcdBufferPrintString(0, "Packet TX" , 0, eLcdPage7);
    lcdBufferSetHLine(0, 0, LCD_COLS-1, 55);
    lcdBufferInvertPage(0, 0, LCD_COLS, eLcdPage7);
    lcdSendBuffer(0);*/
    cout<<"EasyLink Test"<<endl;
    cout<<dec<<"Sent packets :\033[1;31m"<<packetCounter<<"\033[0m"<<endl;
    cout<<"Packet \033[1;31mTX\033[0m"<<endl;
}