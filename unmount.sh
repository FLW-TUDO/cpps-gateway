#!/bin/sh

if [ $# -eq 0 ]
	then
		echo "No arguments supplied!"
		exit -1
fi

if [ "$1" = "AP1" ]
	then
		sudo fusermount -u ~/AP1/
		exit 0
elif [ "$1" = "AP2" ]
	then
		sudo fusermount -u ~/AP2/
		exit 0
elif [ "$1" = "AP3" ]
	then
		sudo fusermount -u ~/AP3/
		exit 0
fi
