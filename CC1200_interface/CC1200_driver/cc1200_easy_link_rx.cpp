//*****************************************************************************
//! @file        cc120x_easy_link_rx.c
//
//! @brief     This program sets up an easy link between two trxEB's with
//                CC120x EM's connected. 
//                The program can take any recomended register settings exported
//                from SmartRF Studio 7 without any modification with exeption 
//                from the assumtions decribed below.
//  
//                The following asumptions must be fulfilled for the program
//                to work:
//                
//                1. GPIO2 has to be set up with GPIO2_CFG = 0x06
//                   PKT_SYNC_RXTX for correct interupt
//                2. Packet engine has to be set up with status bytes enabled 
//                   PKT_CFG1.APPEND_STATUS = 1
//
//  Copyright (C) 2013 Texas Instruments Incorporated - http://www.ti.com/
//
//
//  Redistribution and use in source and binary forms, with or without
//  modification, are permitted provided that the following conditions
//  are met:
//
//    Redistributions of source code must retain the above copyright
//    notice, this list of conditions and the following disclaimer.
//
//    Redistributions in binary form must reproduce the above copyright
//    notice, this list of conditions and the following disclaimer in the
//    documentation and/or other materials provided with the distribution.
//
//    Neither the name of Texas Instruments Incorporated nor the names of
//    its contributors may be used to endorse or promote products derived
//    from this software without specific prior written permission.
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
//****************************************************************************/


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

/******************************************************************************
* DEFINES
*/
#define ISR_ACTION_REQUIRED 1
#define ISR_IDLE            0
#define GPIO0   0
#define GPIO2   2
#define RX_FIFO_ERROR       0x11
#define PKTLEN              30 // 1 < PKTLEN < 126
/******************************************************************************
* LOCAL VARIABLES
*/
static uint8_t  packetSemaphore;
static uint32_t packetCounter = 0;
static uint8_t rssi=0;
/******************************************************************************
* STATIC FUNCTIONS
*/
//static void registerConfig(void);
void RunRX(CC1200);
static void radioRxTxISR(void);
static void updateLcd(void);
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
  RunRX(cc1200);
}
/******************************************************************************
 * @fn          runRX
 *
 * @brief       puts radio in RX and waits for packets. Function assumes
 *              that status bytes are appended in the RX_FIFO
 *              Update packet counter and display for each packet received.
 *                
 * @param       none
 *
 * @return      none
 */
 void RunRX(CC1200 cc1200){

  uint8_t rxBuffer[128] = {0};
  uint8_t rxBytes;
  uint8_t marcStatus;
  
    // Write radio registers
  //registerConfig();
  
  // Connect ISR function to GPIO0, interrupt on falling edge
  //trxIsrConnect(&radioRxTxISR);
  wiringPiISR(GPIO0, INT_EDGE_FALLING, &radioRxTxISR);
  // Enable interrupt from GPIO_0
  //trxEnableInt();

  // Update LCD
  updateLcd();

  // Set radio in RX
  cc1200.SendStrobe(SRX);

  // Loop until left button is pushed (exits application)
  while(TRUE){

    // Wait for packet received interrupt 
    if(packetSemaphore == ISR_ACTION_REQUIRED){

      // Read number of bytes in rx fifo
      cc1200.ccReadReg(REG_NUM_RXBYTES, &rxBytes, 1);
      rssi = cc1200.ReadReg(REG_RSSI1);
      // Check that we have bytes in fifo
      if(rxBytes != 0){

        // Read marcstate to check for RX FIFO error
        cc1200.ccReadReg(REG_MARCSTATE, &marcStatus, 1);
        
        // Mask out marcstate bits and check if we have a RX FIFO error
        if((marcStatus & 0x1F) == RX_FIFO_ERROR){

          // Flush RX Fifo
          cc1200.SendStrobe(SFRX);
        }
        else{ 

          // Read n bytes from rx fifo
          cc1200.ccReadRxFifo(rxBuffer, rxBytes,0);  
          
          // Check CRC ok (CRC_OK: bit7 in second status byte)
          // This assumes status bytes are appended in RX_FIFO
          // (PKT_CFG1.APPEND_STATUS = 1.)
          // If CRC is disabled the CRC_OK field will read 1
          if(rxBuffer[rxBytes-1] & 0x80){
            for(uint8_t i = 3; i < (PKTLEN + 1); i++) {
          //txBuffer[i] = (uint8_t)rand();
              cout<<"\033[1;34m"<<(int)i<<"th packet:"<<(int)rxBuffer[i]<<"\033[0m"<<endl;
            }
            // Update packet counter
            packetCounter++;
          }
        }
      }
      
      // Update LCD
      updateLcd();
      
      // Reset packet semaphore
      packetSemaphore = ISR_IDLE;
      
      // Set radio back in RX
      cc1200.SendStrobe(SRX);
      
    }
  }
  // Reset packet counter
  packetCounter = 0;
  // Put radio to sleep and exit application
  cc1200.SendStrobe(SPWD);
}
/*******************************************************************************
* @fn          radioRxTxISR
*
* @brief       ISR for packet handling in RX. Sets packet semaphore 
*              and clears isr flag.
*
* @param       none
*
* @return      none
*/
static void radioRxTxISR(void){

  // Set packet semaphore
  packetSemaphore = ISR_ACTION_REQUIRED;  
  
  // Clear isr flag
  //trxClearIntFlag();
}

/*******************************************************************************
* @fn          registerConfig
*
* @brief       Write register settings as given by SmartRF Studio found in
*              cc120x_easy_link_reg_config.h
*
* @param       none
*
* @return      none
*/
/*
static void registerConfig(void){
  
  uint8_t writeByte;
  
  // Reset radio
  trxSpiCmdStrobe(CC120X_SRES);
  
  // Write registers to radio
  for(uint16 i = 0; i < (sizeof  preferredSettings/sizeof(registerSetting_t)); i++) {
    writeByte =  preferredSettings[i].data;
    cc120xSpiWriteReg( preferredSettings[i].addr, &writeByte, 1);
  }
}*/
/******************************************************************************
 * @fn          updateLcd
 *
 * @brief       updates LCD buffer and sends bufer to LCD module.
 *                
 * @param       none
 *
 * @return      none
 */
 static void updateLcd(void){

      // Update LDC buffer and send to screen.
      //lcdBufferClear(0);
      //lcdBufferPrintString(0, "    EasyLink Test    ", 0, eLcdPage0);
  cout<<"EasyLink Test"<<endl;
      //lcdBufferSetHLine(0, 0, LCD_COLS-1, eLcdPage7); 
      //lcdBufferPrintString(0, "Received ok:", 0, eLcdPage3);
  cout<<dec<<"Received ok:\t\033[1;31m"<<packetCounter<<"\033[0m"<<endl;
      //lcdBufferPrintInt(0, packetCounter, 70, eLcdPage4);
      //lcdBufferPrintString(0, "      Packet RX        ", 0, eLcdPage7);
  cout<<"Packet \033[1;34mRX\033[0m"<<endl;
  cout<<"RSSI:\t\033[1;36m"<<(int)rssi<<"\033[0m dBm"<<endl;
      //lcdBufferSetHLine(0, 0, LCD_COLS-1, 55);
      //lcdBufferInvertPage(0, 0, LCD_COLS, eLcdPage7);
      //lcdSendBuffer(0);
}