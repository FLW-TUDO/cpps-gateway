import struct
import sys
import os
import subprocess
import json
import time
import datetime
import configparser
import serial
import threading
import signal

from models import log
from enum import Enum
from pathlib import Path


RX_FIFO = '/tmp/sfb_rxfifo'
TX_FIFO = '/tmp/sfb_txfifo'


'''
############################################################
'''


# Config settings
config_file_name = 'config.ini'
if not os.path.isfile(config_file_name):
    log(
        40,
        'CONFIG',
        'No config.ini file detected, please create and set up the configurations'
    )
    sys.exit(-1)
config_parser = configparser.ConfigParser()
config_parser.read(config_file_name)
if 'GatewayServer' not in config_parser or 'GatewayInterface' not in config_parser:
    log(
        40,
        'CONFIG',
        'No option for gateway server found in config file. Please create and set up!'
    )
    sys.exit(-1)
gs_config = config_parser['GatewayServer']
if_config = config_parser['GatewayInterface']


'''
############################################################
'''
      

'''
############################################################
'''


# Config settings
config_file_name = 'config.ini'
if not os.path.isfile(config_file_name):
    log(
        40,
        'CONFIG',
        'No cpps_task_config.ini file detected, please create and set up the configurations'
    )
    sys.exit(-1)
config_parser = configparser.ConfigParser()
config_parser.read(config_file_name)
if 'GatewayServer' not in config_parser:
    log(
        40,
        'CONFIG',
        'No option for gateway server found in config file. Please create and set up!'
    )
    sys.exit(-1)
gs_config = config_parser['GatewayServer']


'''
CCPacket is the packet format used by the driver for the CC1200 radio
on the Phynodes.
It consists of (in this order):
    size (Bytes)	element			description
    --------------------------------------------------------------------
    1 				status1			statusbyte 1 of the cc1200
                                    contains the RSSI of the received packet
                                    will be ignored for tx packets
    1				status2			statusbyte2 of the CC1200
                                    7 CRC_OK, 6:0 LQI (Link Quality Indicator)
                                    will be ignored for tx packets
    1				length			payload length of the packet that was received
                                    or payload length to be transmitted
    1				address			address to send the packet to. For tx only.
    1-126			payload			payload
'''


class CCPacket:
    def __init__(self, address=0, payload=bytearray(0)):
        if type(payload) is bytes:
            payload = bytearray(payload)
        elif type(payload) is not bytearray:
            raise TypeError("Payload of CCPacket must be %s but is %s" % (type(bytearray()), type(payload)))

        if type(address) is not int:
            raise TypeError("Address must be %s but is %s" % (type(int()), type(address)))

        self.status1 = 0
        self.status2 = 0
        self.length = len(payload)
        self.address = address
        self.payload = payload

    def __len__(self):
        return 4 + len(self.payload)

    def get_bytes(self):
        cc_pkt_format = 'BBBB%ds' % len(self.payload)
        bytes = struct.pack(cc_pkt_format, self.status1, self.status2, len(self.payload), self.address, self.payload)
        return bytes

    def get_rssi(self):
        return self.status1


'''
############################################################
'''


'''
APPacket is the packet format used by SFBGateway.app
Packets read from RX_FIFO will be in this format and packets written
to TX_FIFO need to have this format.

An APPacket consists of a module number, which is the number of the
CC1200 module to be used to send a packet / that a packet was received on,
and can therefore be in [0,4), since there are 4 CC1200 modules in an AP.

An APPAcket can be created by passing either a module number + CCPacket
or a module number, address  and payload to the constructor.

A packet can then be send by calling send(), which will write the packet to
TX_FIFO in the correct format.
'''


class APPacket:
    def __init__(self, *args, **kwargs):
        self.module = None
        self.pkt = None

        if len(args) is 2:
            self.init_cc(args[0], args[1])
        elif len(args) is 3:
            self.init_raw(args[0], args[1], args[2])
        else:
            raise ValueError("[APPacket]: Invalid number of arguments: %d\nMust be 2 (module, cc_pkt) or 3 (module, address, payload)" % len(args))

    def init_cc(self, module, cc_pkt):
        if not isinstance(cc_pkt, CCPacket):
            raise TypeError("[APPacket]: cc_pkt must be %s but is %s" % (type(CCPacket()), type(cc_pkt)))

        if type(module) is not int:
            raise TypeError("[APPacket]: module must be %s but is %s" % (type(int()), type(module)))

        if module not in range(0, 4):
            raise ValueError("[APPacket]: Invalid module number: %d (must be in %s)" % (module, range(0, 4)))

        self.module = module
        self.pkt = cc_pkt

    def init_raw(self, module, address, payload):
        cc = CCPacket(address, payload)
        self.init_cc(module, cc)

    def send(self):
        pkt_format = 'B%ds' % len(self.pkt)
        pkt = struct.pack(pkt_format, self.module, self.pkt.get_bytes())
        tx_fifo = open(TX_FIFO, 'wb')
        tx_fifo.write(pkt)
        tx_fifo.close()

        log(
            10,
            'AP_PACKET',
            'Send {:d} bytes on module {:d}: {} on addr: {}'.format(self.pkt.length, self.module, self.pkt.payload, self.pkt.address)
            )


'''
############################################################
'''


'''
The following code is copied from the 'gateway' script from the CNI Kratos
'''


class CCPhyStats(Enum):
    ENERGY = 1
    TX_SUCCESS_PKG = 2
    TX_SUCCESS_BYTE = 3
    RX_SUCCESS_PKG = 4
    RX_SUCCESS_BYTE = 5
    RX_FAIL_TOTAL = 6
    RX_FAIL_CRC = 7
    RX_FAIL_ADDR = 8
    RX_FAIL_EMPTY = 9
    RX_FAIL_INCONSISTENT = 10
    RX_FAIL_OVERFLOW = 11


'''
############################################################
'''


class CCPhyParser:

    def __init__(self):
        self.seqnr = 0
        self.replys_by_seqnr = self.create_list()
        log(20, 'CC_PHY_PARSER', 'Initialized!')

    def create_list(self):
        l = {}.fromkeys([i for i in range(0, 256)])
        for k in l.keys():
            l[k] = []
        return l
            
    def print(self):
        print(sorted(self.replys_by_seqnr.items()))

    def get_seqnr(self):
        return self.seqnr

    def log_by_seqnr(self, seqnr, reply):
        self.replys_by_seqnr[seqnr].append(reply)
    
    def get_by_seqnr(self, seqnr):
        result = self.replys_by_seqnr[seqnr]
        if len(result) != 0:
            self.replys_by_seqnr[seqnr] = []
        return result

    def _mkmsg(self, addr, *data):
        if len(data) > 1:
            bin_str = self._mkmsg_no_seq(addr, data[0], self.seqnr, ' '.join(map(lambda x: str(x), data[1:])))
        else:
            bin_str = self._mkmsg_no_seq(addr, data[0], self.seqnr)

        self.seqnr = (self.seqnr + 1) % 255
        return bin_str

    def _mkmsg_no_seq(self, addr, *data):
        base_str = ' '.join(map(lambda x: str(x), data))# + "\n"
        bin_str = base_str.encode('UTF-8')
        return bin_str

    def create_ping_request(self, addr):
        return self._mkmsg(addr, 'PING Q')

    def create_beacon_request(self, addr):
        return self._mkmsg(addr, 'BECN Q')

    def create_duid_request(self, addr):
        return self._mkmsg(addr, 'DUID Q')
    
    def create_bats_request(self, addr, energy):
        return self._mkmsg(addr, 'BATS Q', energy)

    def create_enum_request(self, addr):
        return self._mkmsg(addr, 'ENUM Q')

    def create_sadr_request(self, addr, uid, newaddr):
        return self._mkmsg(addr, 'SADR Q', uid, newaddr)

    def create_chnl_request(self, addr, channel):
        return self._mkmsg(addr, 'CHNL Q', channel)

    def create_poll_request(self, addr, ordernumber, descriptor):
        return self._mkmsg(addr, 'POLL Q', ordernumber, descriptor)

    def create_notify_msg(self, addr, descriptor, amount):
        return self._mkmsg_no_seq(addr, 'NTFY M', descriptor, amount)

    def create_notify_request(self, addr, descriptor, amount):
        return self._mkmsg(addr, 'NTFY Q', descriptor, amount)

    def create_deliver_msg(self, addr, amount):
        return self._mkmsg_no_seq(addr, 'DLVR M', amount)

    def create_deliver_request(self, addr, amount):
        return self._mkmsg(addr, 'DLVR Q', amount)

    def create_insert_request(self, addr, amount):
        return self._mkmsg(addr, 'ISRT Q', amount)

    def create_reserve_request(self, addr, ordernumber, amount):
        return self._mkmsg(addr, 'RSVE Q', ordernumber, amount)

    def create_set_item_request(self, addr, item, amount=0):
        return self._mkmsg(addr, 'SETI Q', item, amount)

    def create_start_msg(self, addr):
        return self._mkmsg_no_seq(addr, 'STRT M')

    def create_stop_msg(self, addr):
        return self._mkmsg_no_seq(addr, 'STOP M')

    def create_stat_request(self, addr, item):
        return self._mkmsg(addr, 'STAT Q', item)

    def create_butn_request(self, addr, buttonid):
        return self._mkmsg(addr, 'BUTN Q', buttonid)


'''
############################################################
'''


class RadioStats:
    def __init__(self, proto):
        self.pong_count = []
        self.seqnr = 0
        self.proto = proto
        self.final_stats = {}
        self.reset()
        self.csv_suffix = 'generic'
        self.runtime_stats_active = None
        self.runtime_stats = None
        self.seqnr_to_addr = None
        self.log_prefix = None
        log(20, 'RADIO_STATS', 'Initialized!')

    def reset(self):
        self.runtime_stats = {
            0: {
                'tx': 0,
                'rx': 0,
            }
        }
        self.runtime_stats_active = False
        self.seqnr_to_addr = [0 for i in range(0, 256)]

    def __call__(self):
        return self

    def set_suffix(self, suf):
        self.csv_suffix = suf

    def expect_rx(self, seqnr, addr):
        self.seqnr_to_addr[seqnr] = addr

    def ping_sent(self, seqnr):
        self.seqnr = seqnr
        self.pong_count.append(0)

    def add_pong(self, pong_seqnr):
        if pong_seqnr == self.seqnr:
            self.pong_count[-1] += 1
        else:
            sys.stderr.write(
                "[W] Received an invalid (delayed?) PONG.\n"
                + "[W] Expected seqnr {exp}, got seqnr {got}\n".format(
                    exp=self.seqnr, got=pong_seqnr
                )
            )

    def enable_runtime_stats(self, clients=[]):
        self.runtime_stats_active = True
        self.runtime_stats[0] = {
            'tx': 0,
            'rx': 0,
        }

        for client in clients:
            self.runtime_stats[client] = {
                'tx': 0,
                'rx': 0,
            }

    def disable_runtime_stats(self):
        self.runtime_stats_active = False

    def log_packet_by_seqnr(self, seqnr, direction):
        self.log_packet(self.seqnr_to_addr[seqnr], direction)

    def log_packet(self, addr, direction):
        if not self.runtime_stats_active:
            return

        if addr not in self.runtime_stats:
            return

        if addr == 0 and direction == 'tx':
            # broadcasts are sent to all clients
            for device in self.runtime_stats.values():
                device[direction] += 1
        else:
            self.runtime_stats[addr][direction] += 1

    def dump_stats(self):
        # print("Sent {ping} pings with an average of {pong:.1f} replies".format(
        # ping = len(self.pong_count),
        # pong = np.mean(self.pong_count)))

        self.final_stats[0] = dict([[x.name, {'seqnr': None, 'data': None}] for x in CCPhyStats])

        print("Sent {tx} broadcasts and received {rx} unknown/broadcast replies".format(
            tx=self.runtime_stats[0]['tx'],
            rx=self.runtime_stats[0]['rx'],
        ))

        buf = "ADDRESS,DUID," + ','.join([x.name for x in CCPhyStats])
        buf += ",AP_TX_SUCCESS_PKG,AP_RX_SUCCESS_PKG\n"
        for addr in sorted(self.final_stats.keys()):
            buf += "{addr},{duid}".format(addr=str(addr), duid='-1')
            str(addr)

            for stat in CCPhyStats:
                if self.final_stats[addr][stat.name]['data'] is None:
                    buf += ',-1'
                else:
                    buf += ',' + str(self.final_stats[addr][stat.name]['data'])

            if addr in self.runtime_stats:
                buf += ',' + str(self.runtime_stats[addr]['tx'])
                buf += ',' + str(self.runtime_stats[addr]['rx'])
            else:
                buf += ',-1,-1'

            buf += "\n"
        print(buf)
        with open("{pre}-{suf}.csv".format(pre=self.log_prefix, suf=self.csv_suffix), 'w') as f:
            f.write(buf)

    def gather(self, addr):
        # no clever code - just get that damn data somehow
        self.final_stats[addr] = dict([[x.name, {'seqnr': None, 'data': None}] for x in CCPhyStats])
        for statistic in CCPhyStats:
            self.final_stats[addr][statistic.name]['seqnr'] = self.proto.get_seqnr()
            # serial_write(self.proto.create_stat_request(addr, statistic.value))
            time.sleep(0.200)

    def add_final_stat(self, seqnr, data):
        for addr in self.final_stats.keys():
            for stat in CCPhyStats:
                if self.final_stats[addr][stat.name]['data'] is None:
                    if self.final_stats[addr][stat.name]['seqnr'] == seqnr:
                        self.final_stats[addr][stat.name]['data'] = data
                        return

        sys.stderr.write("[W] Receveid an invalid STAT reply\n")


'''
############################################################
'''


class LineReader:
    def __init__(self, stats, dhcp, preserver, proto):
        self.stats = stats
        self.dhcp = dhcp
        self.preserver = preserver
        self.proto = proto
        log(20, 'LINE_READER', 'Initialized!')

    def __call__(self):
        return self

    def parse_line(self, line):
        log(10, 'LINE_READER', str(line) + '\n')

        linedata = line.split(' ')

        if len(linedata) < 2:
            sys.stderr.write("[E] Invalid line: {li}".format(li=line))
            return
        
        tmstamp = time.strftime('%H:%M:%S', time.localtime())
        instr = linedata[0]
        mode = linedata[1]
        param = linedata[2:]

        # log(10, 'LINE_READER', 'inst: {} mode: {} param:{}'.format(instr, mode, str(param)))

        # we only care about replies
        if mode == 'R':
            if instr == 'PING':
                seqnr = int(param[0])
                # self.stats.log_packet_by_seqnr(seqnr, 'rx')
                # self.stats.add_pong(seqnr)
            elif instr == 'DUID':
                # sequence number doesn't matter as the DUID is constant
                if len(param) != 3:
                    sys.stderr.write("[E] Parse error: Invalid DUID reply\n")
                    return
                seqnr = int(param[0])
                duid = int(param[1])
                phyaddr = int(param[2])
                reply = {'uid': duid, 'seqnr': seqnr}
                self.proto.log_by_seqnr(seqnr=seqnr, reply=reply)
                # self.stats.log_packet_by_seqnr(seqnr, 'rx')
                # time.sleep(0.2)
                # self.dhcp.offer(duid)
            elif instr == 'SADR':
                if len(param) != 2 or param[1] != 'ACK':
                    sys.stderr.write("[E] Parse error: Invalid SADR reply\n")
                    return
                seqnr = int(param[0])
                reply = {'ack': True}
                self.proto.log_by_seqnr(seqnr=seqnr, reply=reply)
            elif instr == 'CHNL':
                if len(param) != 2 or param[1] != 'ACK':
                    sys.stderr.write("[E] Parse error: Invalid SADR reply\n")
                    return
                seqnr = int(param[0])
                reply = {'ack': True}
                self.proto.log_by_seqnr(seqnr=seqnr, reply=reply)
            elif instr == 'STAT':
                if len(param) != 2:
                    sys.stderr.write("[E] Parse error: Invalid STAT reply\n")
                    return
                seqnr = int(param[0])
                value = int(param[1])
                # self.stats.log_packet_by_seqnr(seqnr, 'rx')
                # self.stats.add_final_stat(seqnr, value)
            elif instr == 'BATS':
                if len(param) != 2:
                    sys.stderr.write("[E] Parse error: Invalid BATS reply\n")
                    return
                seqnr = int(param[0])
                reply = {'ack': True}
                self.proto.log_by_seqnr(seqnr=seqnr, reply=reply)
                # self.stats.log_packet_by_seqnr(seqnr, 'rx')
                # self.stats.add_final_stat(seqnr, value)
            elif instr == 'POLL':
                if len(param) != 5:
                    sys.stderr.write("[E] Parse error: Invalid POLL reply\n")
                    return
                seqnr = int(param[0])
                ordernumber = int(param[1])
                amount = int(param[2])
                phyaddr = int(param[3])
                energy = int(param[4])
                poll = {
                    'ordernumber': ordernumber,
                    'amount': amount,
                    'phyaddr': phyaddr,
                    'energy': energy
                }
                self.preserver.store_by_ordernumber(poll, tmstamp)
            elif instr == 'ENUM':
                if len(param) != 6:
                    sys.stderr.write("[E] Parse error: Invalid POLL reply\n")
                    return
                seqnr = int(param[0])
                itemdescr = int(param[1])
                amount = int(param[2])
                phyaddr = int(param[3])
                ordernumber = int(param[4])
                orderamount = int(param[5])
                reply = {
                    'itemdescr': itemdescr,
                    'amount': amount,
                    'phyaddr': phyaddr,
                    'ordernumber': ordernumber,
                    'orderamount': orderamount
                }
                self.proto.log_by_seqnr(seqnr, reply)
            elif instr == 'DLVR':
                if len(param) != 1:
                    sys.stderr.write("[E] Parse error: Invalid DLVR reply\n")
                    return
                seqnr = int(param[0])
            elif instr == 'ISRT':
                if len(param) != 1:
                    sys.stderr.write("[E] Parse error: Invalid ISRT reply\n")
                    return
                seqnr = int(param[0])
                reply = {'ack': True}
                self.proto.log_by_seqnr(seqnr=seqnr, reply=reply)
            elif instr == 'SETI':
                if len(param) != 1:
                    sys.stderr.write("[E] Parse error: Invalid SETI reply\n")
                    return
                seqnr = int(param[0])
                reply = {'ack': True}
                self.proto.log_by_seqnr(seqnr=seqnr, reply=reply)
            elif instr == 'RSVE':
                if len(param) != 2:
                    sys.stderr.write("[E] Parse error: Invalid STAT reply\n")
                    return
                seqnr = int(param[0])
                ordernumber = int(param[1])
                reply = {'ordernumber': ordernumber}
                self.proto.log_by_seqnr(seqnr=seqnr, reply=reply)
                self.preserver.block_by_ordernumber(ordernumber)
            else:
                pass
                # TODO might also be something else
                # self.stats.log_packet(0, 'rx')
        elif mode == 'M':
            if instr == 'RSTO':
                if len(param) < 3:
                    sys.stderr.write("[E] Parse error: Invalid RSTO message\n")
                    return
                phyaddr = int(param[0])
                uid = int(param[1])
                ordernumber = int(param[2])
                self.preserver.rsto_by_phyaddr(phyaddr, ordernumber)
            elif instr == 'FULE':
                if len(param) != 2:
                    sys.stderr.write("[E] Parse error: Invalid FULE message\n")
                    return
                phyaddr = int(param[0])
                energy = int(param[1])
                self.preserver.update_energy(phyaddr, energy, tmstamp)
            elif instr == 'LOWE':
                if len(param) != 2:
                    sys.stderr.write("[E] Parse error: Invalid FULE message\n")
                    return
                phyaddr = int(param[0])
                energy = int(param[1])
                self.preserver.update_energy(phyaddr, energy, tmstamp)


'''
############################################################
'''


class SerialReader():
    def __init__(self, parser):
        self.recv_buf = ''
        self.parser = parser
        log(20, 'SERIAL_READER', 'Initialized!')

    def __call__(self):
        return self

    def parse_lines(self, lines):
        for line in lines:
            self.parser.parse_line(line)

    def data_received(self, data):
        try:
            str_data = data.decode('UTF-8')
            self.recv_buf += str_data
            lines = self.recv_buf.split("\n\r")

            if len(lines) > 1:
                self.parse_lines(lines[0: -1])
                self.recv_buf = lines[-1]
        except UnicodeDecodeError:
            sys.stderr.write("[E] UART output contains garbage: {data}\n".format(data=data))


'''
############################################################
'''


'''
DHCP duid struct:
    {
        duid: number,
        addr: [0-255],
        state: ['OFFER_SENT', 'COMPLETE"],
        seqnr: number
        ping_cnt: number,
        pong_cnt: number
    }
'''

class DHCP:
    def __init__(self, proto):
        self.proto = proto
        self.by_duid = {}
        self.by_addr = {}
        self.next_addr = 1
        log(20, 'DHCP', 'Initialized!')

    def __call__(self):
        return self

    def discover(self):
        module = gs_config.getint('module')
        pkt = APPacket(module, 0, self.proto.create_duid_request(0))
        pkt.send()

    def offer(self, duid):
        module = gs_config.getint('module')
        if duid not in self.by_duid:
            devinfo = {
                'duid': duid,
                'addr': self.next_addr,
                'state': 'OFFER_SENT',
                'seqnr': self.proto.get_seqnr(),
                'stats': {},
                'ping_cnt': 0,
                'pong_cnt': 0,
            }
            self.by_duid[duid] = devinfo

            print("[I] Offering address {addr} to node {duid}".format(
                addr=self.next_addr,
                duid=duid
            ))

            pkt = APPacket(module, 0, self.proto.create_sadr_request(0, duid, self.next_addr))
            pkt.send()
            # ~ serial_write(proto.create_sadr_request(0, duid, self.next_addr))
            self.next_addr += 1
        elif self.by_duid[duid]['state'] != 'COMPLETE':
            self.by_duid[duid]['seqnr'] = self.proto.get_seqnr()
            pkt = APPacket(module, 0, self.proto.create_sadr_request(0, duid, self.by_duid[duid]['addr']))
            pkt.send()

    def ack(self, seqnr):
        for device in self.by_duid.values():
            if device['seqnr'] == seqnr:
                device['state'] = 'COMPLETE'
                self.by_addr[device['addr']] = device

                print("[I] node {duid} now has address {addr}".format(
                    addr=device['addr'],
                    duid=device['duid']
                ))

                return

        sys.stderr.write("[E] Got DHCP ACK for an offer we didn't send\n")

    def clients(self):
        return sorted(self.by_addr.keys())

    def dump_stats(self):
        print("\n\n --- DHCP stats ---\n")
        print("  DUID  ADDR  STATE")

        for duid in sorted(self.by_duid.keys()):
            print("{duid:6d} {addr:5d}  {state}".format(
                duid=duid,
                addr=self.by_duid[duid]['addr'],
                state=self.by_duid[duid]['state'],
            ))

        print("\n ---            ---\n")


'''
############################################################
'''


class Preserver:
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.phynode_list = self.init()
        self.received_poll_messages = []
        self.lock = threading.Lock()
        self.print_phynodelist()
        log(20, 'PRESERVER', 'Initialized!')
        # self.cleaning_thread = threading.Thread(group=None, target=self.cleaning_loop, name='Cleaning Thread', daemon=True)
        # self.cleaning_thread.start()

    def init(self):
        return [
            {'uid': 2330, 'phyaddr': 10, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': True, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 6202, 'phyaddr': 11, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': True, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 9991, 'phyaddr': 12, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': True, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 6672, 'phyaddr': 13, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': True, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 10502, 'phyaddr': 14, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': True, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 2574, 'phyaddr': 50, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 9995, 'phyaddr': 51, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 7946, 'phyaddr': 52, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 6925, 'phyaddr': 53, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 3095, 'phyaddr': 54, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 7437, 'phyaddr': 55, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 1806, 'phyaddr': 56, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 3852, 'phyaddr': 57, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
            {'uid': 7483, 'phyaddr': 58, 'rsto': False, 'ordernumber': 0, 'blocked': False, 'empty': False, 'energy': 0, 'energy_timestamp': '', 'poll_list': []},
        ]

    def print_phynodelist(self):
        print("\n --- PHYNODES ---\n")
        print("DUID      PHYADDR    RSTO       ORDERNUMBER      BLOCKED")
        for phynode in self.phynode_list:
            print('uid:{:5d} phyaddr:{:2d} rsto:{:5s} ordernumber:{:4d} blocked:{}'.format(
                phynode['uid'],
                phynode['phyaddr'],
                str(phynode['rsto']),
                phynode['ordernumber'],
                str(phynode['blocked'])
            ))
        print(" ---          ---\n")
        self.publish_information()

    def publish_information(self):
        self.mqtt_client.publish(
            topic='/gateway/phynode/information',
            payload=json.dumps(self.phynode_list),
            qos=0,
            retain=False
        )

    def update_energy(self, phyaddr, energy, timestamp):
        for phynode in self.phynode_list:
            if phynode['phyaddr'] == phyaddr:
                phynode['energy'] = energy
                phynode['energy_timestamp'] = timestamp
                # print('Update energy: ' + str(phyaddr) + str(energy) + ', ' + timestamp)
        log(
            20,
            'ORDER_PRESERVER',
            'Updated energy on phyaddr {:d}\n'.format(phyaddr)
        )
        self.publish_information()

    def rsve_by_phyaddr(self, phyaddr, ordernumber):
        for phynode in self.phynode_list:
            if phynode['phyaddr'] == phyaddr:
                phynode['ordernumber'] = ordernumber
                self.publish_information()
                return True
        return False

    def block_by_ordernumber(self, ordernumber):
        for phynode in self.phynode_list:
            if phynode['ordernumber'] == ordernumber:
                phynode['blocked'] = True
                self.publish_information()
                return

    def is_blocked(self, phyaddr):
        for phynode in self.phynode_list:
            if phynode['phyaddr'] == phyaddr and phynode['blocked'] == True:
                return True
            else:
                return False

    def rsto_by_phyaddr(self, phyaddr, ordernumber):
        phynode = None
        for phynode in self.phynode_list:
            if phynode['phyaddr'] == phyaddr:
                phynode = phynode
        if phynode is not None and ordernumber != 0:
            if not phynode['empty']:
                phynode['blocked'] = False
                phynode['ordernumber'] = 0
                phynode['rsto'] = True
            else:
                phynode['blocked'] = True
                phynode['ordernumber'] = 0
                phynode['rsto'] = True
        if phynode is not None and ordernumber == 0 and phynode['blocked']:
            phynode['blocked'] = False
            phynode['rsto'] = True
        self.publish_information()

    def get_rsto_status(self, phyaddr: int) -> bool:
        for phynode in self.phynode_list:
            if phynode['phyaddr'] == phyaddr:
                result = phynode['rsto']
                if result:
                    phynode['rsto'] = False
                    log(
                        20,
                        'ORDER_PRESERVER',
                        'Un-RSTO phyaddr {:d}: {}\n'.format(phynode['phyaddr'], phynode['rsto'])
                    )
                    self.publish_information()
                return result

    def reset(self):
        self.phynode_list = self.init()
        self.publish_information()

    # def store_poll_by_phyaddr(self, poll):
    #     for phynode in self.phynode_list:
    #         if poll['phyaddr'] == phynode['phyaddr']:
    #             phynode['poll_list'].append(poll)

    # def get_poll_by_ordernumber(self, ordernumber):
    #     result = []
    #     for phynode in self.phynode_list:
    #         for index, poll in enumerate(phynode['poll_list']):
    #             if poll['ordernumber'] == ordernumber:
    #                 result.append(poll)
    #                 phynode['poll_list'].remove(index)
    #     return result

    def get_by_ordernumber(self, ordernumber):
        result = []
        for index, item in enumerate(self.received_poll_messages):
            if int(item['ordernumber']) == ordernumber:
                result.append(self.received_poll_messages.pop(index))
        return result

    def store_by_ordernumber(self, poll, tmpstamp):
        self.received_poll_messages.append(poll)
        self.update_energy(phyaddr=poll['phyaddr'], energy=poll['energy'], timestamp=tmpstamp)
        log(
            20,
            'ORDER_PRESERVER',
            'Append...\n{}, length: {:d}\n'.format(str(poll), len(self.received_poll_messages))
        )


'''
############################################################
'''


class GatewayHandler:
    def __init__(self, proto, stats, dhcp, parser, mqttc):
        self.__proto = proto
        self.__stats = stats
        self.__dhcp = dhcp
        self.__parser = parser
        self.__mqttc = mqttc
        self.__stop = True
        self.__rx_loop = None
        log(20, 'GATEWAY_HANDLER', 'Initialized!')

    def run(self):
        log(10, 'GATEWAY_HANDLER', 'Starting RX_LOOP')

        rx_fifo_path = Path(RX_FIFO)
        # tx_fifo_path = Path(TX_FIFO)
        fifos_ok = True

        # if not tx_fifo_path.exists():
        #     fifos_ok = False
        #     log(40, 'GATEWAY_HANDLER', 'File {file}  does not exist!'.format(file=TX_FIFO))

        if not rx_fifo_path.exists():
            fifos_ok = False
            log(40, 'GATEWAY_HANDLER', 'File {file}  does not exist!'.format(file=RX_FIFO))

        if not fifos_ok:
            raise IOError('ERROR >>>>>> Did you start the SFBGateway.app?')
        else:
            log(10, 'GATEWAY_HANDLER', 'FiFo´s initialized')

        # signal.signal(signal.SIGINT, self.signal_handler)

        self.__stop = False
        self.__rx_loop = threading.Thread(name='RX_LOOP', target=self._rx_loop, daemon=True)
        self.__rx_loop.start()

        # for i in range(0, 2):
        #     self.dhcp.discover()
        #     time.sleep(0.6)
        # ~ dhcp.dump_stats()

    def _rx_loop(self):
        log(10, self.__rx_loop.getName(), 'Started!')
        while not self.__stop:
            try:
                fifo = open(RX_FIFO, 'rb')
                data = fifo.read()
                fifo.close()
                packets = data.split(b'\r\n')
            except IOError as err:
                log(40, self.__rx_loop.getName(), 'RX_FIFO is closed!')
                self.__stop = True
            except Exception as err:
                log(40, self.__rx_loop.getName(), str(err))
                break

            for dat in packets:
                if len(dat) is 0:
                    break
                payload_len = len(dat) - 5
                module, status1, status2, length, addr, payload = struct.unpack('BBBBB%ds' % (payload_len), dat)
                cc = CCPacket(address=addr, payload=bytearray(payload))
                cc.status1 = status1
                cc.status2 = status2
                ap_pkt = APPacket(module, cc)
                self._handle_packet(ap_pkt)
                time.sleep(.05)             #  Timeout for handle packet

        else:
            log(10, self.__rx_loop.getName(), 'Stopped!')

    '''
    Example for packet handler function.
    Can only handle PING messages right now:
    A PING consists of the string "PING" + 1 Byte nodeId (binary)
    Respond by sending a pong after 100ms to the node that send the PING
    '''
    def _handle_packet(self, ap_pkt):
        if not isinstance(ap_pkt, APPacket):
            raise TypeError("ap_pkt must be %s but is %s" % (APPacket, type(ap_pkt)))

        pl = ap_pkt.pkt.payload

        log(
            10,
            'HANDLE_PACKET',
            'Received packet on module {:d} at {} {}'.format(ap_pkt.module, time.strftime("%d.%m.%Y"), time.strftime("%H:%M:%S"))
        )
#        log(10, 'HANDLE_PACKET', '\tRSSI:\t{:d}'.format(ap_pkt.pkt.get_rssi()))
#        log(10, 'HANDLE_PACKET', '\tlength:\t{:d}'.format(ap_pkt.pkt.length))

        try:
            pl = pl.decode()
#            log(10, 'HANDLE_PACKET', '\tpayload:\t{}'.format(pl))
        except:
            log(40, 'HANDLE_PACKET', 'Cound`t decode the payload [E]')

        self.__mqttc.publish(
                topic='/gateway/phynode/replys',
                payload=json.dumps(pl),
                qos=0,
                retain=False
            )
        self.__parser.parse_line(pl)

    def signal_handler(self, signum, frame):
        log(10, 'GATEWAY_HANDLER', 'Stopped...')
        self.__stop = True
        # sys.exit(0)

    def _stop(self):
        self.__stop = True


'''
############################################################
'''
