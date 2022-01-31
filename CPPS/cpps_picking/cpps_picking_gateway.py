#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import random
import sys
import time
import requests
import threading

from threading import Lock

'''
##################################################

Logging requirements

Level       Numeric value
CRITICAL    50
ERROR       40
WARNING     30
INFO        20
DEBUG       10
NOTSET      0
'''

directory = 'logfiles'
filename = 'picking_logfile_{}.log'.format(time.strftime('%Y.%m.%d_%H:%M:%S', time.localtime()))
if not os.path.isdir(directory):
    os.mkdir(directory)

logging.basicConfig(
    filename=directory + '/' + filename,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s'
)


def log(level, topic, message, print_out=True):
    logging.log(
        level,
        '[{}]: {}'.format(
            '{:<20}'.format(topic),
            message
        )
    )
    if print_out:
        print('[{}]: {}'.format(
            '{:<20}'.format(topic),
            message
        )
        )


'''
##################################################
'''

# Global constants
CONFIGS = {
    'FMS_GATEWAY_URL': 'http://129.217.152.107:8760',
    'PHYNODE_GATEWAY_URL': 'http://192.168.2.13:8760',
    'FAILED_ATTEMPTS': 5,
    'PICK_KLT_ADDR': 1
}


class PickingGateway:
    def __init__(self, config_parser, demo_mode):
        self._picking_configs = config_parser['DEFAULT']
        self._klt_enum = dict(eval(self._picking_configs['KLT_ENUM']))
        self._picking_tasks = []
        self._checking = True
        self._demo_mode = demo_mode         # todo: implement control
        self._blocked_klts = []
        self._lock = Lock()
        self._threads = []
        self._initialize()

    def _initialize(self):
        if not self._demo_mode:
            # self._thread = threading.Thread(
            #     target=self.check_ack_from_phynodes,
            #     name='CheckingAck',
            #     daemon=True
            # )
            # self._thread.start()
            th = threading.Thread(
                target=self.check_for_unblock,
                name='check_for_unblock'
            )
            th.daemon = True
            self._threads.append(th)
            th.start()
        log(
            20,
            'PICKING_GATEWAY',
            '... Initialization completed\n'
        )

    def check_for_unblock(self):
        log(10, 'PICKING GATEWAY', '>>> Started unblock thread ...')
        log(10, '', '--------------------------------------------------')
        while True:
            if self._picking_tasks:
                self._lock.acquire()
                for picking_task in self._picking_tasks:
                    if not picking_task['restored'] and picking_task['fms_offer']:
                        phyaddr = picking_task['task']['phyaddr']
                        start_time = float(picking_task['fms_offer']['start_time'])
                        difference = start_time - float(picking_task['fms_offer']['estimated_pickup'])
                        unblock_time = start_time + 7.5 + difference
                        if time.time() > unblock_time:
                            self.restore_phyaddr(phyaddr)
                            picking_task['restored'] = True
                self._lock.release()
            time.sleep(1)

    def add_new_picking_task(self, task: dict) -> dict:
        """
        :param task: (dict)
        :return: (dict)
        """
        log(10, 'PICKING GATEWAY', '>>> Add new picking task ...')
        log(10, '', '--------------------------------------------------')
        picking_task = {
            'task': task,
            'fms_offer': None,
            'withdrawn': False,
            'arrived': False,
            'reserved': False,
            'booked': False,
            'restored': False
        }
        log(10,
            'ID:{} AV:{} WS:{}'.format(picking_task['task']['id_task'],
                                       picking_task['task']['id_labor_process'],
                                       picking_task['task']['workstation_id']
                                       ),
            '    klt_id: {}'.format(picking_task['task']['klt_id'])
            )
        log(10,
            'ID:{} AV:{} WS:{}'.format(picking_task['task']['id_task'],
                                       picking_task['task']['id_labor_process'],
                                       picking_task['task']['workstation_id']
                                       ),
            '    target: {}'.format(picking_task['task']['target'])
            )
        log(10,
            'ID:{} AV:{} WS:{}'.format(picking_task['task']['id_task'],
                                       picking_task['task']['id_labor_process'],
                                       picking_task['task']['workstation_id']
                                       ),
            '    desired_availability_date: {}'.format(
                datetime.datetime.fromtimestamp(picking_task['task']['desired_availability_date']))
            )
        log(10,
            'ID:{} AV:{} WS:{}'.format(picking_task['task']['id_task'],
                                       picking_task['task']['id_labor_process'],
                                       picking_task['task']['workstation_id']
                                       ),
            '    skill_time: {}'.format(picking_task['task']['skill_time'])
            )
        log(10,
            'ID:{} AV:{} WS:{}'.format(picking_task['task']['id_task'],
                                       picking_task['task']['id_labor_process'],
                                       picking_task['task']['workstation_id']
                                       ),
            '    phyaddr: {}'.format(picking_task['task']['phyaddr'])
            )
        self._lock.acquire()
        self._picking_tasks.append(picking_task)
        self._lock.release()
        return picking_task

    def book_picking_task(self,
                          id_task: int,
                          id_labor_process: str,
                          rejects: list,
                          workstation_id: str,
                          employee_id: str,
                          robot_id: str,
                          start_time: float,
                          time_slot_length: float,
                          rejects_for_fms: list,
                          workstation_vicon_id: str
                          ):
        log(10, 'BOOK ID:{} OP ID: {}'.format(str(id_task), id_labor_process), '>>> Start booking ...')
        log(10, '', '--------------------------------------------------')
        # log(10, 'REJECT LIST', rejects)
        if self._picking_tasks:
            self._lock.acquire()
            if rejects:
                for reject in rejects:
                    for picking_task in self._picking_tasks:
                        if picking_task['task']['id_task'] == id_task and \
                                picking_task['task']['id_labor_process'] == reject[0] and \
                                picking_task['task']['workstation_id'] == reject[1]:
                            self._picking_tasks.remove(picking_task)
                            log(20,
                                '{} / {}'.format(str(id_task), id_labor_process),
                                '    Reject 1 picking task for {}'.format(reject)
                                )
                            break
            for picking_task in self._picking_tasks:
                tuple_for_log = [id_labor_process, workstation_id]
                if picking_task['task']['id_task'] == id_task and \
                        picking_task['task']['id_labor_process'] == id_labor_process and \
                        picking_task['task']['workstation_id'] == workstation_id:
                    picking_task['task']['desired_availability_date'] = start_time
                    picking_task['booked'] = True
                    log(20,
                        '{} / {}'.format(str(id_task), id_labor_process),
                        '    Update picking task for {}'.format(tuple_for_log)
                        )
                    break
            self._lock.release()
            request_data = {
                'decision': {
                    'id_task': id_task,
                    'id_labor_process': id_labor_process,
                    'rejects': rejects_for_fms,
                    'workstation_id': workstation_vicon_id,
                    'employee_id': employee_id,
                    'robot_id': robot_id,
                    'start_time': start_time,
                    'time_slot_length': time_slot_length
                }
            }
            response = self.send_http_request(
                method='POST',
                url='{}/fms/api/pickrobot/book'.format(CONFIGS['FMS_GATEWAY_URL']),
                request_body=request_data
            )
            if response is None:
                log(40,
                    'BOOK ID:{} OP ID: {}'.format(str(id_task), id_labor_process),
                    '    ABORT! Received None response'
                    )
                return {'FAILURE': 'Received None response'}
            else:
                try:
                    payload = response.json()
                except ValueError:
                    log(40,
                        'BOOK ID:{} OP ID: {}'.format(str(id_task), id_labor_process),
                        '    ABORT! ValueError by parsing the payload'
                        )
                    return {'FAILURE': 'ValueError by parsing the payload'}
                log(20,
                    'PICKING GATEWAY',
                    '{:>25}: {}'.format('fms_book_result', payload))
                return payload
        return {'FAILURE': 'Did not find any picking task for task id {}'.format(id_task)}

    def check_ack_from_phynodes(self):
        while self._checking:
            for picking_task in self._picking_tasks:
                if time.time() > picking_task['task']['desired_availability_date']:
                    request_body1 = {
                        'phyaddr': picking_task['phyaddr']
                    }
                    response = self.send_http_request(
                        'POST',
                        '{}/gateway/RSTO'.format(CONFIGS['PHYNODE_GATEWAY_URL']),
                        request_body1
                    )
                    if response is not None and response.status_code == 200:
                        try:
                            payload = response.json()
                        except ValueError:
                            log(40, 'PICKING GATEWAY', '    ABORT! ValueError by parsing payload')
                            continue
                        if 'rsto' in payload and payload['rsto']:
                            request_body2 = {
                                'vicon_id': picking_task['klt_vicon_id']
                            }
                            self.send_http_request(
                                'POST',
                                '{}/fms/api/bring_home'.format(CONFIGS['FMS_GATEWAY_URL']),
                                request_body2
                            )
                            picking_task['withdrawn'] = True
            time.sleep(0.5)

    def get_picking_tasks(self):
        return self._picking_tasks

    def klt_arrived(self, id_task: int, phyaddr: int) -> bool:
        for task in self._picking_tasks:
            if task['id_task'] == id_task and task['phyaddr'] == phyaddr:
                task['arrived'] = True
                return task['arrived']
        return False

    # Returns picking task with same id task and id labor process if exists
    def find_phyaddr_for_task(self, id_cycle: str) -> int:
        log(10, 'PICKING GATEWAY', '>>> Start finding the required picking task ...')
        log(10, '', '--------------------------------------------------')
        result = None
        if self._picking_tasks:
            for picking_task in self._picking_tasks:
                if picking_task['task']['id_cycle'] == id_cycle and not picking_task['booked']:
                    result = picking_task['task']['phyaddr']
                    log(20,
                        'PICKING GATEWAY',
                        '    Find phyaddr (ADDR: {}) for task. Continue with offer'.format(result)
                        )
                    break
        if result is None:
            log(30, 'PICKING GATEWAY', '    Dont find phyaddr for task! Continue with offer')
        return result

    def get_offer(self,
                  alpha_time: float,
                  alpha_costs: float,
                  id_cycle: str,
                  id_task: int,
                  id_labor_process: str,
                  desired_availability_date: float,
                  skill_time: float,
                  target: str,
                  workstation_id: str,
                  components: dict,
                  buffer_time_workstation: float
                  ) -> dict:
        log(10, 'PICKING GATEWAY', '>>> Start offer ...')
        log(10, '', '--------------------------------------------------')
        phyaddr = self.find_phyaddr_for_task(id_cycle=id_cycle)
        if phyaddr is None:
            phyaddr = self.get_free_phyaddr(id_task=id_task)
            self.reserve_phyaddr(phyaddr=phyaddr, ordernumber=id_task)
            if phyaddr is None:
                log(40, 'PICKING GATEWAY', '    ABORT! No replies from any phynodes')
                return {'FAILURE': 'No replies from any phynodes'}
        task_for_fms = {
            'id_cycle': id_cycle,
            'id_task': id_task,
            'id_labor_process': id_labor_process,
            'klt_id': '/vicon/' + self._klt_enum[phyaddr] + '/' + self._klt_enum[phyaddr],
            'robot_id': '',
            'target': target,
            'desired_availability_date': desired_availability_date,
            'skill_time': skill_time,
            'alpha_time': alpha_time,
            'alpha_costs': alpha_costs,
            'phyaddr': phyaddr,
            'workstation_id': workstation_id,
            'components': components,
            'buffer_time': buffer_time_workstation
        }
        picking_task = self.add_new_picking_task(
            task=task_for_fms
        )
        # if self.reserve_phyaddr(phyaddr=phyaddr, ordernumber=id_task):
        #     picking_task['reserved'] = True
        log(10, 'PICKING_GATEWAY', '    Send request to Fleet Management System')
        response = self.send_http_request(
            method='POST',
            url='{}/fms/api/pickrobot/offer'.format(CONFIGS['FMS_GATEWAY_URL']),
            request_body={
                'task': task_for_fms
            }
        )
        if response is None:
            log(40, 'PICKING_GATEWAY', '    Received None response')
            return {'FAILURE': 'Failed to get an offer from fms'}
        else:
            try:
                payload = response.json()
            except ValueError:
                log(40, 'PICKING GATEWAY', '    Received None payload')
                return {'FAILURE': 'ValueError from fms'}
            picking_task['fms_offer'] = payload
            log(10, 'PICKING_GATEWAY', '    Save fms offer into picking task')
            for key in picking_task['fms_offer']:
                if key == 'estimated_pickup' or key == 'start_time' or key == 'robot_start_time':
                    value = datetime.datetime.fromtimestamp(picking_task['fms_offer'][key])
                else:
                    value = picking_task['fms_offer'][key]
                log(20, 'PICKING_GATEWAY', '{:>25}: {}'.format(key, value))
            log(10, 'PICKING_GATEWAY', '    Reply the fms offer to the workstation gateway')
        return picking_task['fms_offer']

    def get_free_phyaddr(self, id_task: int) -> int:
        log(10, 'PICKING GATEWAY', '>>> Searching for free klt ...')
        log(10, '', '--------------------------------------------------')
        if self._demo_mode:
            empty_phynode_addr = random.randrange(start=11, stop=17, step=1)
            log(20, 'PICKING GATEWAY', '    Find a free klt (ADDR: {})'.format(empty_phynode_addr))
        else:
            successful = False
            empty_phynode_addr = None
            url = '{}/gateway/POLL'.format(CONFIGS['PHYNODE_GATEWAY_URL'])
            itemdescr = int(self._picking_configs['itemdescr'])
            max_attempts = CONFIGS['FAILED_ATTEMPTS']
            attempts = 1
            while empty_phynode_addr is None and attempts <= max_attempts:
                request_body = {
                    'ordernumber': id_task,
                    'itemdescr': CONFIGS['PICK_KLT_ADDR']
                }
                log(10, 'PICKING GATEWAY', '    Send request [ordernumber: {}, itemdescr:{}]'.format(id_task, itemdescr))
                response = self.send_http_request('POST', url, request_body)
                if response is not None:
                    try:
                        payload = response.json()
                    except ValueError:
                        print('\n')
                        log(40, 'PICKING GATEWAY', '    ABORT! ValueError by parsing the payload')
                        break

                    if 'FAILURE' not in payload:
                        phynode_with_lowest_energy = None
                        # Iterate over the list of possible candidates to find the phynode
                        # with lowest energy.
                        for p_item in payload:
                            if 'ordernumber' in p_item and \
                                    p_item['ordernumber'] == id_task:
                                if phynode_with_lowest_energy is None:
                                    phynode_with_lowest_energy = p_item
                                elif phynode_with_lowest_energy['energy'] > p_item['energy']:
                                    phynode_with_lowest_energy = p_item

                        empty_phynode_addr = int(phynode_with_lowest_energy['phyaddr'])
                        successful = True
                if not successful:
                    sys.stdout.write('\r[{}]: {}'.format('{:<20}'.format('PICKING GATEWAY'),
                                                         '    Picking abort after: {:4d}'.format(max_attempts - attempts)))
                    sys.stdout.flush()
                    time.sleep(.5)
                attempts += 1
            else:
                if attempts > max_attempts:
                    log(30, 'PICKING GATEWAY', '    Connection failed after {:d} attempts!'.format(max_attempts))
                else:
                    log(20, 'PICKING GATEWAY', '    Find a free klt (ADDR: {})'.format(empty_phynode_addr))
        return empty_phynode_addr

    def reserve_phyaddr(self, phyaddr: int, ordernumber: int = 0) -> bool:
        log(10, 'PICKING GATEWAY', '>>> Start reserving a phynode')
        log(10, '', '--------------------------------------------------')
        if self._demo_mode:
            log(20, 'PICKING GATEWAY', '   Execute demo mode without reserving a phynode')
        else:
            url = '{}/gateway/RSVE'.format(CONFIGS['PHYNODE_GATEWAY_URL'])
            request_body = {
                'phyaddr': phyaddr,
                'ordernumber': ordernumber,
                'amount': 0
            }
            response = self.send_http_request('POST', url, request_body)
            if response.status_code == 200 and response is not None:
                log(20,
                    'PICKING GATEWAY',
                    '    Reserve phynode (ADDR: {:d})'.format(phyaddr)
                    )
                return True
            else:
                log(40,
                    'PICKING GATEWAY',
                    '    Failed reserve the phynode (ADDR: {:d})'.format(phyaddr)
                    )
                return False

    def restore_phyaddr(self,  phyaddr: int):
        log(10, 'PICKING GATEWAY', '>>> Start restore a phynode')
        log(10, '', '--------------------------------------------------')
        url = '{}/gateway/BUTN'.format(CONFIGS['PHYNODE_GATEWAY_URL'])
        request_body = {
            'addr': phyaddr,
            'buttonId': 1
        }
        response = self.send_http_request('POST', url, request_body)
        if response.status_code == 200 and response is not None:
            log(20,
                'PICKING GATEWAY',
                '    Restored phynode (ADDR: {:d})'.format(phyaddr)
                )
            return True
        else:
            log(40,
                'PICKING GATEWAY',
                '    Failed restore the phynode (ADDR: {:d})'.format(phyaddr)
                )
            return False

    @staticmethod
    def send_http_request(method: str, url: str, request_body: object):
        try:
            data = json.dumps(request_body)
            if method == 'GET':
                response = requests.get(url, data=data)
            elif method == 'POST':
                response = requests.post(url, data=data)
            else:
                return None
        except requests.exceptions.RequestException as err:
            log(40, 'PICKING GATEWAY', str(err))
            return None

        if response.status_code == 200:
            return response
        elif response.status_code == 405:
            log(40, 'HTTP', 'Bad method request. Status code: {}'.format(response.status_code))
            return None

    @staticmethod
    def validate_task(task):
        id_task = task['id_task']
        id_labor_process = task['id_labor_process']
        desired_availability_date = task['desired_availability_date']
        desired_skill = task['desired_skill']
        alpha_time = task['alpha_time']
        alpha_costs = task['alpha_costs']
        if id_task is None or \
                not isinstance(id_task, int):
            return False
        elif id_labor_process is None or \
                not isinstance(id_labor_process, str):
            return False
        elif desired_availability_date is None or \
                not isinstance(desired_availability_date, float) or \
                desired_availability_date < time.time():
            return False
        elif desired_skill is None or \
                not isinstance(desired_skill, str):
            return False
        elif alpha_time is None or \
                not isinstance(alpha_time, float) or \
                (0 > alpha_time > 1):
            return False
        elif alpha_costs is None or \
                not isinstance(alpha_costs, float) or \
                (0 > alpha_costs > 1):
            return False
        return True
