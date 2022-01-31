//Test program for WiringPi + bcm2835 library
//Goal is to make a program works with wiringPi Interrupt(ISR)
//tested on RPi 3

//how to compile : 
// pi@raspberrypi $ g++ wiringPi_bcm2835_isr_test.cpp CC1200.cpp Queue.cpp -o ISRtest.app -lbcm2835 -lwiringPi
//how to execute :
// pi@raspberrypi $ sudo ./ISRtest.app


#include <wiringPi.h>
#include "CC1200.hpp"

#include <errno.h>
#include <stdlib.h>
#include <stdio.h>

#define BUTTON_PIN	0
static volatile int globalCounter = 0;

void myInterrupt(void){
	++globalCounter;
}
using namespace std;

void noInterrupt(void){
	system ("/usr/local/bin/gpio edge 17 none");
}

void enInterrupts(void){
	system ("/usr/local/bin/gpio edge 17 rising") ;
}

int main(){

	int myCounter = 0 ;
	CC1200 cc;
	if(!cc.init()){
		cout<<"init done!"<<endl;
	}
	if (wiringPiSetup () < 0)
	{
		fprintf (stderr, "Unable to setup wiringPi: %s\n", strerror (errno)) ;
		return 1 ;
	}

	if (wiringPiISR (BUTTON_PIN, INT_EDGE_FALLING, &myInterrupt) < 0)
	{
		fprintf (stderr, "Unable to setup ISR: %s\n", strerror (errno)) ;
		return 1 ;
	}
	int a = 0;

	for (;;)
	{
		printf ("Waiting ... ") ; fflush (stdout) ;

		while (myCounter == globalCounter)
			delay (100) ;

		printf (" Done. counter: %5d\n", globalCounter) ;
		noInterrupt();
		myCounter = globalCounter ;
		break;
	}
	enInterrupts();
	for (;;)
	{
		printf ("\aWaiting ... ") ; fflush (stdout) ;

		while (myCounter == globalCounter)
			delay (100) ;

		printf (" Done. counter: %5d\n", globalCounter) ;
		myCounter = globalCounter ;
		break;
	}
	cc.registerConfig();
}