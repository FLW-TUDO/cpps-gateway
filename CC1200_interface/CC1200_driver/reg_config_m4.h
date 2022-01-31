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

/* moved to REG_CC1200.h
typedef struct
{
	int addr;
	uint8_t data;
} registerSettings;*/

static const registerSettings settings_m4[] =
{
   {CC1200_IOCFG2,            0x06},
  {CC1200_SYNC3,             0x6F},
  {CC1200_SYNC2,             0x4E},
  {CC1200_SYNC1,             0x90},
  {CC1200_SYNC0,             0x4E},
  {CC1200_SYNC_CFG1,         0xE5},
  {CC1200_SYNC_CFG0,         0x23},
  {CC1200_DEVIATION_M,       0x47},
  {CC1200_MODCFG_DEV_E,      0x0B},
  {CC1200_DCFILT_CFG,        0x56},
  {CC1200_PREAMBLE_CFG0,     0xBA},
  {CC1200_IQIC,              0xC8},
  {CC1200_CHAN_BW,           0x43},
  {CC1200_MDMCFG1,           0x42},
  {CC1200_MDMCFG0,           0x05},
  {CC1200_SYMBOL_RATE2,      0x94},
  {CC1200_SYMBOL_RATE1,      0x7A},
  {CC1200_SYMBOL_RATE0,      0xE1},
  {CC1200_AGC_REF,           0x2B},
  {CC1200_AGC_CS_THR,        0xF1},
  {CC1200_AGC_CFG1,          0x11},
  {CC1200_AGC_CFG0,          0x90},
  {CC1200_FIFO_CFG,          0x00},
  {CC1200_FS_CFG,            0x12},
  {CC1200_PKT_CFG0,          0x20},
  {CC1200_PKT_LEN,           0xFF},
  {CC1200_IF_MIX_CFG,        0x18},
  {CC1200_TOC_CFG,           0x03},
  {CC1200_MDMCFG2,           0x02},
  {CC1200_FREQ2,             0x56},
  {CC1200_FREQ1,             0xCC},
  {CC1200_FREQ0,             0xCC},
  {CC1200_IF_ADC1,           0xEE},
  {CC1200_IF_ADC0,           0x10},
  {CC1200_FS_DIG1,           0x04},
  {CC1200_FS_DIG0,           0x50},
  {CC1200_FS_CAL1,           0x40},
  {CC1200_FS_CAL0,           0x0E},
  {CC1200_FS_DIVTWO,         0x03},
  {CC1200_FS_DSM0,           0x33},
  {CC1200_FS_DVC1,           0xF7},
  {CC1200_FS_DVC0,           0x0F},
  {CC1200_FS_PFD,            0x00},
  {CC1200_FS_PRE,            0x6E},
  {CC1200_FS_REG_DIV_CML,    0x1C},
  {CC1200_FS_SPARE,          0xAC},
  {CC1200_FS_VCO0,           0xB5},
  {CC1200_IFAMP,             0x05},
  {CC1200_XOSC5,             0x0E},
  {CC1200_XOSC1,             0x03},
};