#include "REG_CC1200.h"

static const registerSetting_t preferredSettings[]= {
   {CC1200_IOCFG2,              0x06},
   {CC1200_SYNC_CFG1,           0xA9},
   {CC1200_MODCFG_DEV_E,        0x0B},
   {CC1200_PREAMBLE_CFG1,       0x30},
   {CC1200_PREAMBLE_CFG0,       0x8A},
   {CC1200_IQIC,                0xC8},
   {CC1200_CHAN_BW,             0x10},
   {CC1200_MDMCFG1,             0x40},
   {CC1200_MDMCFG0,             0x05},
   {CC1200_SYMBOL_RATE2,        0x8F},
   {CC1200_SYMBOL_RATE1,        0x75},
   {CC1200_SYMBOL_RATE0,        0x10},
   {CC1200_AGC_REF,             0x27},
   {CC1200_AGC_CS_THR,          0xEE},
   {CC1200_AGC_CFG1,            0x11},
   {CC1200_AGC_CFG0,            0x94},
   {CC1200_FIFO_CFG,            0x00},
   {CC1200_DEV_ADDR,            0xAA},
   {CC1200_FS_CFG,              0x12},
   {CC1200_PKT_CFG2,            0x00},
   {CC1200_PKT_CFG1,            0x53},
   {CC1200_PKT_CFG0,            0x20},
   {CC1200_RFEND_CFG1,          0x3F},
   {CC1200_RFEND_CFG0,          0x30},
   {CC1200_PKT_LEN,             0x7F},
   {CC1200_IF_MIX_CFG,          0x1C},
   {CC1200_FREQOFF_CFG,         0x22},
   {CC1200_TOC_CFG,             0x03},
   {CC1200_MDMCFG2,             0x02},
   {CC1200_FREQ2,               0x56},
   {CC1200_FREQ1,               0x4F},
   {CC1200_FREQ0,               0x5C},
   {CC1200_IF_ADC1,             0xEE},
   {CC1200_IF_ADC0,             0x10},
   {CC1200_FS_DIG1,             0x07},
   {CC1200_FS_DIG0,             0xAF},
   {CC1200_FS_CAL1,             0x40},
   {CC1200_FS_CAL0,             0x0E},
   {CC1200_FS_DIVTWO,           0x03},
   {CC1200_FS_DSM0,             0x33},
   {CC1200_FS_DVC0,             0x17},
   {CC1200_FS_PFD,              0x00},
   {CC1200_FS_PRE,              0x6E},
   {CC1200_FS_REG_DIV_CML,      0x1C},
   {CC1200_FS_SPARE,            0xAC},
   {CC1200_FS_VCO4,             0x10},
   {CC1200_FS_VCO2,             0x4A},
   {CC1200_FS_VCO1,             0x9C},
   {CC1200_FS_VCO0,             0xB5},
   {CC1200_IFAMP,               0x09},
   {CC1200_XOSC5,               0x0E},
   {CC1200_XOSC1,               0x03},
   {CC1200_IQIE_I1,             0xFF},
   {CC1200_IQIE_I0,             0xBB},
   {CC1200_IQIE_Q1,             0xFF},
   {CC1200_CHFILT_Q0,           0x09},
};





const uint8_t chanList[17][3] =
{
    {0x0A, 0x57, 0x56},   //  Channel 00 -> 863.399963
    {0x47, 0x61, 0x56},   //  Channel 01 -> 863.799896
    {0x85, 0x6B, 0x56},   //  Channel 02 -> 864.199982
    {0xC2, 0x75, 0x56},   //  Channel 03 -> 864.599915
    {0x00, 0x80, 0x56},   //  Channel 04 -> 865.000000
    {0x3D, 0x8A, 0x56},   //  Channel 05 -> 865.399933
    {0x7A, 0x94, 0x56},   //  Channel 06 -> 865.799866
    {0xB8, 0x9E, 0x56},   //  Channel 07 -> 866.199951
    {0xF5, 0xA8, 0x56},   //  Channel 08 -> 866.599884
    {0x33, 0xB3, 0x56},   //  Channel 09 -> 866.999969
    {0x70, 0xBD, 0x56},   //  Channel 10 -> 867.399902
    {0xAE, 0xC7, 0x56},   //  Channel 11 -> 867.799988
    {0xEB, 0xD1, 0x56},   //  Channel 12 -> 868.199921
    {0x28, 0xDC, 0x56},   //  Channel 13 -> 868.599854
    {0x66, 0xE6, 0x56},   //  Channel 14 -> 868.999939
    {0xA4, 0xF0, 0x56},   //  Channel 15 -> 869.400024
    {0xE1, 0xFA, 0x56},   //  Channel 16 -> 869.799957
};
