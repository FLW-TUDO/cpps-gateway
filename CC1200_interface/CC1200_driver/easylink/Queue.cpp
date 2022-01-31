#include "Queue.hpp"

Queue::Queue()
{
	end = 0;
}

Queue::~Queue()
{
	//delete[] array;
}


bool Queue::write(uint8_t data)
{
	if (bytesAvailable() < 1)
	{
		return false;
	}

	array[end] = data;
	end++;
	return true;
}

void Queue::clear()
{
	end = 0;
}


int Queue::read()
{
	if (end == 0)
	{
		return -1;
	}

	uint8_t next = array[0];

	for (int i = 0; i < end; i++)
	{
		array[i] = array[i + 1]; //yes this is a dumb but quick way of dealing with the array. Feel free to improve it...
	}

	end--;
	return next;
}

uint8_t Queue::bytesAvailable()
{
	return QUEUESIZE - end;
}

uint8_t Queue::bytesEnd()
{
	return end;
}


uint8_t Queue::capacity()
{
	return QUEUESIZE;
}