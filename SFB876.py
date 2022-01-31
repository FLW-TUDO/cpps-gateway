#!/usr/bin/env python3

import configparser
import json
import os
import sys
import threading
import time
# from Tools.scripts import google
# from firebase_admin import credentials
# from firebase_admin import firestore
from enum import Enum

import paho.mqtt.client as mqtt
# import firebase_admin
import requests
from pymongo import MongoClient

from models import Order, log

# Initialize
oa = None
ws = None
klt = None

'''
############################################################
'''

client = MongoClient('mongodb://192.168.2.188:27017/')
db = client.phynetlab
collection = db.orders

'''
############################################################
In the first step we use a firebase database. 
After traffic limitation we switch to our own MangoDB database.


# Firebase API settings
cred = credentials.Certificate(
    'phynetlab-webshop-firebase-adminsdk-zr1tr-166d7450db.json'
    )  # Use a service account

# Initialize firebase app with authentication
firebase_admin.initialize_app(cred)  

# Create a database client
db = firestore.client()  

# Reference to the collection
orders_ref = db.collection('orders')  


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
oa_config = config_parser['OrderAdministration']

'''
############################################################
'''

# MQTT settings
mqtt_host = 'gopher.phynetlab.com'
mqtt_port = oa_config.getint('mqtt_port')
mqtt_topic = oa_config.get('mqtt_topic')


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    log(
        20,
        'MQTT_CLIENT',
        "Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    log(
        20,
        'MQTT_CLIENT',
        msg.topic + " " + str(msg.payload))


# The callback function for ack if robot is arrived at home position
def on_robot_ack(client, userdata, message):
    payload = message.payload
    ack_data = json.loads(payload.decode())
    # print('\n{}'.format(ack_data))
    print('\n{}'.format(json.dumps(ack_data, indent=2)))

    if 'task_ack' in ack_data and 'action' in ack_data and 'cart_id' in ack_data:
        if ack_data['task_ack'] == 'arrived' and ack_data['action'] == 'return':
            try:
                k = ack_data['cart_id']
                phyaddr = int(Klt[k].value)
            except KeyError:
                phyaddr = None

            if phyaddr is not None:
                oa.unblock_phynode(phyaddr)
                return
            else:
                log(
                    40,
                    'ROBOT_ACK',
                    'Cant parse the ack!'
                )
        if ack_data['task_ack'] == 'arrived' and ack_data['action'] == 'deliver':
            try:
                k = ack_data['cart_id']
                phyaddr = int(Klt[k].value)
            except KeyError:
                phyaddr = None

            if phyaddr is not None:
                oa.set_as_delivered(phyaddr)
                log(
                    40,
                    'ROBOT_ACK',
                    'Delivered phynode {:d}'.format(phyaddr)
                )
                return
            else:
                log(
                    40,
                    'ROBOT_ACK',
                    'Cant parse the ack!'
                )


def connect_to_mqtt_broker():
    rc = mqtt_client.connect(mqtt_host, port=mqtt_port, keepalive=60, bind_address="")
    if rc == 0:
        log(
            20,
            'MQTT_CLIENT',
            'Connect to broker: {} on port: {:d} and topic: {}'.format(mqtt_host, mqtt_port, mqtt_topic)
        )
        mqtt_client.subscribe('/fms/#')
        mqtt_client.loop_start()
        time.sleep(.2)
    else:
        log(
            40,
            'MQTT_CLIENT',
            'Connection failed with status code: {:d}'.format(rc)
        )


mqtt_client = mqtt.Client('OrderAdministrator')
mqtt_client.on_connect = on_connect
# mqtt_client.on_message = on_message
mqtt_client.message_callback_add('/fms/ack', on_robot_ack)

'''
############################################################
'''

# Base URL for gateway server
base_url = oa_config.get('gateway_base_url')
log(20, 'BASE_URL', 'Gateway: {}'.format(base_url))
# Base URL for order server
base_url_order_server = oa_config.get('orderserver_base_url')
log(20, 'BASE_URL', 'Order Server: {}'.format(base_url_order_server))

'''
############################################################
'''


class Klt(Enum):
    klt01 = 10
    klt02 = 11
    klt03 = 12
    klt04 = 13
    klt05 = 14
    klt06 = 50
    klt07 = 51
    klt08 = 52
    klt09 = 53
    klt10 = 54
    klt11 = 55
    klt12 = 56
    klt13 = 57
    klt14 = 58
    klt15 = 59


'''
############################################################
'''


class Workstations:
    def __init__(self, amount, home_station):
        self.workstations = []
        for i in range(1, amount + 1):
            home = False
            if i == home_station:
                home = True
            self.workstations.append({
                'id': 'WS_{:d}'.format(i),
                'name': 'Working Station {}'.format(i),
                'usage': False,
                'ordernumber': None,
                'home_station': home
            })
        log(20, 'WORKSTATIONS', 'Initialized {:d} with home station {:d}'.format(amount, home_station))

    def is_free(self):
        for workstation in self.workstations:
            if not workstation['home_station'] and not workstation['usage']:
                return True

    def set_workstation_by_ordernumber(self, ordernumber):
        for workstation in self.workstations:
            if not workstation['home_station'] and not workstation['usage']:
                workstation['usage'] = True
                workstation['ordernumber'] = ordernumber
                log(
                    10,
                    'WORKSTATION',
                    '{} blocked by ordernumber {:d}'.format(workstation['id'], ordernumber)
                )
                return workstation['id']
        return None

    def get_workstation_by_ordernumber(self, ordernumber):
        for workstation in self.workstations:
            if workstation['ordernumber'] == ordernumber:
                return workstation['id']
        return None

    def get_homestation(self):
        for workstation in self.workstations:
            if workstation['home_station']:
                return workstation['id']

    def reset_workstation_by_ordernumber(self, ordernumber):
        for workstation in self.workstations:
            if not workstation['home_station'] and workstation['ordernumber'] == ordernumber:
                workstation['usage'] = False
                workstation['ordernumber'] = None
                return True
        return False


'''
############################################################
'''


class OrderAdministration(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stop_request = threading.Event()
        self.threads = []
        self.blocked_articles = []
        self.delivered_klts = []
        self.thread_lock = threading.Lock()
        log(20, 'ORDER_ADMINISTRATION', 'Initialized')

    def run(self):
        log(20, 'ORDER_ADMINISTRATION', 'Waiting for new incoming orders...\n')

        while not self.stop_request.isSet():
            new_order = self._check_for_new_order()

            if new_order is not None:
                if ws.is_free():
                    # Change the web order status
                    self.update_states(new_order.oid, 'state', 'registered')
                    # Open a new thread
                    new_process = OrderProcessing(new_order)
                    new_process.start()
                    # Append thread to the list of executed threads
                    self.threads.append(new_process)
            time.sleep(1)
        else:
            log(20, 'ORDER_ADMINISTRATION', 'Thread has been stopped')
            sys.exit()

    def activate(self):
        self.stop_request.clear()

    def deactivate(self):
        self.stop_request.set()

    @staticmethod
    def update_states(id_order, topic, status):
        order = {'id': id_order}
        new_value = {"$set": {topic: status}}
        collection.update_one(order, new_value)

    @staticmethod
    def publish_mqtt_msg(message):
        mqtt_client.publish(
            topic=mqtt_topic,
            payload=json.dumps(message),
            qos=0,
            retain=False
        )
        print('\n')
        log(
            10,
            'MQTT_CLIENT',
            'Published...'
        )
        print(json.dumps(message, indent=2))
        print('\n')

    def lock(self):
        self.thread_lock.acquire()

    def unlock(self):
        self.thread_lock.release()

    def block_phynode(self, phyaddr, ordernumber, amount):
        url = '{}gateway/RSVE'.format(base_url)
        request_body = {
            'phyaddr': phyaddr,
            'ordernumber': ordernumber,
            'amount': amount
        }
        try:
            response = requests.post(url, data=json.dumps(request_body))
        except requests.exceptions.RequestException as err:
            log(40, 'GUARD', str(err))
            return False
        if response.status_code == 200:
            self.blocked_articles.append(phyaddr)
            log(10, 'GUARD', 'Phynode {:d} blocked...'.format(phyaddr))
            return True
        else:
            return False

    def unblock_phynode(self, phyaddr):
        if phyaddr in self.blocked_articles:
            try:
                self.blocked_articles.remove(phyaddr)
                log(10, 'GUARD', 'Phynode {:d} unblocked!'.format(phyaddr))
                return True
            except ValueError:
                return False

    def is_phynode_blocked(self, phyaddr):
        return phyaddr in self.blocked_articles

    def set_as_delivered(self, phyaddr):
        for klt in self.delivered_klts:
            if klt == phyaddr:
                return
        self.delivered_klts.append(phyaddr)

    def unset_as_delivered(self, phyaddr):
        for klt in self.delivered_klts:
            if klt == phyaddr:
                self.delivered_klts.remove(phyaddr)

    def is_delivered(self, phyaddr):
        for klt in self.delivered_klts:
            if klt == phyaddr:
                return True
        return False

    # @staticmethod
    # def _check_for_new_order():
    #     result = None
    #     try:
    #         orders = orders_ref.get()
    #         for order in orders:
    #             new_order = Order.from_dict(int(order.id), order.to_dict())
    #             if new_order.state == 'open':
    #                 result = new_order
    #     except:     # google.cloud.exceptions.NotFound:
    #         return result
    #     return result

    @staticmethod
    def _check_for_new_order():
        result = None
        try:
            for order in collection.find():
                if order['state'] == 'open' or order['state'] == 'restart':
                    result = Order.from_dict(order)
                    return result
        except Exception as err:
            print(type(err))
            return result


'''
############################################################
'''

'''
This process will start as a thread by calling the run() method 
and loop throw some stages, how are needed for manage the input order.
One stage starts, if the stage before is ready.
Step 1:
The process iterates over the articles from the order 
and creates new intern orders with new order numbers for each article inside.
This orders are stored in the "intern_order_list" with new intern ordernumber.

Step 2:
    stage           description
    ********************************************************************
    1               This stage repeats if the validation for stage 1 is false.
                    The process iterate over the "intern_order_list" and check if all articles have
                    an assigned phynode address. Furthermore one phynode will selected as an empty box
                    for delivering to the consolidation station.
    2               Same like stage 1, but looks for empty cart.
    3               Stage number 2 locks a critical stage for set the workstation and articles in use.
                    If a workstation is not free or a one of the needed articles are blocked, the stage
                    will wait till both conditions are met. After that it send a mqtt-message to the fms-system
                    of the robots, to give movement commands.
    4               The third stage waits for the acknowledgments by button pressed on the phynodes.
                    Then it sends a return message to the fms-system
    5               This stage checks for arrived articles to the home position and unblock them, if its true  
'''


class OrderProcessing(threading.Thread):
    def __init__(self, order):
        super().__init__()
        self.order = order
        self.order_id = order.oid
        self.intern_order_list = []
        self.workstation_id = None
        self.failed = False
        self.finished = False
        log(
            20,
            'ORDER_PROCESS {:d}'.format(self.order_id),
            'New Order_Processing_Thread started'
        )

    def run(self):
        # Step 1
        self._create_intern_order_list()

        # Step 2
        if not self.failed:
            self._stage_1()
        if not self.failed:
            self._stage_2()
        if not self.failed:
            self._stage_3()
        if not self.failed:
            self._stage_4()
        if not self.failed:
            self._stage_5()
        if not self.failed:
            self._stage_6()

        if self.finished:
            oa.update_states(self.order_id, 'state', 'finished')

        if self.failed:
            ws.reset_workstation_by_ordernumber(self.order_id)
            for order in self.intern_order_list:
                oa.unblock_phynode(order['phyaddr'])

        log(
            10,
            'ORDER_PROCESS {:d}'.format(self.order_id),
            'Order process terminated\n')

    def _stage_1(self):
        log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Start with stage 1...')
        oa.update_states(self.order_id, 'stage1', 'Waiting for phynode(s) reply..')

        url = '{}gateway/POLL'.format(base_url)
        max_attempts = oa_config.getint('failed_attempts_stage1') * len(self.intern_order_list)
        attempts = 1
        while not self._validate_stage_1() and attempts <= max_attempts:
            successful = True
            failed_list = []
            for order in self.intern_order_list:
                if order['phyaddr'] is None and order['itemdescr'] is not 0:
                    request_body = {
                        'ordernumber': order['ordernumber'],
                        'itemdescr': order['itemdescr']
                    }
                    response = self._send_http_request('POST', url, request_body)

                    if response is not None:
                        try:
                            payload = response.json()
                        except ValueError as err:
                            print('\n')
                            log(40, 'ORDER_PROCESS {:d}'.format(self.order_id), str(err))
                            break

                        if 'FAILURE' not in payload:
                            phynode_with_lowest_energy = None

                            # Iterate over the list of possible candidates to find the phynode
                            # with lowest energy.
                            for p_item in payload:
                                if 'ordernumber' in p_item and p_item['ordernumber'] == order['ordernumber']:
                                    if phynode_with_lowest_energy is None:
                                        phynode_with_lowest_energy = p_item
                                    else:
                                        print('Look for phynode with lowest energy')
                                        if p_item['energy'] < phynode_with_lowest_energy['energy']:
                                            print('Change phynode with lowest energy!')
                                            phynode_with_lowest_energy = p_item

                            order['phyaddr'] = phynode_with_lowest_energy['phyaddr']
                            order['energy'] = phynode_with_lowest_energy['energy']
                        else:
                            successful = False
                            failed_list.append(order['itemdecr'])
                    else:
                        successful = False
                        failed_list.append(order['itemdescr'])
                time.sleep(.5)
            if not successful:
                oa.update_states(self.order_id, 'stage1',
                                 'Stage 1, phynode(s) {} not reply! Abort after. {:d}'.format(str(failed_list),
                                                                                              max_attempts - attempts))
                sys.stdout.write('\r[{}]: {}'.format(
                    '{:<20}'.format(
                        'ORDER_PROCESS {:d}]'.format(
                            self.order_id)),
                    'Stage 1, phynode(s) {} not reply! Abort after. {:4d}'.format(failed_list,
                                                                                  max_attempts - attempts)))
                sys.stdout.flush()
            attempts += 1
        else:
            if attempts > max_attempts:
                oa.update_states(self.order_id, 'stage1', 'timeout! At least one phynode did not respond')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id),
                    'Stage 1 failed after {:d} attempts!'.format(max_attempts))
                oa.update_states(self.order_id, 'state', 'failed')
                self.failed = True
            else:
                oa.update_states(self.order_id, 'stage1', 'complete')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 1 complete!\n')

    # If all articles have a phynode address assigned, the method returns "True" otherwise "False"
    def _validate_stage_1(self):
        for order in self.intern_order_list:
            if order['itemdescr'] is not 0:
                if order['phyaddr'] is None:
                    return False
        else:
            return True

    def _stage_2(self):
        log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Start with stage 2...')
        oa.update_states(self.order_id, 'stage2', 'Waiting for empty cart reply..')

        successful = False
        empty_cart = self.intern_order_list[0]
        url = '{}gateway/POLL'.format(base_url)
        max_attempts = oa_config.getint('failed_attempts_stage2') * len(self.intern_order_list)
        attempts = 1
        while not self._validate_stage_2() and attempts <= max_attempts:
            request_body = {
                'ordernumber': empty_cart['ordernumber'],
                'itemdescr': empty_cart['itemdescr']
            }
            response = self._send_http_request('POST', url, request_body)
            if response is not None:
                try:
                    payload = response.json()
                except ValueError as err:
                    print('\n')
                    log(40, 'ORDER_PROCESS {:d}'.format(
                        self.order_id), str(err))
                    break

                if 'FAILURE' not in payload:
                    phynode_with_lowest_energy = None

                    # Iterate over the list of possible candidates to find the phynode
                    # with lowest energy.
                    for p_item in payload:
                        if 'ordernumber' in p_item and \
                                p_item['ordernumber'] == self.intern_order_list[0]['ordernumber']:
                            if phynode_with_lowest_energy is None:
                                phynode_with_lowest_energy = p_item
                            elif phynode_with_lowest_energy['energy'] > p_item['energy']:
                                phynode_with_lowest_energy = p_item

                    empty_cart['phyaddr'] = phynode_with_lowest_energy['phyaddr']
                    empty_cart['energy'] = phynode_with_lowest_energy['energy']
                    successful = True
            if not successful:
                oa.update_states(self.order_id, 'stage2',
                                 'Empty cart not reply! Abort after. {:d}'.format(max_attempts - attempts))
                sys.stdout.write('\r[{}]: {}'.format('{:<20}'.format('ORDER_PROCESS {:d}]'.format(self.order_id)),
                                                     'Stage 2, abort after: {:4d}'.format(max_attempts - attempts)))
                sys.stdout.flush()
                time.sleep(.5)
            attempts += 1
        else:
            if attempts > max_attempts:
                oa.update_states(self.order_id, 'stage2', 'timeout! Empty phynode did not respond')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id),
                    'Stage 2 failed after {:d} attempts!'.format(max_attempts))
                oa.update_states(self.order_id, 'state', 'failed')
                self.failed = True
            else:
                oa.update_states(self.order_id, 'stage2', 'complete')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 2 complete!\n')

    # If the empty klt have a phynode address assigned, the method returns "True" otherwise "False"
    def _validate_stage_2(self):
        if self.intern_order_list[0]['phyaddr'] is None:
            return False
        else:
            return True

    def _stage_3(self):
        log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Start with stage 3...')

        max_time = oa_config.getint('max_time_stage3') * len(self.intern_order_list)
        sleep = max_time
        while not self._validate_stage_3() and sleep > 0:
            oa.lock()
            if ws.is_free():
                self.workstation_id = ws.set_workstation_by_ordernumber(self.order_id)

                block_failure = ''
                for order in self.intern_order_list:
                    if not oa.is_phynode_blocked(order['phyaddr']):
                        result = oa.block_phynode(
                            phyaddr=order['phyaddr'],
                            ordernumber=order['ordernumber'],
                            amount=order['amount']
                        )
                        if not result:
                            block_failure = block_failure + str(order['phyaddr']) + ' '
                        time.sleep(0.5)  # Timeout for sending RF request

                if self._validate_stage_3():
                    carts = []
                    dest = self.workstation_id
                    # index = 1
                    for index, order in enumerate(self.intern_order_list):
                        # Define the destination and status for mqtt message
                        if order['itemdescr'] == 0:
                            status = 'empty'
                        else:
                            status = order['itemdescr']

                        try:
                            klt = Klt(order['phyaddr']).name
                        except KeyError:
                            print('\n')
                            log(
                                40,
                                'KLT',
                                '{:d} is not a valid Klt!'.format(order['phyaddr'])
                            )
                            break

                        carts.append(
                            {
                                'cart{:d}'.format(index): {
                                    'id': klt,
                                    'status': status
                                }
                            }
                        )
                        # index += 1

                    # Send the mqtt message to the broker
                    message = {
                        'order_num': self.order_id,
                        'action': {
                            'type': 'bring',
                            'carts': carts
                        },
                        'workstation': dest
                    }
                    oa.publish_mqtt_msg(message)
                    oa.unlock()
                else:
                    ws.reset_workstation_by_ordernumber(self.order_id)
                    oa.update_states(self.order_id, 'stage3',
                                     'Could not block phynodes {}. Countdown by: {:d}'.format(block_failure, sleep))
                    sys.stdout.write('\r[{}]: {}'.format('{:<20}'.format('ORDER_PROCESS {:d}]'.format(self.order_id)),
                                                         'Stage 3, countdown by: {:4d}'.format(sleep)))
                    sys.stdout.flush()
            if not self._validate_stage_3():
                oa.unlock()
                time.sleep(1)
                sleep -= 1
        else:
            if sleep == 0:
                oa.update_states(self.order_id, 'stage3',
                                 'timeout! Workstation or phynodes could not blocked in period of time')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 3 abort after timeout!\n')
                oa.update_states(self.order_id, 'state', 'failed')
                self.failed = True
            else:
                oa.update_states(self.order_id, 'stage3', 'complete')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 3 complete!\n')

    def _validate_stage_3(self):
        all_phynodes_blocked = True
        for order in self.intern_order_list:
            if not oa.is_phynode_blocked(order['phyaddr']):
                all_phynodes_blocked = False
        if self.workstation_id is None or not all_phynodes_blocked:
            return False
        else:
            return True

    def _stage_4(self):
        log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Start with stage 4...')

        url = '{}gateway/RSTO'.format(base_url)
        max_time = oa_config.getint('max_time_stage4') * len(self.intern_order_list)
        klt = None
        sleep = max_time
        while not self._validate_stage_4() and sleep > 0:
            for index, order in enumerate(self.intern_order_list):
                if not order['ack']:
                    request_body = {'phyaddr': order['phyaddr']}
                    response = self._send_http_request('GET', url, request_body)
                    if response is not None and response.status_code == 200:
                        try:
                            payload = response.json()
                            if 'rsto' in payload and payload['rsto']:
                                order['ack'] = True

                                # Define the destination and status for mqtt message
                                if order['itemdescr'] == 0:
                                    dest = str(ws.get_homestation())
                                    status = 'empty'
                                    typ = 'deliver'
                                else:
                                    dest = ''
                                    status = order['itemdescr']
                                    typ = 'return'

                                try:
                                    klt = Klt(order['phyaddr']).name
                                except KeyError:
                                    print('\n')
                                    log(
                                        40,
                                        'KLT',
                                        '{:d} is not a valid Klt!'.format(order['phyaddr'])
                                    )

                                message = {
                                    'order_num': self.order_id,
                                    'action': {
                                        'type': typ,
                                        'carts': [
                                            {
                                                'cart0': {
                                                    'id': klt,
                                                    'status': status
                                                }
                                            }
                                        ]
                                    },
                                    'workstation': dest
                                }
                                oa.publish_mqtt_msg(message)
                        except ValueError as err:
                            print('\n')
                            log(40, 'ORDER_PROCESS {:d}'.format(self.order_id), str(err))
            if not self._validate_stage_4():
                oa.update_states(self.order_id, 'stage4', 'Countdown by: {:d}'.format(sleep))
                sys.stdout.write('\r[{}]: {}'.format('{:<20}'.format('ORDER_PROCESS {:d}]'.format(self.order_id)),
                                                     'Stage 4, countdown by: {:4d}'.format(sleep)))
                sys.stdout.flush()
                time.sleep(1)
                sleep -= 1
        else:
            if sleep == 0:
                oa.update_states(self.order_id, 'stage4', 'timeout! Do not get ack from phynodes in period of time')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 4 abort after timeout!\n')
                oa.update_states(self.order_id, 'state', 'failed')
                self.failed = True
            else:
                oa.update_states(self.order_id, 'stage4', 'complete')
                print('\n')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 4 complete!\n')
            ws.reset_workstation_by_ordernumber(self.order_id)
            self.workstation_id = None

    def _validate_stage_4(self):
        for order in self.intern_order_list:
            if not order['ack']:
                return False
        return True

    def _stage_5(self):
        log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Start with stage 5...')

        url = '{}gateway/RSTO'.format(base_url)
        deliver_klt = self.intern_order_list[0]
        max_time = oa_config.getint('max_time_stage5') * len(self.intern_order_list)
        sleep = max_time
        failed_first_step = False
        while not deliver_klt['deliver'] and sleep > 0:
            if oa.is_delivered(deliver_klt['phyaddr']):
                oa.unset_as_delivered(deliver_klt['phyaddr'])
                break
            oa.update_states(self.order_id, 'stage5', 'Wait for delivering. Countdown by: {:d}'.format(sleep))
            sys.stdout.write('\r[{}]: {}'.format('{:<20}'.format('ORDER_PROCESS {:d}]'.format(self.order_id)),
                                                 'Stage 5 step 1, countdown by: {:4d}'.format(sleep)))
            sys.stdout.flush()
            time.sleep(1)
            sleep -= 1
        else:
            if not oa.is_delivered(deliver_klt['phyaddr']):
                failed_first_step = True
            else:
                sleep = max_time
        while not deliver_klt['ack2'] and sleep > 0 and not failed_first_step:
            request_body = {'phyaddr': deliver_klt['phyaddr']}
            response = self._send_http_request('GET', url, request_body)
            if response is not None and response.status_code == 200:
                try:
                    payload = response.json()
                    if 'rsto' in payload and payload['rsto']:
                        deliver_klt['ack2'] = True

                        try:
                            klt = Klt(deliver_klt['phyaddr']).name
                        except KeyError:
                            print('\n')
                            log(
                                40,
                                'KLT',
                                '{:d} is not a valid Klt!'.format(deliver_klt['phyaddr'])
                            )
                            continue

                        message = {
                            'order_num': self.order_id,
                            'action': {
                                'type': 'return',
                                'carts': [
                                    {
                                        'cart0': {
                                            'id': klt,
                                            'status': deliver_klt['itemdescr']
                                        }
                                    }
                                ]
                            },
                            'workstation': ''
                        }
                        oa.publish_mqtt_msg(message)
                except ValueError as err:
                    print('\n')
                    log(40, 'ORDER_PROCESS {:d}'.format(self.order_id), str(err))
            else:
                oa.update_states(self.order_id, 'stage5', 'Wait for ack2. Countdown by: {:d}'.format(sleep))
                sys.stdout.write('\r[{}]: {}'.format('{:<20}'.format('ORDER_PROCESS {:d}]'.format(self.order_id)),
                                                     'Stage 5 step 2, countdown by: {:4d}'.format(sleep)))
                sys.stdout.flush()
                time.sleep(1)
                sleep -= 1
        if sleep == 0 or failed_first_step:
            oa.update_states(self.order_id, 'stage5', 'timeout! Cant complete delivering or return in period of time')
            log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 5 abort after timeout!\n')
            oa.update_states(self.order_id, 'state', 'failed')
            self.failed = True
        else:
            oa.update_states(self.order_id, 'stage5', 'complete')
            log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 5 complete!\n')

    def _stage_6(self):
        log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Start with stage 6...')

        max_time = oa_config.getint('max_time_stage6') * len(self.intern_order_list)
        sleep = max_time
        while not self._validate_stage_6 and sleep > 0:
            for order in self.intern_order_list:
                if not order['return']:
                    if not oa.is_phynode_blocked(order['phyaddr']):
                        order['return'] = True
                        log(10, 'ORDER_PROCESS {:d}'.format(self.order_id),
                            'Phynode {:d} arrived at home position!'.format(order['phyaddr']))
            if not self._validate_stage_6:
                oa.update_states(self.order_id, 'stage6', 'Countdown by: {:d}'.format(sleep))
                sys.stdout.write('\r[{}]: {}'.format('{:<20}'.format('ORDER_PROCESS {:d}]'.format(self.order_id)),
                                                     'Stage 6, countdown by: {:4d}'.format(sleep)))
                sys.stdout.flush()
                time.sleep(1)
                sleep -= 1
        else:
            if sleep == 0:
                oa.update_states(self.order_id, 'stage6', 'timeout! Robots do not ack the arriving in period of time')
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 6 abort after timeout!\n')
                oa.update_states(self.order_id, 'state', 'failed')
                self.failed = True
            else:
                oa.update_states(self.order_id, 'stage6', 'complete')
                self.finished = True
                log(10, 'ORDER_PROCESS {:d}'.format(self.order_id), 'Stage 6 complete!\n')

    def _validate_stage_6(self):
        for order in self.intern_order_list:
            if not order['return']:
                return False
        return True

    def _create_intern_order_list(self):
        self.intern_order_list.append(
            {
                'ordernumber': (int(self.order_id) * 10),
                'itemdescr': 0,
                'amount': 0,
                'phyaddr': None,
                'energy': None,
                'ack': False,
                'ack2': False,
                'return': False,
                'deliver': False
            }
        )
        index = 1
        for article in self.order.articles:
            new_ordernumber = (int(self.order_id) * 10) + index
            self.intern_order_list.append(
                {
                    'ordernumber': new_ordernumber,
                    'itemdescr': article['article']['number'],
                    'amount': article['amount'],
                    'phyaddr': None,
                    'energy': None,
                    'ack': False,
                    'return': False,
                    'deliver': False
                }
            )
            index += 1

    def _send_http_request(self, method, url, request_body):
        try:
            # log(
            #     10,
            #     'ORDER_PROCESS {:d}'.format(self.order_id),
            #     'Sending request {} to {}'.format(str(request_body), url)
            # )
            data = json.dumps(request_body)
            if method == 'GET':
                response = requests.get(url, data=data)
            elif method == 'POST':
                response = requests.post(url, data=data)
            else:
                return None
        except requests.exceptions.RequestException as err:
            log(40, 'ORDER_PROCESS {:d}'.format(self.order_id), str(err))
            return None

        if response.status_code == 200:
            return response
        elif response.status_code == 405:
            log(40, 'HTTP', 'Bad method request. Status code: {}'.format(response.status_code))
            return None


'''
############################################################
'''


def main():
    log(20, 'ORDER', 'MAIN Started!')
    oa.run()
    while True:
        time.sleep(1)


if __name__ == '__main__':
    oa = OrderAdministration()

    # Parse options
    debug = oa_config.getboolean('debug')
    active = oa_config.getboolean('active')
    number_of_workstations = oa_config.getint('number_of_workstations')
    home_station = oa_config.getint('home_station')

    # Set up
    if number_of_workstations is None or home_station is None:
        log(30, 'ORDER_ADMINISTRATION', 'Can`t parse the workstation options. Please check the config file')
    else:
        ws = Workstations(number_of_workstations, home_station)

    connect_to_mqtt_broker()

    # Start main() if activated
    if active:
        main()
    else:
        log(30, 'ORDER', 'MAIN don´t started, because deactivated!')
