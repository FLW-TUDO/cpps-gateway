#ifndef CC1200_H
#define CC1200_H

#include <iostream>
#include <bcm2835.h>
#include <cerrno>
#include <iomanip>
#include <cstring>
#include <clocale>

#include "Queue.hpp"
#include "REG_CC1200.h"
#include "cc1200_easy_link_reg_config.h"

#define CS_CC1200 		RPI_V2_GPIO_P1_40
#define MISO_CC1200 	RPI_V2_GPIO_P1_21
#define RESET_CC1200	RPI_V2_GPIO_P1_32
/*
 * Conflict between wiringPi.h
 * 
 * wiringPi already define OUTPUT as 0x01
 * and INPUT as 0x00
 */
// #define OUTPUT 0x01
// #define INPUT 	0x00
#ifndef OUTPUT
#define OUTPUT	BCM2835_GPIO_FSEL_OUTP
#endif

#ifndef INPUT
#define INPUT		BCM2835_GPIO_FSEL_INPT
#endif
//radio states from chip status byte
typedef enum _CC1200_STATE_
{
	CC1200_IDLE = 0, /// < Radio in standby 
    CC1200_RX, /// 1 transmit ready
    CC1200_TX,  /// 2 transmitting active
    CC1200_FSTX, /// 3 fast transmit ready 
    CC1200_CALIBRATE, /// 4 = CALIBRATE (synthesizer is calibrating)
    CC1200_SETTLING,  /// 5 = Radio SETTLING
    CC1200_RXERROR,   /// 6 = RX FIFO Error
    CC1200_TXERROR, /// 7 = TX Fifo Error
} CC1200_STATE;

//#warning deprecate in favor of typedef enum
#define RADIO_IDLE (uint8_t)0
#define RADIO_RX (uint8_t)1
#define RADIO_TX (uint8_t)2
#define RADIO_FSTX (uint8_t)3
#define RADIO_CALIBRATE (uint8_t)4
#define RADIO_SETTLING (uint8_t)5
#define RADIO_RXERROR (uint8_t)6
#define RADIO_TXERROR (uint8_t)7


#define REG_TXFIFO 0x3F

#define COMMAND_QUEUE_SIZE 8 //radio commands are queued in an array of two uint8_t arrays.

#define RADIO_SINGLE_ACCESS  0x00
#define RADIO_WRITE_ACCESS   0x00
#define RADIO_BURST_ACCESS   0x40
#define RADIO_READ_ACCESS    0x80

#define RX_FIFO_ERROR       0x11

#define PKTBUFSIZE 8  //5 packets for circular buffer
#define CCPKTLENGTH 128 //64 + 2 status + 1 length + 1 flutterState(rx,tx,rxSucceed, txSucceed, rxFailed, txFailed)

class CC1200
{

public:

	CC1200_STATE state;

	volatile uint8_t chipStatus;
	bool asleep;
	
	CC1200()
	{
		chipStatus = 0;
		asleep = false;
	}
	~CC1200()
	{
		bcm2835_spi_end();
		bcm2835_close();
	}
	bool init();
	uint8_t getState();
	//void flushRX();
	//void flushTX();
	void reset();
	void enterSleep();
	void exitSleep();
	bool transmit(uint8_t data[], uint8_t start, uint8_t length);
	//readRX 큐 설정한 후에 복구할것.
	bool readRX(Queue& rxBuffer, uint8_t bytesToRead);
	uint8_t bytesAvailable();
	uint8_t readRSSI();

	bool sleep(bool _sleep);

	uint8_t ccGetTxStatus(void);
	uint8_t ccGetRxStatus(void);
	bool SetFrequency(uint32_t frequency);
	void setAddress(uint8_t address);
	bool txBytes(uint8_t _bytes);
	void setBand(uint8_t _band);

	uint8_t printMARC();

	void clearRXFIFO();

	//configutation
	uint16_t registerConfig(void);

	CC1200_STATE setState(CC1200_STATE setState);


	void WriteReg(uint16_t, uint8_t);
	uint8_t ReadReg(uint16_t);
	void ReadBurstReg(uint8_t addr, uint8_t *buffer, uint8_t count);
	void WriteBurstReg(uint8_t addr, uint8_t *buffer, uint8_t count);
	void readConfigRegs(void);


	//SPI communications
	void ccReadWriteBurstSingle(uint8_t addr, uint8_t *pData, uint16_t len, uint16_t dataStart);
	uint8_t cc16BitRegAccess(uint8_t accessType, uint8_t extAddr, uint8_t regAddr, uint8_t *pData, uint16_t len);
	uint8_t cc8BitRegAccess(uint8_t accessType, uint8_t addrByte, uint8_t *pData, uint16_t len, uint16_t dataStart);
	uint8_t SendStrobe(uint8_t);
	uint8_t SPItransfer(uint8_t dataOut);

	//register access
	uint8_t ccWriteReg(uint16_t addr, uint8_t *pData, uint8_t len);
	uint8_t ccReadReg(uint16_t addr, uint8_t *pData, uint8_t len);
	uint8_t ccWriteTxFifo(uint8_t *pData, uint8_t len);
	uint8_t ccReadRxFifo(uint8_t * pData, uint8_t len, uint16_t dataStart);
	
	//for gpio control
	void digitalWrite(uint8_t pin, uint8_t on);
	uint8_t digitalRead(uint8_t pin);
	void pinMode(uint8_t pin, uint8_t mode);

private:
#ifdef DEBUG
	//debugging
	void printBuffer(uint8_t *buffer, uint8_t length);
	void printReg(uint16_t reg, String name);

 #endif /* DEBUG */

};


#endif /* CC1200_H */