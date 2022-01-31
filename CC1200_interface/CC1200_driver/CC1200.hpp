#ifndef CC1200_H
#define CC1200_H

#include <iostream>
#include <wiringPi.h>
#include <bcm2835.h>
#include <cerrno>
#include <iomanip>
#include <cstring>
#include <clocale>
#include <queue>

#include "Queue.hpp"
#include "REG_CC1200.h"
#include "CC1200_RPi_reg_config.h"
#include "semaphore.h"


#define MISO_CC1200 	RPI_V2_GPIO_P1_21
#define RESET_CC1200	RPI_V2_GPIO_P1_32

#define M1_CS RPI_V2_GPIO_P1_40
#define M2_CS RPI_V2_GPIO_P1_18
#define M3_CS RPI_V2_GPIO_P1_08
#define M4_CS RPI_V2_GPIO_P1_11

#define CONFIG_CC1200_MAX_PHY_PAYLOAD_LENGTH 255
#define CC1200_SIZE_OF_STATUS_FIELD 1
#define CC1200_SIZE_OF_LENGTH_FIELD 1
#define CC1200_SIZE_OF_ADDRESS_FIELD 1
#define CC1200_SIZE_OF_CRC_FIELD 1
#define CC1200_NUM_APPENDED_STATUS_BITS 2

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
    CC1200_RX, /// 1 RX mode
    CC1200_TX,  /// 2 transmitting active
    CC1200_FSTX, /// 3 fast transmit ready 
    CC1200_CALIBRATE, /// 4 = CALIBRATE (synthesizer is calibrating)
    CC1200_SETTLING,  /// 5 = Radio SETTLING
    CC1200_RXERROR,   /// 6 = RX FIFO Error
    CC1200_TXERROR, /// 7 = TX Fifo Error
} CC1200_STATE;

typedef struct module {
	unsigned int cs;
	unsigned int gpio0;
	unsigned int gpio2;
	unsigned int gpio3;
  	uint8_t channel;
	uint8_t number;
} module_t;

typedef struct __attribute__((packed)) {
        unsigned char statusbyte1;     // Contains RSSI
        unsigned char statusbyte2;     // 7 CRC_OK, 6:0 LQI (Link Quality Indicator)
        unsigned char length;          // Payload length only; This value will be corrected by send() and receive() automatically to the value expected by the CC1200 (e.g. adding address byte)
        unsigned char address;         // PHY Address
        unsigned char payload[CONFIG_CC1200_MAX_PHY_PAYLOAD_LENGTH - CC1200_SIZE_OF_LENGTH_FIELD + CC1200_NUM_APPENDED_STATUS_BITS];   //Payload
} CCPHYPacket;


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

using namespace std;

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
	bool init(module_t module);
	uint8_t getState();
	//void flushRX();
	//void flushTX();
	void reset();
	void HWReset();
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
	bool setChannel(uint8_t c);
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


	bool packetAvailable(){ return (packetQueue.size() > 0);}
	CCPHYPacket getPacket();
	CCPHYPacket receive(){ return getPacket(); }
	void send(CCPHYPacket& pkg);
	void listen();
	module_t getModule(){ return module; }

private:

#ifdef DEBUG
	//debugging
	void printBuffer(uint8_t *buffer, uint8_t length);
	void printReg(uint16_t reg, String name);

 #endif /* DEBUG */

 void _read_string(unsigned char buffer[], unsigned int len);
 void isr();
 void clearPackets();
 static void isr_m1(void);
 static void isr_m2(void);
 static void isr_m3(void);
 static void isr_m4(void);
 int CS_CC1200 = RPI_V2_GPIO_P1_18;
 uint8_t channel;
 queue<CCPHYPacket*> packetQueue;
 //CCPHYPacket pkt;
 //bool pktAvailable = false;
 module_t module;
};

extern CC1200 cc1200_m1, cc1200_m2, cc1200_m3, cc1200_m4;
extern Semaphore sema;

#endif /* CC1200_H */