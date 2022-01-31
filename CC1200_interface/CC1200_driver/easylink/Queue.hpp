#ifndef Queue_h
#define Queue_h
#include <stdint.h>
#define QUEUESIZE 128

class Queue
{

public:
	uint8_t array[QUEUESIZE];
	uint8_t end;
	Queue();
	~Queue();
	void insert(uint8_t data);
	int read();
	bool write(uint8_t);
	void clear();
	uint8_t bytesAvailable();
	uint8_t bytesEnd();
	uint8_t capacity();
};

#endif