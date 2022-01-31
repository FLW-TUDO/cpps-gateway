#!/bin/sh

if [ $# -eq 0 ]
	then
		echo "No arguments supplied!"
		exit -1
fi

if [ "$1" = "AP1" ]
	then
		sudo sshfs AP1@192.168.2.11:/home/AP1/ ~/AP1/ -o idmap=user -o allow_other
		exit 0
elif [ "$1" = "AP2" ]
	then
		sudo sshfs AP2@192.168.2.12:/home/AP2/ ~/AP2/ -o idmap=user -o allow_other
		exit 0
elif [ "$1" = "AP3" ]
	then
		sudo sshfs AP3@192.168.2.13:/home/AP3/ ~/AP3/ -o idmap=user -o allow_other
		exit 0
fi
