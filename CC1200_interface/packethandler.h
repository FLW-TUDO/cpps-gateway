#ifndef SFB_PACKETHANDLER
#define SFB_PACKETHANDLER

#include "CC1200_driver/CC1200.hpp"

void handlePacket(CCPHYPacket& packet, CC1200& module);

#endif