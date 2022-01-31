/*
 *	@author	:	luiseok (http://luiseok.com)
 *	@file 	:	CC1200.cpp
 *	@brief	:	CC1200 class for Raspberry Pi. Tested on Raspberry Pi 2 / 3.
 *				Based on FlutterWireless Library (https://github.com/flutterwireless/FlutterWirelessLibrary)
 * 	@license:	GNU v3
*/

#include <math.h>
#include "CC1200.hpp"

#define FREQ_ADJ 0

void CC1200::digitalWrite(uint8_t pin, uint8_t on)
{
	bcm2835_gpio_write(pin,on);
}

uint8_t CC1200::digitalRead(uint8_t pin)
{
	return bcm2835_gpio_lev(pin);
}
void CC1200::pinMode(uint8_t pin, uint8_t mode)
{
	bcm2835_gpio_fsel(pin, mode);
}

 bool CC1200::init()
 {
 	if(!bcm2835_init())
 	{
 		std::cout<<"bcm2835 init failed. Are you running as root?"<<strerror(errno)<<std::endl;
 		setlocale(LC_MESSAGES, "ko_kr.utf8");
 		std::cout<<"bcm2835를 시작할 수 없습니다 : "<<strerror(errno)<<std::endl;
 		return false;
 	}
 	if(!bcm2835_spi_begin())
 	{
 		std::cout<<"bcm2835 spi begin failed. "<<strerror(errno)<<std::endl;
 		setlocale(LC_MESSAGES, "ko_kr.utf8");
 		std::cout<<"SPI를 시작할 수 없습니다. : "<<strerror(errno)<<std::endl;
 		return false;
 	}

	bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);      	// The default
    bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);                   	// The default
    bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_128); 	// 6.25MHz
    bcm2835_spi_chipSelect(BCM2835_SPI_CS1);                      	// Actual value = CS0
    //bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS0, LOW);      // the default
    
    pinMode(CS_CC1200, OUTPUT);
	
    //pinMode(MISO_CC1200, INPUT);	//does not need to handle MISO pin as INPUT.
    return true;
}

uint16_t CC1200::registerConfig(void)
{
	uint8_t	writeByte;
	uint8_t verifyVal;
	uint16_t errors = 0;

	reset();
	std::cout<<"reset done"<<std::endl;
	uint8_t registerCount = (sizeof(settings) / sizeof(registerSettings));

	// Write registers to radio
	for (uint16_t i = 0; i < registerCount; i++)
	{
		writeByte = settings[i].data;
		ccWriteReg(settings[i].addr, &writeByte, 1);
		ccReadReg(settings[i].addr, &verifyVal, 1);
		std::cout<<std::hex<<std::uppercase<<"addr : 0x"<<(int)settings[i].addr<<"\t write val : 0x"<<(int)writeByte<<"\tread val : 0x"<<(int)verifyVal<<std::endl;
		if (verifyVal != writeByte)
		{
			errors++;
			
			std::cout<<std::hex<<"Error writing to address 0x"<<(int)settings[i].addr<<". Value set as 0x"<<(int)writeByte<<" but read as 0x"<<(int)verifyVal<<std::endl;
		}
	}
	std::cout<<"\033[1;31mregister config done\033[0m"<<std::endl;
	return errors;
}



uint8_t CC1200::SendStrobe(uint8_t cmd)
{
	uint8_t rc;					//return value;
	// Pull CS_N low and wait for SO to go low before communication starts
	digitalWrite(CS_CC1200,0);
	//waiting for Slave Out 0 (stable)
	while(digitalRead(MISO_CC1200) == 1);

	rc = bcm2835_spi_transfer(cmd);

	digitalWrite(CS_CC1200,1);
	return (rc);
}

uint8_t CC1200::SPItransfer(uint8_t dataOut)
{
	uint8_t returnval = bcm2835_spi_transfer(dataOut);
#ifdef DEBUGSPI
	std::cout<<std::hex<<std::uppercase<<"in : "<<dataOut<<"\tout : "<<returnval<<std::endl;
#endif
	return returnval;
}

void CC1200::ccReadWriteBurstSingle(uint8_t addr, uint8_t *pData, uint16_t len, uint16_t dataStart)
{
	uint16_t i;
	pData += dataStart; //increment pdata pointer to the next available data slot in our queue array

	// std::cout<<"Length: ");
	// Serial.println(len);

	/* Communicate len number of bytes: if RX - the procedure sends 0x00 to push bytes from slave*/
	if (addr & RADIO_READ_ACCESS)
	{
		if (addr & RADIO_BURST_ACCESS)
		{
			for (i = 0; i < len; i++)
			{
				uint8_t data = SPItransfer(0x00);     /* Store pData from last pData RX */
				*pData = data;
				pData++;
			}
		}
		else
		{
			*pData = SPItransfer(0x00);
		}
	}
	else
	{
		if (addr & RADIO_BURST_ACCESS)
		{
			/* Communicate len number of bytes: if TX - the procedure doesn't overwrite pData */
			for (i = 0; i < len; i++)
			{
				SPItransfer(*pData);
				pData++;
			}
		}
		else
		{
			SPItransfer(*pData);
		}
	}
	;
	return;
}
uint8_t CC1200::cc8BitRegAccess(uint8_t accessType, uint8_t addrByte, uint8_t *pData, uint16_t len, uint16_t dataStart)
{
	uint8_t readValue;
	/* Pull CS_N low and wait for SO to go low before communication starts */
	digitalWrite(CS_CC1200, 0);

	while (digitalRead(MISO_CC1200) == 1);

	/* send register address uint8_t */
	/* Storing chip status */
	readValue = SPItransfer(accessType | addrByte);
// std::cout<<"[0x")
// std::cout<<accessType|addrByte,HEX);
// std::cout<<",[0x")
	ccReadWriteBurstSingle(accessType | addrByte, pData, len, dataStart);
	digitalWrite(CS_CC1200, 1);
	/* return the status uint8_t value */
	return (readValue);
}

uint8_t CC1200::cc16BitRegAccess(uint8_t accessType, uint8_t extAddr, uint8_t regAddr, uint8_t *pData, uint16_t len)
{
	uint8_t readValue;
	/* Pull CS_N low and wait for SO to go low before communication starts */
	digitalWrite(CS_CC1200, 0);

	while (digitalRead(MISO_CC1200) == 1);

	/* send extended address uint8_t with access type bits set */
	/* Storing chip status */
	readValue = SPItransfer(accessType | extAddr);
	SPItransfer(regAddr);
	/* Communicate len number of bytes */
	ccReadWriteBurstSingle(accessType | regAddr, pData, len, 0);
	digitalWrite(CS_CC1200, 1);
	/* return the status uint8_t value */
	return (readValue);
}

/******************************************************************************
 * @fn          cc120xSpiWriteReg
 *
 * @brief       Write value(s) to config/status/extended radio register(s).
 *              If len  = 1: Writes a single register
 *              if len  > 1: Writes len register values in burst mode
 *
 * input parameters
 *
 * @param       addr   - address of first register to write
 * @param       *pData - pointer to data array that holds bytes to be written
 * @param       len    - number of bytes to write
 *
 * output parameters
 *
 * @return      rfStatus_t
 */
uint8_t CC1200::ccWriteReg(uint16_t addr, uint8_t *pData, uint8_t len)
{
	uint8_t tempExt = (uint8_t)(addr >> 8);
	uint8_t tempAddr = (uint8_t)(addr & 0x00FF);
	uint8_t rc;

	/* Checking if this is a FIFO access - returns chip not ready */
	if ((SINGLE_TXFIFO <= tempAddr) && (tempExt == 0))
	{
		return STATUS_CHIP_RDYn_BM;
	}

	/* Decide what register space is accessed */
	if (tempExt == 0)
	{
		rc = cc8BitRegAccess((RADIO_BURST_ACCESS | RADIO_WRITE_ACCESS), tempAddr, pData, len, 0);
	}
	else if (tempExt == 0x2F)
	{
		rc = cc16BitRegAccess((RADIO_BURST_ACCESS | RADIO_WRITE_ACCESS), tempExt, tempAddr, pData, len);
	}

	//chipStatus = rc;
	return (rc);
}
/******************************************************************************
 * @fn          cc120xSpiReadReg
 *
 * @brief       Read value(s) from config/status/extended radio register(s).
 *              If len  = 1: Reads a single register
 *              if len != 1: Reads len register values in burst mode
 *
 * input parameters
 *
 * @param       addr   - address of first register to read
 * @param       *pData - pointer to data array where read bytes are saved
 * @param       len   - number of bytes to read
 *
 * output parameters
 *
 * @return      rfStatus_t
 */
uint8_t CC1200::ccReadReg(uint16_t addr, uint8_t *pData, uint8_t len)
{
	uint8_t tempExt = (uint8_t)(addr >> 8);
	uint8_t tempAddr = (uint8_t)(addr & 0x00FF);
	uint8_t returnval;

	if ((SINGLE_TXFIFO <= tempAddr) && (tempExt == 0))
	{
		return STATUS_CHIP_RDYn_BM;
	}

	/* Decide what register space is accessed */
	if (tempExt == 0)
	{
		returnval = cc8BitRegAccess((RADIO_BURST_ACCESS | RADIO_READ_ACCESS), tempAddr, pData, len, 0); //burst access is okay if we raise chip select after transfer (though I'm not sure why TI used burst here).
	}
	else if (tempExt == 0x2F)
	{
		returnval = cc16BitRegAccess((RADIO_BURST_ACCESS | RADIO_READ_ACCESS), tempExt, tempAddr, pData, len);
	}

	//chipStatus = returnval;
	return (returnval);
}

void CC1200::WriteReg(uint16_t addr, uint8_t value)
{
#ifdef DEBUG1
	uint8_t origValue;
	origValue = ReadReg(addr); //capture old value for debugging
#endif
	ccWriteReg(addr, &value, 1);
	uint8_t result = ReadReg(addr);
#ifdef DEBUG1
	std::cout<<std::hex<<std::uppercase<<"Address 0x"<<addr<<" was set to 0x"<<origValue<<". Now set to: 0x"<<result<<std::endl;

	if (result != value)
	{
		std::cout<<" Read value does not match set value of 0x"<<std::hex<<std::uppercase<<value<<std::endl;
	}
#endif
}

uint8_t CC1200::ReadReg(uint16_t addr)
{
	uint8_t data;
	ccReadReg(addr, &data, 1);
	return data;
}

bool CC1200::sleep(bool _sleep)
{
	asleep = _sleep;

	if (asleep)
	{
		setState(CC1200_IDLE);
	}
	else
	{
		setState(CC1200_RX);
	}

	return true;
}

void CC1200::setAddress(uint8_t address)
{
	WriteReg(REG_DEV_ADDR, address);
}
//sets the frequency for the radio oscillator.
//int frequency = desired center frequency in Hz
//returns true if success, or false if failure. Should not fail.
bool CC1200::SetFrequency(uint32_t frequency)
{
	//digitalWrite(8,HIGH);
	setState(CC1200_IDLE);
	SendStrobe(SFRX);
	int freq = 0.0065536f * frequency; //magic number comes from simplification of calculations from the datasheet with 40MHz crystal and LO Divider of 4.
	uint8_t f0 = 0xFF & freq;
	uint8_t f1 = (freq & 0xFF00) >> 8;
	uint8_t f2 = (freq & 0xFF0000) >> 16;
#ifdef DEBUG_FREQUENCY
	std::cout<<"Programming Frequency "<<frequency<<" MHz. Registers 0, 1, and 2 are 0x"<<std::hex<<std::uppercase<<f0<<" 0x"<<f1<<" 0x"f2<<std::endl;
#endif
	WriteReg(REG_FREQ0, f0);
	WriteReg(REG_FREQ1, f1);
	WriteReg(REG_FREQ2, f2);
	setState(CC1200_RX);

	if (ReadReg(REG_FREQ0) == f0 && ReadReg(REG_FREQ1) == f1 && ReadReg(REG_FREQ2) == f2)
	{
		//digitalWrite(8,LOW);
		return true;
	}
	else
	{
		//digitalWrite(8,LOW);
		return false;
	}
}

#ifdef DEBUG1

uint8_t CC1200::printMARC()
{
	uint8_t marcState = ReadReg(REG_MARCSTATE);

	switch (marcState >> 5)
	{
		case 0:
			std::cout<<"Marc Settling"<<std::endl;
			break;

		case 1:
			std::cout<<"Marc TX"<<std::endl;
			break;

		case 2:
			std::cout<<"Marc IDLE"<<std::endl;
			break;

		case 3:
			std::cout<<"Marc RX"<<std::endl;
			break;
	}

	std::cout<<"Marc State: 0x"<<std::hex<<(int)(marcState & 0x1F)<<std::endl;
	return marcState;
}


void CC1200::printRadioState(uint8_t state)
{
	switch (state)
	{
		case CC1200_IDLE:
			std::cout<<"CC1200_IDLE";
			break;

		case CC1200_RXWAIT:
			std::cout<<"CC1200_RXWAIT";
			break;

		case CC1200_RXACTIVE:
			std::cout<<"CC1200_RXACTIVE";
			break;

		case CC1200_RXREAD:
			std::cout<<"CC1200_RXREAD";
			break;

		case CC1200_TXSTART:
			std::cout<<"CC1200_TXSTART";
			break;

		case CC1200_TXACTIVE:
			std::cout<<"CC1200_TXACTIVE";
			break;

		default:
			break;
	}
}
#endif


uint8_t CC1200::readRSSI()
{
	return ReadReg(REG_RSSI1);
}

//*** Basic Radio Functions ***//
//*****************************//
//*****************************//

void CC1200::reset()
{
	SendStrobe(SRES);
	delay(5);
	SendStrobe(SRES); //is twice necessary? Probably not. Does it cause problems? You tell me...
}


bool CC1200::transmit(uint8_t *txBuffer, uint8_t start, uint8_t length)
{
	if (asleep == true)
	{
		return false;
	}

	//check FIFO and radio state here
	uint8_t txBytesUsed = 0;
	// Read number of bytes in TX FIFO
	ccReadReg(REG_NUM_TXBYTES, &txBytesUsed, 1);

	if (txBytesUsed > 0)
	{
		// Make sure that the radio is in IDLE state before flushing the FIFO
		setState(CC1200_IDLE);
		SendStrobe(SFTX); //flush buffer if needed
	}

	setState(CC1200_FSTX); //spin up frequency synthesizer
	uint8_t data[length];

	for (int i = 0; i < length; i++)
	{
		data[i] = txBuffer[i + start]; //TODO: alter fifo access functions to allow passing txBuffer directly to read or write from a specific chunk of it
	}

	ccWriteTxFifo(data, length); //TODO: do error checking for underflow, CCA, etc.

	setState(CC1200_TX); //spin up frequency synthesizer
	return true;
}

uint8_t CC1200::getState()
{
	//0 = IDLE, 		1 = RX, 		2 = TX, 		3 = FastTx ready
	//4 = CALIBRATE (synthesizer is calibrating), 		5 = SETTLING
	//6 = RX FIFO Error 7 = TX FIFO ERROR

	uint8_t state = (SendStrobe(0x00) >> 4) & 0x7;
	return (state);
}


CC1200_STATE CC1200::setState(CC1200_STATE setState)
{
	uint8_t currentState = getState(); //0 = IDLE, 1 = RX, 2 = TX, 3 = FastTX ready
	//4 = CALIBRATE (synthesizer is calibrating), 5 = SETTLING, 6 = RX FIFO Error, 7 = TX Fifo Error

	while (currentState != setState)
	{
#ifdef DEBUG_STATES
		std::cout<<"setState = "<<setState<<" currentState = "<<currentState<<std::endl;
#endif

		switch (currentState)
		{
			case CC1200_IDLE:
				switch (setState)
				{
					case CC1200_RX:
						SendStrobe(SRX);
						break;

					case CC1200_TX:
						SendStrobe(STX);
						break;

					case CC1200_FSTX:
						SendStrobe(SFSTXON);
						break;
				}

				currentState = getState();
				break;

			case CC1200_RX:
				switch (setState)
				{
					case CC1200_IDLE:
						SendStrobe(SIDLE);
						break;

					case CC1200_TX:
						SendStrobe(STX);
						break;

					case CC1200_FSTX:
						SendStrobe(SFSTXON);
						break;
				}

				currentState = getState();
				break;

			case CC1200_TX:
				switch (setState)
				{
					case CC1200_IDLE:
						SendStrobe(SIDLE);
						break;

					case CC1200_RX:
						SendStrobe(SRX);
						break;

					case CC1200_FSTX:
						SendStrobe(SFSTXON);
						break;
				}

				currentState = getState();
				break;

			case CC1200_FSTX:
				switch (setState)
				{
					case CC1200_IDLE:
						SendStrobe(SIDLE);
						break;

					case CC1200_TX:
						SendStrobe(STX);
						break;

					case CC1200_RX:
						SendStrobe(SRX);
						break;
				}

				currentState = getState();
				break;

			case CC1200_CALIBRATE:
				delayMicroseconds(50);
				currentState = getState();
				break;

			case CC1200_SETTLING:
				delayMicroseconds(50);
				currentState = getState();
				break;

			case CC1200_RXERROR:
				SendStrobe(SFRX);
				currentState = getState();
				break;

			case CC1200_TXERROR:
				SendStrobe(SFTX);
				currentState = getState();
				break;
		}
	}
	return (CC1200_STATE)currentState;
}

/*******************************************************************************
 * @fn          cc120xSpiWriteTxFifo
 *
 * @brief       Write pData to radio transmit FIFO.
 *
 * input parameters
 *
 * @param       *pData - pointer to data array that is written to TX FIFO
 * @param       len    - Length of data array to be written
 *
 * output parameters
 *
 * @return      rfStatus_t
 */
uint8_t CC1200::ccWriteTxFifo(uint8_t *pData, uint8_t len)
{
	uint8_t rc;
	rc = cc8BitRegAccess(0x00, BURST_TXFIFO, pData, len, 0);
	chipStatus = rc;
	return (rc);
}

/*******************************************************************************
 * @fn          cc120xSpiReadRxFifo
 *
 * @brief       Reads RX FIFO values to pData array
 *
 * input parameters
 *
 * @param       *pData - pointer to data array where RX FIFO bytes are saved
 * @param       len    - number of bytes to read from the RX FIFO
 *
 * output parameters
 *
 * @return      rfStatus_t
 */
uint8_t CC1200::ccReadRxFifo(uint8_t * pData, uint8_t len, uint16_t dataStart)
{
	uint8_t rc;
// Serial.print("Length1: ");
// Serial.println(len);
	rc = cc8BitRegAccess(0x00, BURST_RXFIFO, pData, len, dataStart);
	chipStatus = rc;
	return (rc);
}

/******************************************************************************
 * @fn      cc120xGetTxStatus(void)
 *
 * @brief   This function transmits a No Operation Strobe (SNOP) to get the
 *          status of the radio and the number of free bytes in the TX FIFO.
 *
 *          Status byte:
 *
 *          ---------------------------------------------------------------------------
 *          |          |            |                                                 |
 *          | CHIP_RDY | STATE[2:0] | FIFO_BYTES_AVAILABLE (free bytes in the TX FIFO |
 *          |          |            |                                                 |
 *          ---------------------------------------------------------------------------
 *
 *
 * input parameters
 *
 * @param   none
 *
 * output parameters
 *
 * @return  rfStatus_t
 *
 */
uint8_t CC1200::ccGetTxStatus(void)
{
	SendStrobe(SNOP);
	return (SendStrobe(SNOP));
}

/******************************************************************************
 *
 *  @fn       cc120xGetRxStatus(void)
 *
 *  @brief
 *            This function transmits a No Operation Strobe (SNOP) with the
 *            read bit set to get the status of the radio and the number of
 *            available bytes in the RXFIFO.
 *
 *            Status byte:
 *
 *            --------------------------------------------------------------------------------
 *            |          |            |                                                      |
 *            | CHIP_RDY | STATE[2:0] | FIFO_BYTES_AVAILABLE (available bytes in the RX FIFO |
 *            |          |            |                                                      |
 *            --------------------------------------------------------------------------------
 *
 *
 * input parameters
 *
 * @param     none
 *
 * output parameters
 *
 * @return    rfStatus_t
 *
 */
uint8_t CC1200::ccGetRxStatus(void)
{
	SendStrobe(SNOP | RADIO_READ_ACCESS);
	return (SendStrobe(SNOP | RADIO_READ_ACCESS));
}

uint8_t CC1200::bytesAvailable()
{
	uint8_t rxBytes = 0;
	// Read number of bytes in RX FIFO
	ccReadReg(REG_NUM_RXBYTES, &rxBytes, 1);
	return rxBytes;
}

void CC1200::clearRXFIFO()
{
	setState(CC1200_IDLE);
	SendStrobe(SFRX);
	setState(CC1200_RX);
#ifdef DEBUG
	std::cout<<"PACKET ERROR, CLEARED RX FIFO"<<std::endl;
#endif
}

bool CC1200::readRX(Queue& rxBuffer, uint8_t bytesToRead)
{
	uint8_t marcState;
	bool dataGood = false;

	//Serial.println("Bytes to Read: ");
    //Serial.println(bytesToRead);

	if (rxBuffer.bytesAvailable() < bytesToRead)
	{
#ifdef DEBUG
		std::cout<<"QUEUE CAPACITY INSUFFICIENT. PACKET OF LENGTH "<<bytesToRead<<" BYTES WILL NOT FIT IN QUEUE."<<std::endl;
#endif
		clearRXFIFO();
		return false;
	}

	// Read MARCSTATE to check for RX FIFO error
	ccReadReg(REG_MARCSTATE, &marcState, 1);

	// Mask out MARCSTATE bits and check if we have a RX FIFO error
	if ((marcState & 0x1F) == RX_FIFO_ERROR)
	{
#ifdef DEBUG
		std::cout<<"RX FIFO ERR"<<std::endl;
#endif
		// Flush RX FIFO
		setState(CC1200_IDLE);
		SendStrobe(SFRX);
		setState(CC1200_RX);
	}
	else
	{
		// Read n bytes from RX FIFO
		ccReadRxFifo(rxBuffer.array, (uint16_t)bytesToRead, rxBuffer.end);

		// Check CRC ok (CRC_OK: bit7 in second status uint8_t)
		// This assumes status bytes are appended in RX_FIFO
		// (PKT_CFG1.APPEND_STATUS = 1)
		// If CRC is disabled the CRC_OK field will read 1
		if (rxBuffer.array[rxBuffer.end + bytesToRead - 1] & 0x80)
		{
			//  Serial.println("CRC OK");
			// Update packet counter
			//  packetCounter++;
			dataGood = true;
			rxBuffer.end = rxBuffer.end + bytesToRead;
		}
		else
		{
#ifdef DEBUG
			std::cout<<"CRC BAD"<<std::endl;
#endif
			clearRXFIFO();
		}
	}

#ifdef DEBUG

	if (dataGood)
	{
		std::cout<<"RX buffer contains "<<bytesToRead<<" bytes.");
		printBuffer(rxBuffer.array, bytesToRead);
	}

#endif
	return dataGood;
}
#ifdef DEBUG
void CC1200::printBuffer(uint8_t *buffer, uint8_t length)
{
	for (int i = 0; i < length; i++)
	{
		std::cout<<std::hex<<std::uppercase<<"[0x"<<buffer[i]<<"]"<<std::endl;
	}
	uint8_tendl;
} 
#endif