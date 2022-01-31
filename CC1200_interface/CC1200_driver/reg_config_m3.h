// Modulation format = 2-GFSK
// RX filter BW = 50.505051
// Packet bit length = 0
// Device address = 0
// Carrier frequency = 915.000000
// Manchester enable = false
// Packet length mode = Variable
// Whitening = true
// Bit rate = 20
// Address config = Address checking, 0x00 is broadcast address.
// Symbol rate = 20
// Deviation = 12.5kHz
// Packet length = 255

#include "REG_CC1200.h"


static const registerSettings settings_m3[] =
{
{CC1200_IOCFG2, 0x06},
{CC1200_SYNC_CFG1, 0xAC},
{CC1200_DEVIATION_M, 0xD7},
{CC1200_MODCFG_DEV_E, 0x1A},
{CC1200_DCFILT_CFG, 0x13},
{CC1200_PREAMBLE_CFG0, 0xE3},
{CC1200_IQIC, 0x00},
{CC1200_CHAN_BW, 0x81},
{CC1200_MDMCFG0, 0x02},
{CC1200_SYMBOL_RATE2, 0x5F},
{CC1200_SYMBOL_RATE1, 0x75},
{CC1200_SYMBOL_RATE0, 0x10},
{CC1200_AGC_REF, 0x48},
{CC1200_AGC_CS_THR, 0xEC},
{CC1200_AGC_CFG3, 0x31},
{CC1200_AGC_CFG1, 0x24},
{CC1200_AGC_CFG0, 0x9F},
{CC1200_FIFO_CFG, 0x00},
{CC1200_FS_CFG, 0x12},
{CC1200_PKT_CFG2, 0x00},
{CC1200_PKT_CFG0, 0x20},
{CC1200_ASK_CFG, 0xBF},
{CC1200_PKT_LEN, 0xFF},
{CC1200_IF_MIX_CFG, 0x1C},
{CC1200_FREQOFF_CFG, 0x00},
{CC1200_MDMCFG2, 0xFC},
{CC1200_FREQ2, 0x56},
{CC1200_FREQ1, 0xCC},
{CC1200_FREQ0, 0xCC},
{CC1200_IF_ADC1, 0xEE},
{CC1200_IF_ADC0, 0x10},
{CC1200_FS_DIG1, 0x07},
{CC1200_FS_DIG0, 0xA0},
{CC1200_FS_CAL1, 0x40},
{CC1200_FS_CAL0, 0x0E},
{CC1200_FS_DIVTWO, 0x03},
{CC1200_FS_DSM0, 0x33},
{CC1200_FS_DVC0, 0x17},
{CC1200_FS_PFD, 0x00},
{CC1200_FS_PRE, 0x6E},
{CC1200_FS_REG_DIV_CML, 0x1C},
{CC1200_FS_SPARE, 0xAC},
{CC1200_FS_VCO0, 0xB5},
{CC1200_IFAMP, 0x09},
{CC1200_XOSC5, 0x0E},
{CC1200_XOSC1, 0x03},
};
