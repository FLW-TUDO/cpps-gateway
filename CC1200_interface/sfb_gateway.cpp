#include "sfb_gateway_defines.h"

using namespace std;
using namespace std::chrono;

void printHelp(char *argv[]){
  printf("Usage: %s [-1 <channel>] [-2 <channel>] [-3 <channel>] [-4 <channel>] [-f <filename>] [-s] [-i <id>]\n", argv[0]);
  printf("\t<channel>: 0-%d\n",SRD_MAX_CHANNEL);
  printf("\t-f <filename>: logfile name. Module name and ending will be added automatically (e.g. <filename>_M1.txt)\n");
  printf("\t-s: Single logfile. Don't use seperate logfiles for each module.\n");
  printf("\t-i <id>: Gateway ID. Can be 1, 2, or 3.\n");
  printf("\t-b <seconds>: Beacon interval in seconds\n");
  printf("\t-t <seconds>: Exercise time in seconds. Will be send to the nodes. Nodes will send their response after this time\n");
  printf("\t-g <num>: Number of start broadcasts that will be send on program start\n");
  printf("\t-h: Show this help.\n");
  printf("Example: sudo %s -1 0 -2 4 -4 15 -f log_2017_06_21\n",  argv[0]);
}

thread radioThread, readFifoThread;

int main(int argc, char *argv[])
{
	std::cout << "SFB Gateway" << std::endl;

	struct sigaction sigIntHandler;

	sigIntHandler.sa_handler = exitHandler;
	sigemptyset(&sigIntHandler.sa_mask);
	sigIntHandler.sa_flags = 0;

	sigaction(SIGINT, &sigIntHandler, NULL);

	int opt;
	opterr = 0;

	while ((opt = getopt(argc, argv, "1:2:3:4:f:shi:b:t:g:n:")) != -1) {
		switch (opt) {
		case '1':
			use_m1 = true;
			if(atoi(optarg) > SRD_MAX_CHANNEL){
			  std::cout << "M1 Invalid channel: " << atoi(optarg) << ", using channel " << (int)m1.channel << " instead" <<  std::endl;
			}
			else{
			  m1.channel = atoi(optarg);
			}
			 std::cout << "\033[1;33mM1 using channel " << (int)m1.channel << "\033[0m"<< std::endl;
			break;
		case '2':
			use_m2 = true;
		   if(atoi(optarg) > SRD_MAX_CHANNEL){
			  std::cout << "M2 Invalid channel: " << atoi(optarg) << ", using channel " << (int)m2.channel << " instead" <<  std::endl;
			}
			else{
			  m2.channel = atoi(optarg);
			}
			std::cout << "\033[1;33mM2 using channel " << (int)m2.channel << "\033[0m"<< std::endl;
			break;
		case '3':
			use_m3 = true;
		   if(atoi(optarg) > SRD_MAX_CHANNEL){
			  std::cout << "\033[1;31mM3 Invalid channel: " << atoi(optarg) << ", using channel " << (int)m3.channel << " instead\033[0m" <<  std::endl;
			}
			else{
			  m3.channel = atoi(optarg);
			}
			std::cout << "\033[1;33mM3 using channel " << (int)m3.channel << "\033[0m"<< std::endl;
			break;
		case '4':
			use_m4 = true;
		   if(atoi(optarg) > SRD_MAX_CHANNEL){
			  std::cout << "M4 Invalid channel: " << atoi(optarg) << ", using channel " << (int)m4.channel << " instead" <<  std::endl;
			}
			else{
			  m4.channel = atoi(optarg);
			}
			std::cout << "\033[1;33mM4 using channel " << (int)m4.channel << "\033[0m"<< std::endl;
			break;
		  break;
		default: /* '?' */
			printHelp(argv);
			exit(EXIT_FAILURE);
		}
	}

	if(!(use_m1 || use_m2 || use_m3 || use_m4)){
		printHelp(argv);
		exit(EXIT_FAILURE);
	}

	if(!gpioInit()){
		cout << "gpioInit(): ERROR" << endl;
		exit(-1);
	} else {
		#ifdef DEBUG_STATES
		cout << "gpioInit(): OK" << endl;
		#endif
	}

	int ret = initFifos();
	
	if( ret ){
		//~ #ifdef DEBUG_STATES
		cout << "initFifos() failed: " << ret << endl;
		//~ #endif
	}

	if ( wiringPiSetup() < 0 ) {
		fprintf (stderr, "Unable to setup wiringPi: %s\n", strerror (errno)) ;
		exit(-1);
	} else {
		#ifdef DEBUG_STATES
		cout << "wiringPiSetup: OK!" << endl;
		#endif
	}

	// strip = LPD8806(3, LED_DATA_PIN, LED_CLK_PIN);
	strip.begin();
	strip.show();

	initLED();

	initModules();
	#ifdef DEBUG_STATES
	cout << "initModules done!" << endl;
	#endif
    

	radioThread = thread(radioLoop);
	readFifoThread = thread(readFifoLoop);
	//~ radioLoop();
	readFifoThread.join();
	cout << "readFifoThread done" << endl;
	radioThread.join();
	cout << "radioThread done" << endl;
	return 0;
}

void readFifoLoop(){
  APPacket pkt;
	cout << "Waiting for data in TX_FIFO (" << TX_FIFO_PATH << ")" << endl;
	
	while(1){
		FILE *tx_fifo = fopen(TX_FIFO_PATH, "r");
		fread(&pkt, sizeof(pkt), 1, tx_fifo);
        //~ cout << "sending " << pkt.packet.payload << " on module: " << (int)pkt.module_num << endl;

    switch(pkt.module_num){
      case 1:
        cc1200_m1.send(pkt.packet);
        blinkLED(0x00FF00, 100);
        break;
      case 2:
        cc1200_m2.send(pkt.packet);
        blinkLED(0x00FF00, 100);
        break;
      case 3:
        cc1200_m2.send(pkt.packet);
        blinkLED(0x00FF00, 100);
        break;
      case 4:
        cc1200_m4.send(pkt.packet);
        blinkLED(0x00FF00, 100);
        break;
      default:
        cout << "invalid module number: " << pkt.module_num << endl;
    }
		bcm2835_delay(75); // TODO: Better solution with interrupts  semaphores...
		
		fclose(tx_fifo);
	}
}

void handlePacket(CCPHYPacket& packet, CC1200& module){
  
	if(!PACKET_CRC_OK(packet)){
		cout << "CRC Error" << endl;
		// Blink red to show corrupted packet was received
		blinkLED(0x00FF00, 100);
		return;
	}

	// Blink green to show packet was received
	blinkLED(0x0000FF, 100);


	// write packet to RX_FIFO
  //~ cout << "handling packet..." << endl;
  //~ cout << "status1: " << (int)packet.statusbyte1 << endl;
  //~ cout << "status2: " << (int)packet.statusbyte2 << endl;
  //~ cout << "address: " << hex << (int)packet.address << dec << endl;
  //~ cout << "length: " << (int)packet.length << endl;
  //~ cout << "payload: " << packet.payload << endl;
	APPacket p;
	p.module_num = module.getModule().number;
	p.packet = packet;
  
	FILE *rx_fifo = fopen(RX_FIFO_PATH, "a");
	int len = packet.length + 4 + sizeof(p.module_num);
	//~ fwrite(&p, len, 1, rx_fifo);
	//~ int len = packet.length + 4 + sizeof(p.module_num);
	//~ printf("writing to fifo (%d bytes): %*s\n", len, len, &p);
	fprintf(rx_fifo, "%*s\r\n", packet.length + 4 + sizeof(p.module_num), &p);
	fclose(rx_fifo);
	//~ cout << "written " << len << " Bytes to RX_FIFO" << endl;
}


void radioLoop(){

  uint8_t rxBuffer[128] = {0};
  uint8_t rxBytes;
  uint8_t marcStatus;
  
  cc1200_m1.SendStrobe(SIDLE);
  cc1200_m2.SendStrobe(SIDLE);
  cc1200_m3.SendStrobe(SIDLE);
  cc1200_m4.SendStrobe(SIDLE);


  if(use_m1){
      cc1200_m1.listen();
      cout << "M1 is in RX mode" << endl;
  }
  if(use_m2){
      cc1200_m2.listen();
     cout << "M2 is in RX mode" << endl;
  }
  if(use_m3){
      cc1200_m3.listen();
      cout << "M3 is in RX mode" << endl;
  }
  if(use_m4){
      cc1200_m4.listen();
      cout << "M4 is in RX mode" << endl;
  }
  

  while(TRUE){

    sema.p();
    while(cc1200_m1.packetAvailable()){
      CCPHYPacket packet = cc1200_m1.getPacket();
      handlePacket(packet, cc1200_m1);
    }
    while(cc1200_m2.packetAvailable()){
      CCPHYPacket packet = cc1200_m2.getPacket();
     handlePacket(packet, cc1200_m2);
    }
    while(cc1200_m3.packetAvailable()){
      CCPHYPacket packet = cc1200_m3.getPacket();
      handlePacket(packet, cc1200_m3);
    }
    while(cc1200_m4.packetAvailable()){
      CCPHYPacket packet = cc1200_m4.getPacket();
      handlePacket(packet, cc1200_m4);
    }

  }
  // Put radio to sleep and exit application
  cc1200_m1.SendStrobe(SPWD);
  cc1200_m2.SendStrobe(SPWD);
  cc1200_m3.SendStrobe(SPWD);
  cc1200_m4.SendStrobe(SPWD);
}



bool gpioInit(void){
  if(!bcm2835_init())
 	{
 		std::cout<<"bcm2835 init failed. Are you running as root?"<<strerror(errno)<<std::endl;
     return false;
 	}
 	if(!bcm2835_spi_begin())
 	{
 		std::cout<<"bcm2835 spi begin failed. "<<strerror(errno)<<std::endl;
     return false;
 	}

	bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);      	// The default
    bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);                   	// The default
    bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_32); 	    // /32 = 7.8 MHz
    bcm2835_spi_chipSelect(BCM2835_SPI_CS1);                      	// Actual value = CS0

    bcm2835_gpio_fsel(LED_DATA_PIN, OUTPUT);
    bcm2835_gpio_write(LED_DATA_PIN, 0);

    bcm2835_gpio_fsel(LED_CLK_PIN, OUTPUT);
    bcm2835_gpio_write(LED_CLK_PIN, 0);

  return true;
}

void initModules(){

// set all CS pins to high, regardless of whether or not the module is connected
// otherwise  some of the pins might be low, which causes errors if the module is connected but not used
bcm2835_gpio_fsel(m1.cs, OUTPUT);
bcm2835_gpio_write(m1.cs, 1);
bcm2835_gpio_fsel(m2.cs, OUTPUT);
bcm2835_gpio_write(m2.cs, 1);
bcm2835_gpio_fsel(m3.cs, OUTPUT);
bcm2835_gpio_write(m3.cs, 1);
bcm2835_gpio_fsel(m4.cs, OUTPUT);
bcm2835_gpio_write(m4.cs, 1);


  if(use_m1){
    // cc1200_m1.reset();
#ifdef DEBUG_STATES
    cout << "Module M1: " << endl;
    cout << "  init: " << flush;
#endif
      if(cc1200_m1.init(m1)){
#ifdef DEBUG_STATES
        cout << "OK!" << endl;
#endif
      }
      else{
 #ifdef DEBUG_STATES
        cout << "FAILED!" << endl;
#endif
      }

  }

   if(use_m2){
 #ifdef DEBUG_STATES
    cout << "Module M2: " << endl;
    cout << "  init: " << flush;
#endif
      if(cc1200_m2.init(m2)){
 #ifdef DEBUG_STATES
        cout << "OK!" << endl;
#endif
      }
      else{
 #ifdef DEBUG_STATES
        cout << "FAILED!" << endl;
#endif
      }
  }

   if(use_m3){
 #ifdef DEBUG_STATES
    cout << "Module M3: " << endl;
    cout << "  init: " << flush;
#endif
      if(cc1200_m3.init(m3)){
 #ifdef DEBUG_STATES
        cout << "OK!" << endl;
#endif
      }
      else{
 #ifdef DEBUG_STATES        
        cout << "FAILED!" << endl;
  #endif
      }
    
  }

   if(use_m4){
 #ifdef DEBUG_STATES
    cout << "Module M4: " << endl;
    cout << "  init: " << flush;
#endif
      if(cc1200_m4.init(m4)){
 #ifdef DEBUG_STATES
        cout << "OK!" << endl;
#endif
      }
      else{
#ifdef DEBUG_STATES
        cout << "FAILED!" << endl;
#endif
      }
  }

  // Perform hardware reset (toggle reset pin)
  // There is only one reset pin for all 4 Modules,
  // that is why the init and register config is done this way instead of putting the registerConfig() call 
  // into init()
  cc1200_m1.HWReset();
  cc1200_m3.HWReset();

  // Configure registers

  if(use_m1){
#ifdef DEBUG_STATES
     cout << "Module M1: " << endl;
#endif
    uint16_t regConfErr = cc1200_m1.registerConfig();
#ifdef DEBUG_STATES
     cout << "  registerConfig: ";
    if(regConfErr == 0){
      cout << "OK!" << endl;
    }
    else{
      cout << dec << regConfErr  << " Errors" << endl;
    }
#endif
    cc1200_m1.SendStrobe(SIDLE);
  }

  if(use_m2){
#ifdef DEBUG_STATES
     cout << "Module M2: " << endl;
#endif
    uint16_t regConfErr = cc1200_m2.registerConfig();
#ifdef DEBUG_STATES
     cout << "  registerConfig: ";
    if(regConfErr == 0){
      cout << "OK!" << endl;
    }
    else{
       cout << dec << regConfErr  << " Errors" << endl;
    }
#endif
    cc1200_m2.SendStrobe(SIDLE);
  }

  if(use_m3){
#ifdef DEBUG_STATES
     cout << "Module M3: " << endl;
#endif
    uint16_t regConfErr = cc1200_m3.registerConfig();
#ifdef DEBUG_STATES
     cout << "  registerConfig: ";
    if(regConfErr == 0){
      cout << "OK!" << endl;
    }
    else{
      cout<< dec << regConfErr  << " Errors" << endl;
    }
#endif
    cc1200_m3.SendStrobe(SIDLE);
  }

  if(use_m4){
#ifdef DEBUG_STATES
     cout << "Module M4: " << endl;
#endif
    uint16_t regConfErr = cc1200_m4.registerConfig();
#ifdef DEBUG_STATES
     cout << "  registerConfig: ";
    if(regConfErr == 0){
      cout << "OK!" << endl;
    }
    else{
       cout << dec << regConfErr  << " Errors" << endl;
    }
#endif
    cc1200_m4.SendStrobe(SIDLE);
  }
}

void initLED(){
  for(int i = 0; i < strip.numPixels(); i++){
    strip.setPixelColor(i, 0xFF0000);
  }
  strip.show();
}
void blinkLED(uint32_t color, int duration){
  for(int i = 0; i < strip.numPixels(); i++){
    strip.setPixelColor(i, color);
  }
  strip.show();
  timer.runLater(duration, true, &initLED);
}

void ledOff(){
  for(int i = 0; i < strip.numPixels(); i++){
    strip.setPixelColor(i, 0);
  }
  strip.show();
}

int initFifos(){
	int ret;
  
	remove(TX_FIFO_PATH);
 
	
	umask(0);
	ret = mkfifo(TX_FIFO_PATH, S_IRUSR | S_IRGRP | S_IROTH | S_IWOTH | S_IWUSR | S_IWGRP);
	
	if(ret){
		std::cout << "error creating " << TX_FIFO_PATH << ": " << ret << std::endl;
		return ret;
	}
	
	remove(RX_FIFO_PATH);

	ret = mkfifo(RX_FIFO_PATH, S_IRWXO | S_IRWXG | S_IRWXU | S_IWOTH | S_IWGRP | S_IWUSR);

	if(ret){
	std::cout << "error creating " << RX_FIFO_PATH << ": " << ret << std::endl;
	return ret;
	}
  
  return 0;

}

void exitHandler(int s){
  if(s == 2){
    ledOff();
  }
  remove(TX_FIFO_PATH);
  remove(RX_FIFO_PATH);
  exit(0);
  //~ std::terminate();
}
