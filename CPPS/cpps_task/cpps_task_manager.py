#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import os
import string
import sys
import json
import threading
import time
import math
import requests
import random
import logging
import configparser
import paho.mqtt.client as mqtt
import numpy

from copy import deepcopy
from cpps_task import Task
from pymongo import MongoClient

FMS_ack = True

'''
##################################################

Logging requirements

Level       Nummeric value
CRITICAL    50
ERROR       40
WARNING     30
INFO        20
DEBUG       10
NOTSET      0
'''

directory = 'logfiles'
filename = 'task_manager_logfile_{}.log'.format(time.strftime('%Y.%m.%d_%H:%M:%S', time.localtime()))
if not os.path.isdir(directory):
    os.mkdir(directory)

logger = logging.getLogger('task')
logger.setLevel(logging.DEBUG)
fh_manager = logging.FileHandler(directory + '/' + filename)
fh_manager.setLevel(logging.DEBUG)
fm_manager = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s')
fh_manager.setFormatter(fm_manager)
logger.addHandler(fh_manager)


# logging.basicConfig(
#     filename=directory + '/' + filename,
#     level=logging.DEBUG,
#     format='%(asctime)s %(levelname)-8s %(message)s'
# )


def log(level, topic, message, print_out=True):
    logger.log(
        level,
        '[{}]: {}'.format(
            '{:<20}'.format(topic),
            message
        )
    )
    if print_out:
        print('[{}]: {}'.format('{:<20}'.format(topic), message))


'''
##################################################
'''

client = MongoClient('mongodb://192.168.2.188:27017/')
db = client.cpps
collection = db.cpps_tasks

'''
##################################################
'''


class TaskManager(threading.Thread):
    def __init__(self,
                 task_collection: MongoClient,
                 config_parser: configparser,
                 config_file_name: str,
                 demo_mode: bool,
                 virtual_phynode_mode: bool
                 ):
        super().__init__()
        self._task_collection = task_collection
        self._config_file_name = config_file_name,
        self._config_parser = config_parser
        self._manager_configs = self._config_parser['DEFAULT']
        self._demo_mode = demo_mode
        self._virtual_phynode_mode = virtual_phynode_mode
        self._blocked_klt_list = []
        self._stop = False
        self._agents = []
        self._positions = {}
        self._reference_turning_time = {}
        self._reference_review = {}
        self.lock = threading.Lock()
        self._initialize()

    def _initialize(self):
        # Realtime or demo szenario
        if self._demo_mode:
            log_text = '... Start demo scenario'
        else:
            log_text = '... Start realtime scenario'
        log(10, 'TASK_MANAGER', log_text)
        if self._virtual_phynode_mode:
            log_text = '... Start virtual phynode scenario'
        else:
            log_text = '... Start real phynode scenario'
        log(10, 'TASK_MANAGER', log_text)
        # Init MQTT Client
        self._mqtt_client = mqtt.Client('TaskManager')
        self._mqtt_connect()
        # Init the reference criteria
        if bool(self._manager_configs['reference_turning_time_init']):
            param = int(self._manager_configs['reference_turning_time_param'])
            operations = dict(eval(self._manager_configs['reference_turning_time_init_values']))
            self._manager_configs['reference_turning_time_init'] = 'False'
            for operation in operations.keys():
                values = []
                for count in range(1, param + 1):
                    values.append(operations['{}'.format(operation)])
                self._reference_turning_time['{}'.format(operation)] = values
            self._manager_configs['reference_turning_time'] = str(self._reference_turning_time)
        else:
            self._reference_turning_time = self._manager_configs['reference_turning_time']
        if bool(self._manager_configs['reference_review_init']):
            param = int(self._manager_configs['reference_review_param'])
            operations = dict(eval(self._manager_configs['reference_review_init_values']))
            self._manager_configs['reference_review_init'] = 'False'
            for operation in operations.keys():
                values = []
                for count in range(1, param + 1):
                    values.append(operations['{}'.format(operation)])
                self._reference_review['{}'.format(operation)] = values
            self._manager_configs['reference_review'] = str(self._reference_review)
        else:
            self._reference_review = self._manager_configs['reference_review']
        # Update config file
        self.update_configs('reference_turning_time', str(self._reference_turning_time))
        self.update_configs('reference_review', str(self._reference_review))
        log(10,
            'TASK_MANAGER',
            '... Initialization completed\n----------------------------------------------------------'
            )
        log(10, 'TASK_MANAGER', '    Wait for new Tasks...'
            )

    def _mqtt_connect(self):
        host = str(self._manager_configs['MQTT_HOST'])
        port = int(self._manager_configs['MQTT_PORT'])
        topic_of_positions = str(self._manager_configs['MQTT_TOPIC_POSITION'])
        self._mqtt_client.message_callback_add(
            topic_of_positions,
            self.set_position
        )
        rc = self._mqtt_client.connect(
            host=host,
            port=port,
            keepalive=60,
            bind_address=""
        )
        if rc == 0:
            log(10,
                'MQTT_CLIENT',
                '... Connected to broker: {} on port: {}'.format(
                    host,
                    port
                )
                )
            log(10,
                'MQTT_CLIENT',
                '... Subscribed to topic: {}'.format(
                    topic_of_positions
                )
                )
            self._mqtt_client.subscribe(topic_of_positions)
            self._mqtt_client.loop_start()
            time.sleep(.2)
        else:
            log(
                40,
                'MQTT_CLIENT',
                'Connection failed with status code: {:d}'.format(rc)
            )
            sys.exit(1)

    def mqtt_publish(self,
                     subject: str,
                     duration: float,
                     color: str,
                     xscale: float,
                     yscale: float,
                     animation: str,
                     visible: str  # true; false
                     ):
        message = {
            'subject': subject,
            'duration': duration,
            'color': color,
            'xscale': xscale,
            'yscale': yscale,
            'animation': animation,
            'visible': visible
        }
        self._mqtt_client.publish(topic='/unity/laser/vicon/animation', payload=json.dumps(message), qos=0)

    def run(self):
        while not self._stop:
            orders = self._task_collection.find()
            next_order = None
            for order in orders:
                if order['state'] == 'open' or order['state'] == 'restart':
                    if next_order is None:
                        next_order = order
                    elif next_order['task_id'] > order['task_id']:
                        next_order = order
            if next_order is not None:
                new_task = Task.from_dict(next_order)
                # Request to the Fleet Management System. Allocating a robot for the task.
                payload = self.send_http_request(
                    'POST',
                    '{}/fms/api/taskrobot/block'.format(self._manager_configs['fms_gateway_url']),
                    {
                        'task_id': new_task.task_id
                    }
                )
                if payload is not None and 'SUCCESS' in payload:
                    # Update database
                    self.update_states(id_order=new_task.task_id, topic='state', status='active')
                    new_task.robot = payload['SUCCESS']
                    new_agent = TaskAgent(
                        agent_id=random.randint(1, 1000),
                        task=new_task,
                        task_manager=self,
                        config_parser=self._config_parser,
                        positions=self._positions,
                        demo_mode=self._demo_mode,
                        virtual_phynode_mode=self._virtual_phynode_mode
                    )
                    self._agents.append(new_agent)
                    log(20,
                        'TASK_MANAGER',
                        '... Create task (ID: {}) with Robot ({})'.format(new_task.task_id, new_task.robot['robot_id'])
                        )
                    new_agent.start()
                    log(10, 'TASK_MANAGER', '    Wait for a new task offer')
                    # self._stop = True
                else:
                    # self._stop = True
                    log(30, 'TASK_MANAGER', '    At the moment no other robot is available')
            time.sleep(1)
        else:
            log(
                20,
                'TASK_MANAGER',
                '... Process stopped'
            )

    def get_beta(self):
        self._config_parser.read(self._config_file_name)
        return float(self._config_parser['DEFAULT']['beta'])

    def reserve_free_klt(self):
        attempts = 0
        while attempts < 20:
            phyaddr = random.randrange(start=20, stop=24, step=1)
            if phyaddr not in self._blocked_klt_list:
                self._blocked_klt_list.append(phyaddr)
                log(10, 'TASK_MANAGER', '    Reserve phynode (ADDR: {})'.format(phyaddr))
                return phyaddr
            attempts += 1
        return 99

    def restore_free_klt(self, phyaddr: int):
        try:
            self._blocked_klt_list.remove(phyaddr)
            log(10, 'TASK_MANAGER', '    Restore phynode (ADDR: {})'.format(phyaddr))
            return True
        except KeyError:
            return False

    def get_gamma(self):
        self._config_parser.read(self._config_file_name)
        return float(self._config_parser['DEFAULT']['gamma'])

    def get_average_turning_time(self, operation: str) -> float:
        operation_values = list(self._reference_turning_time['{}'.format(operation)])
        return sum(operation_values) / len(operation_values)

    def get_average_review(self, operation: str) -> float:
        operation_values = list(self._reference_review['{}'.format(operation)])
        return sum(operation_values) / len(operation_values)

    def get_reference_turning_time(self):
        return self._reference_turning_time

    def get_reference_turning_time_remaining(self,
                                             finished_operations: list,
                                             average_turning_time: float
                                             ) -> float:
        result = average_turning_time
        for operation in finished_operations:
            result -= self.get_average_turning_time(operation)
        return result

    def get_reference_review(self):
        return self._reference_review

    def update_configs(self, option: str, value: str):
        section = 'DEFAULT'
        if type(option) is not str or type(value) is not str:
            log(
                20,
                'CONFIG_PARSER',
                '... Failed to update option: {}. Wrong type format!'.format(option)
            )
            return False
        else:
            try:
                self._config_parser.set(section, option, value)
                with open(self._manager_configs['CONFIG_FILE_NAME'], 'w') as configfile:
                    self._config_parser.write(configfile)
                configfile.close()
                log(
                    20,
                    'CONFIG_PARSER',
                    '... Update option: {}'.format(option)
                )
                return True
            except (TypeError, configparser.NoSectionError) as err:
                log(
                    20,
                    'CONFIG_PARSER',
                    '... Raised Exception: {}!'.format(type(err))
                )
                return False

    def update_reference_turning_time(self, operation: str, new_turning_time: float):
        operation_values = list(self._reference_turning_time['{}'.format(operation)])
        del operation_values[0]
        operation_values.append(round(new_turning_time, 3))
        self._reference_turning_time['{}'.format(operation)] = operation_values
        self.update_configs('REFERENCE_TURNING_TIME', str(self._reference_turning_time))

    def update_reference_review(self, operation: str, new_review: float):
        operation_values = list(self._reference_review['{}'.format(operation)])
        del operation_values[0]
        operation_values.append(round(new_review, 3))
        self._reference_review['{}'.format(operation)] = operation_values
        self.update_configs('REFERENCE_REVIEW', str(self._reference_review))

    def set_position(self, client, userdata, message):
        payload = message.payload
        data = json.loads(payload.decode())
        self._positions[data['child_frame_id']] = {
            'translation': data['transform']['translation']
        }

    def stop(self):
        self._stop = True

    @staticmethod
    def random_generator(size: int = 6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    @staticmethod
    def send_http_request(method, url, request_body):
        payload = None
        try:
            data = json.dumps(request_body)
            log(20, 'HTTP', '    Send request to {}'.format(url))
            if method == 'GET':
                response = requests.get(url, data=data)
            elif method == 'POST':
                response = requests.post(url, data=data)
            else:
                return payload
        except requests.exceptions.RequestException as err:
            log(40, 'HTTP', '    Raise RequestException!\n{}'.format(str(err)))
            return None
        if response is None:
            log(40, 'HTTP', '    Receive None response object!')
            return payload
        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError:
                log(40, 'HTTP', 'Raise ValueError by parsing response data!')
            return payload
        elif response.status_code == 400:
            try:
                log(30,
                    'HTTP',
                    '{}'.format(response.json())
                    )
            except ValueError:
                log(40, 'HTTP', 'Raise ValueError by parsing response data!')
            return payload
        else:
            log(30, 'HTTP', '    Receive wrong status code: {}'.format(response.status_code))
        return payload

    @staticmethod
    def update_states(id_order, topic, status):
        order = {'task_id': id_order}
        new_value = {"$set": {topic: status}}
        collection.update_one(order, new_value)


class TaskAgent(threading.Thread):
    def __init__(self,
                 agent_id: int,
                 task: Task,
                 task_manager: TaskManager,
                 config_parser: configparser.ConfigParser,
                 positions: dict,
                 demo_mode: bool,
                 virtual_phynode_mode: bool
                 ):
        super().__init__()
        self._agent_id = agent_id
        self._logger = logging.getLogger('TaskAgent_{:d}'.format(agent_id))
        self._cpps_task_manager = task_manager
        self._agent_configs = config_parser['DEFAULT']
        self._demo_mode = demo_mode
        self._virtual_phynode_mode = virtual_phynode_mode
        self._klt_enum = {}
        self._priority_graph = {}
        self._priority_graph_index = 1
        self._failed = False
        self._block = False
        self._task = task
        self._secondary_components = {}
        self._next_completion_time = 0.0
        self._last_workstation_id = ''
        self._next_start_time = 0.0
        self._positions = positions
        self._initialize()
        time.sleep(0.5)
        self.log(10,
                 'AGENT ID:{:d}'.format(self._agent_id),
                 '... Initialization completed'
                 )

    def log(self, level, topic, message, print_out=True):
        self._logger.log(
            level,
            '[{}]: {}'.format(
                '{:<20}'.format(topic),
                message
            )
        )
        if print_out:
            print('[{}]: {}'.format('{:<20}'.format(topic), message))

    def _initialize(self):
        direct = 'logfiles'
        file = 'task_{:d}_agent_{:d}_logfile.log'.format(self._task.task_id, self._agent_id)
        self._logger.setLevel(logging.DEBUG)
        fh_agent = logging.FileHandler(direct + '/' + file)
        fh_agent.setLevel(logging.DEBUG)
        fm_agent = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s')
        fh_agent.setFormatter(fm_agent)
        self._logger.addHandler(fh_agent)
        if not self._demo_mode:
            log_text = '... Start realtime scenario'
        else:
            log_text = '... Start demo scenario'
        log(10, 'TASK_MANAGER', log_text)
        try:
            # Update database with task robot id
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'task_robot_id',
                self._task.robot['robot_id']
            )
            product_variants = dict(eval(self._agent_configs['product_variants']))
            self._klt_enum = dict(eval(self._agent_configs['klt_enum']))
            self._priority_graph = dict(eval(self._agent_configs['priority_graph']))
            self._secondary_components = product_variants[self._task.product_variant]
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '... Load klt enumeration settings'
                     )
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '... Load priority graph'
                     )
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '... Load secondary components'
                     )
        except KeyError:
            self._failed = True
            self.log(40,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     'ABORT! KeyError by parsing {} in product variants'.format(self._task.product_variant)
                     )

    def run(self):
        # Starting stage 1
        if not self._failed:
            self.stage_1()
        # # Starting stage 2
        if not self._failed:
            self.stage_2()
        if self._failed:
            self.restore_phyaddr()
            # Update database
            self._cpps_task_manager.update_states(id_order=self._task.task_id, topic='state', status='failed')
        else:
            # Update database
            self._cpps_task_manager.update_states(id_order=self._task.task_id, topic='state', status='finished')
        self.log(
            20,
            'AGENT ID:{:d}'.format(self._agent_id),
            'Finished ...'
        )

    def _decision_finding(self, offers: dict, stage: str) -> dict:
        """
        :param offers:
        :return: (dict)
            alpha_time: (float)
            alpha_costs: (float)
            buffer_time: (float)
            completion_time: (float)
            costs_ial_transport: (float)
            costs_workstation: (float)
            desired_availability_date: (float)
            id_task: (int)
            id_labor_process: (str)
            skill_time: (float)
            time_slot_length: (float)
        """
        local_offers = deepcopy(offers)
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start choosing the best decision')
        self.log(10, '', '--------------------------------------------------')
        # print(json.dumps(offers, indent=4, sort_keys=True))
        if not local_offers:
            self._failed = True
            self.log(40,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Got an empty offer argument!'
                     )
            return {}
        else:
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '{:>25}: {:d}'.format('total_count_of_offers', len(local_offers))
                     )
            best_decision = None
            for key in local_offers:
                offer = local_offers[key]
                if 'valuation_result' in offer:
                    review_result = offer['valuation_result'] / \
                                    self._cpps_task_manager.get_average_review(
                                        offer['offer_from_workstation']['id_labor_process']
                                    )
                    offer['review_result'] = review_result
                    self.log(20,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '{:>25}: {:0.2f}'.format('review_result_{}'.format(key), review_result)
                             )
                    if best_decision is None:
                        best_decision = key
                    elif local_offers[best_decision]['review_result'] > review_result:
                        best_decision = key
                else:
                    self.log(30,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '    Got review result without a valuation result'
                             )
            if best_decision is not None and local_offers[best_decision]['valuation_result'] != 999:
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    stage,
                    'Choose best decision with review result: {:0.2f} from {} for {}'.format(
                        local_offers[best_decision]['review_result'],
                        best_decision,
                        local_offers[best_decision]['offer_from_workstation']['id_labor_process']
                    )
                )
                self.log(
                    20,
                    'AGENT ID:{:d}'.format(self._agent_id),
                    '    Best decision with review result: {:0.2f} from {} for {}'.format(
                        local_offers[best_decision]['review_result'],
                        best_decision,
                        local_offers[best_decision]['offer_from_workstation']['id_labor_process']
                    )
                )
                best_offer = local_offers[best_decision]
                best_offer['workstation_id'] = local_offers[best_decision]['offer_from_workstation']['workstation_id']
                self._cpps_task_manager.update_reference_review(
                    operation=best_offer['offer_from_workstation']['id_labor_process'],
                    new_review=best_offer['valuation_result']
                )
                self._cpps_task_manager.update_reference_turning_time(
                    operation=best_offer['offer_from_workstation']['id_labor_process'],
                    new_turning_time=best_offer['throughput_time_j']
                )
                self._cpps_task_manager.mqtt_publish(self._klt_enum[self._task.empty_klt_phyaddr], 5,
                                                     '#00FF00', 0.9, 1.5, 'pulse', 'true')
                self._cpps_task_manager.mqtt_publish(best_offer['offer_from_workstation']['target'], 5,
                                                     '#00FF00', 1.1, 2.5, 'pulse', 'true')
                if self._demo_mode:
                    self._last_workstation_id = best_offer['workstation_id']
                return best_offer
            else:
                self._failed = True
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    stage,
                    'ABORT! No valid offer received'
                )
                self.log(40,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '    ABORT! No valid offer received'
                         )
                return {}

    def _get_alpha_time(self):
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start calculating the alpha time parameter')
        self.log(10, '', '--------------------------------------------------')
        finished_operations = []
        average_turning_time = 0.0
        for node in self._priority_graph['finished_nodes']:
            finished_operations.append(self._priority_graph[node]['operation'])
        beta = self._cpps_task_manager.get_beta()
        self.log(20, 'AGENT ID:{:d}'.format(self._agent_id), '{:>25}: {}'.format('beta', beta))
        gamma = self._cpps_task_manager.get_gamma()
        self.log(20, 'AGENT ID:{:d}'.format(self._agent_id), '{:>25}: {}'.format('gamma', gamma))
        for key in self._cpps_task_manager.get_reference_turning_time().keys():
            average_turning_time += self._cpps_task_manager.get_average_turning_time(key)
        self.log(20, 'AGENT ID:{:d}'.format(self._agent_id), '{:>25}: {} sec'.format('average_turning_time',
                                                                                     int(average_turning_time)
                                                                                     )
                 )
        remaining_turning_time = self._cpps_task_manager.get_reference_turning_time_remaining(finished_operations,
                                                                                              average_turning_time
                                                                                              )
        self.log(20, 'AGENT ID:{:d}'.format(self._agent_id), '{:>25}: {} sec'.format('remaining_turning_time',
                                                                                     int(remaining_turning_time)
                                                                                     )
                 )
        task_end_time_planned = self._task.task_end_time
        self.log(20, 'AGENT ID:{:d}'.format(
            self._agent_id), '{:>25}: {}'.format('task_end_time_planned',
                                                 datetime.datetime.fromtimestamp(task_end_time_planned)
                                                 )
                 )
        task_end_time_expected = self._next_completion_time + remaining_turning_time
        self.log(20, 'AGENT ID:{:d}'.format(
            self._agent_id), '{:>25}: {}'.format('task_end_time_expected',
                                                 datetime.datetime.fromtimestamp(task_end_time_expected)
                                                 )
                 )
        if self._task.task_end_time < task_end_time_expected:
            result = gamma + (1 - gamma) * math.exp(-1 / (beta * (task_end_time_expected - task_end_time_planned)))
        else:
            result = gamma
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                'Set ALPHA TIME parameter: {}'.format(result)
            )
        self.log(20, 'AGENT ID:{:d}'.format(self._agent_id), '{:>25}: {:0.2f}'.format('ALPHA_TIME', result))
        return result

    def _get_alpha_costs(self, alpha_time: float) -> float:
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start calculating the alpha costs parameter')
        self.log(10, '', '--------------------------------------------------')
        result = 1 - alpha_time
        # Update database
        self._cpps_task_manager.update_states(
            self._task.task_id,
            'stage1',
            'Set ALPHA TIME parameter: {}'.format(result)
        )
        self.log(20, 'AGENT ID:{:d}'.format(self._agent_id), '{:>25}: {:0.2f}'.format('ALPHA_COSTS', result))
        return result

    def _get_offer(self,
                   id_cycle: str,
                   id_labor_process: str,
                   completion_time: float,
                   stage: str
                   ) -> dict:
        alpha_time = self._get_alpha_time()
        alpha_costs = self._get_alpha_costs(alpha_time)
        # Update database
        self._cpps_task_manager.update_states(
            self._task.task_id,
            'stage1',
            'Start offer process..'
        )
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start getting an offer')
        self.log(10, '', '--------------------------------------------------')
        request_body = {
            'task': {
                'alpha_time': alpha_time,
                'alpha_costs': alpha_costs,
                'completion_time': completion_time,
                'id_cycle': id_cycle,
                'id_task': self._task.task_id,
                'id_labor_process': id_labor_process,
                'robot': self._task.robot,
                'components': self._secondary_components[id_labor_process],
                'last_workstation_id': self._last_workstation_id
            }
        }
        payload = self._cpps_task_manager.send_http_request(
            method='POST',
            url='{}/ws/api/offer'.format(self._agent_configs['workstation_gateway_url']),
            request_body=request_body
        )
        if payload is not None:
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                stage,
                'Received {} offer(s) from workstation gateway for {}'.format(
                    len(payload),
                    self._priority_graph[self._priority_graph['start_node']]['operation']
                )
            )
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Received {} offer(s) from workstation gateway'.format(len(payload))
                     )
            self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '    Continue with next step ...')
            return payload
        else:
            self._failed = True
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                'Finished offer process with none response from workstation gateway'
            )
            self.log(40, 'AGENT ID:{:d}'.format(self._agent_id), '    Received empty response from workstation gateway')
            return {}

    # Return a boolean if task will be finished
    def _is_finished(self) -> bool:
        if self._priority_graph[self._priority_graph['end_node']]['state'] == 0:
            return False
        return True

    # Request for a free phynode
    def _get_phynode(self):
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start poll a phynode')
        self.log(10, '', '--------------------------------------------------')
        url = '{}/gateway/POLL'.format(self._agent_configs['PHYNODE_GATEWAY_URL'])
        request_body = {
            'ordernumber': self._task.task_id,
            'itemdescr': self._agent_configs['task_klt_addr']
        }
        max_attempts = int(self._agent_configs['failed_attempts_polling'])
        attempts = 1
        successful = False
        new_line = False
        while not successful and attempts <= max_attempts:
            if self._virtual_phynode_mode:
                self._task.empty_klt_phyaddr = self._cpps_task_manager.reserve_free_klt()
                self._task.empty_klt_energy = 999
                successful = True
            else:
                # Search for a free klt
                payload = self._cpps_task_manager.send_http_request('POST', url, request_body)
                if payload is not None and 'FAILURE' not in payload:
                    phynode_with_lowest_energy = None
                    # Iterate over the list of possible candidates to find the phynode
                    # with lowest energy.
                    for p_item in payload:
                        if 'ordernumber' in p_item and p_item['ordernumber'] == self._task.task_id:
                            if phynode_with_lowest_energy is None:
                                phynode_with_lowest_energy = p_item
                            elif phynode_with_lowest_energy['energy'] > p_item['energy']:
                                phynode_with_lowest_energy = p_item

                    self._task.empty_klt_phyaddr = phynode_with_lowest_energy['phyaddr']
                    self._task.empty_klt_energy = phynode_with_lowest_energy['energy']
                    successful = True
                if not successful:
                    # Update database
                    self._cpps_task_manager.update_states(
                        self._task.task_id,
                        'stage1',
                        'Empty cart not reply! Abort after {:d} attempt(s)'.format(max_attempts - attempts)
                    )
                    self.log(40,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '    {}. poll for task id: {} failed!'.format(attempts, self._task.task_id)
                             )
                    # sys.stdout.write('\r[{}]: {}'.format(
                    #     '{:<20}'.format('AGENT ID:{:d}'.format(self._agent_id)),
                    #     '    Polling, abort after {:4d} attempt(s)'.format(max_attempts - attempts))
                    # )
                    # sys.stdout.flush()
                    # new_line = True
                    attempts += 1
                    time.sleep(.5)
        else:
            # print('\n')
            # If FAILURE
            if attempts > max_attempts:
                self._failed = True
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'stage1',
                    'timeout! Empty phynodes dont respond'
                )
                if new_line:
                    text = '\n    POLL abort after {:d} attempt(s) to set a phynode!'.format(max_attempts)
                else:
                    text = '    POLL abort after {:d} attempt(s) to set a phynode!'.format(max_attempts)
                self.log(40,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         text
                         )
            # If SUCCESS
            else:
                # Update database
                self._cpps_task_manager.update_states(self._task.task_id, 'stage1', 'Polling phynode complete!')
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'empty_klt_phyaddr',
                    self._task.empty_klt_phyaddr
                )
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'empty_klt_energy',
                    self._task.empty_klt_energy
                )
                if new_line:
                    text = '\n    Poll phynode (ADDR: {})'.format(self._task.empty_klt_phyaddr)
                else:
                    text = '    Poll phynode (ADDR: {})'.format(self._task.empty_klt_phyaddr)
                self.log(20,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         text
                         )

    # Reserve the free phynode
    def _set_phynode(self, stage):
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start reserving a phynode')
        self.log(10, '', '--------------------------------------------------')
        if self._virtual_phynode_mode:
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Execute virtual phynode mode. Phynode is already reserved'
                     )
        else:
            url = '{}/gateway/RSVE'.format(self._agent_configs['phynode_gateway_url'])
            request_body = {
                'phyaddr': self._task.empty_klt_phyaddr,
                'ordernumber': self._task.task_id,
                'amount': 0
            }
            payload = self._cpps_task_manager.send_http_request('POST', url, request_body)
            if payload is not None:
                klt = self._klt_enum[self._task.empty_klt_phyaddr]
                target = 'vicon/{}/{}'.format(klt, klt)
                # Set home position
                try:
                    current_position = self._positions[target]
                    self._positions['home_position_{}'.format(klt)] = current_position
                except KeyError:
                    self._failed = True
                    # Update database
                    self._cpps_task_manager.update_states(
                        self._task.task_id,
                        stage,
                        'Failed to set the home position for Klt {}'.format(klt)
                    )
                    self.log(40,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '    Failed to set the home position for Klt {}'.format(klt)
                             )
                    return
                self._cpps_task_manager.mqtt_publish(klt, 60, 'magenta', 0.9, 1.5, 'none', 'true')
                self._cpps_task_manager.send_http_request(
                    method='POST',
                    url='{}/fms/api/robot/pick_cart'.format(self._agent_configs['fms_gateway_url']),
                    request_body={
                        'robot_id': self._task.robot['robot_id'],
                        'target': target,
                        'demo_mode': self._demo_mode
                    }
                )
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'stage1',
                    '    Reserving the phynode (ADDR: {}) complete!'.format(self._task.empty_klt_phyaddr)
                )
                self.log(20,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '    Reserve phynode (ADDR: {:d})'.format(self._task.empty_klt_phyaddr)
                         )
            else:
                self._failed = True
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'stage1',
                    'ABORT! Failed to block the phynode (ADDR: {:d})'.format(self._task.empty_klt_phyaddr)
                )
                self.log(40,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '    Failed to block the phynode (ADDR: {:d})'.format(self._task.empty_klt_phyaddr)
                         )

    # Task end time will be the time, when the task could be finished
    def _set_task_end_time(self):
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start calculating the task end time')
        self.log(10, '', '--------------------------------------------------')
        current_time = self._next_completion_time
        entire_cycle_time = 0.0
        for key in self._cpps_task_manager.get_reference_turning_time().keys():
            entire_cycle_time += self._cpps_task_manager.get_average_turning_time(key)
        self.log(20,
                 'AGENT ID:{:d}'.format(self._agent_id),
                 '{:>25}: {:d}:{:d} min'.format('entire_cycle_time',
                                                int(entire_cycle_time / 60),
                                                int(entire_cycle_time % 60)
                                                )
                 )
        self._task.task_end_time = current_time + entire_cycle_time
        # Update database
        self._cpps_task_manager.update_states(
            self._task.task_id,
            'stage1',
            '{:>25}: {}'.format('Calculate task end time', datetime.datetime.fromtimestamp(self._task.task_end_time))
        )
        self._cpps_task_manager.update_states(
            self._task.task_id,
            'task_end_time_planned',
            self._task.task_end_time
        )
        self.log(
            20,
            'AGENT ID:{:d}'.format(self._agent_id),
            '{:>25}: {}'.format('task_end_time', datetime.datetime.fromtimestamp(self._task.task_end_time))
        )

    # Request the initial start time and update the next completion time attribute
    def _set_initial_start_time(self):
        target_vicon_list = []
        initial_start_time_offset = int(self._agent_configs['initial_start_time_offset'])
        if not self._demo_mode:
            initial_start_time_offset += 30
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start setting the initial start time')
        self.log(10, '', '--------------------------------------------------')
        payload_from_workstation_gateway = self._cpps_task_manager.send_http_request(
            method='GET',
            url='{}/ws/api/workstations'.format(self._agent_configs['WORKSTATION_GATEWAY_URL']),
            request_body={}
        )
        if payload_from_workstation_gateway is not None:
            for workstation in payload_from_workstation_gateway:
                if workstation['active']:
                    target_vicon_list.append(workstation['vicon_id'])
            self.log(20,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Create target vicon list with {} element(s)'.format(len(target_vicon_list)))
        else:
            self._failed = True
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                '    ABORT! Workstation gateway reply with status code {}'.format(
                    payload_from_workstation_gateway.status_code
                )
            )
            self.log(40,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    ABORT! Workstation gateway reply NoneType object'
                     )
        if not self._failed:
            request_body = {
                'robot_id': self._task.robot['robot_id'],
                'klt_id': self._klt_enum[self._task.empty_klt_phyaddr],
                'target': target_vicon_list
            }
            payload_from_fms_gateway = self._cpps_task_manager.send_http_request(
                method='POST',
                url='{}/fms/api/taskrobot/start_time'.format(self._agent_configs['fms_gateway_url']),
                request_body=request_body
            )
            if payload_from_fms_gateway is not None:
                if 'completion_time' in payload_from_fms_gateway:
                    self.log(20,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '    Add {} seconds as offset to completion time from fms'.format(
                                 initial_start_time_offset)
                             )
                    self._next_completion_time = payload_from_fms_gateway['completion_time'] + \
                                                 initial_start_time_offset  # todo: Average time calculation
                    # Update database
                    self._cpps_task_manager.update_states(
                        self._task.task_id,
                        'stage1',
                        '{:>25}: {}'.format('Set initial start time',
                                            datetime.datetime.fromtimestamp(self._next_completion_time))
                    )
                    self._cpps_task_manager.update_states(
                        self._task.task_id,
                        'initial_start_time',
                        self._next_completion_time
                    )
                    self.log(
                        20,
                        'AGENT ID:{:d}'.format(self._agent_id),
                        '    Set initial start time: {}'.format(
                            datetime.datetime.fromtimestamp(self._next_completion_time)
                        )
                    )
                else:
                    self._failed = True
                    # Update database
                    self._cpps_task_manager.update_states(
                        self._task.task_id,
                        'stage1',
                        'Failed to set initial start time! ValueError'
                    )
                    self.log(40,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '    ValueError! Received payload without completion_time key'
                             )
            else:
                self._failed = True
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'stage1',
                    'Failed to set initial start time! No response from fms'
                )
                self.log(40,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '    ABORT! Set initial start time failed by getting fms reply'
                         )

    # Books the best decision
    def _book_labor_process(self,
                            id_task: int,
                            id_labor_process: str,
                            rejects: list,
                            workstation_id: str,
                            employee_id: str,
                            robot_id: str,
                            start_time: float,
                            time_slot_length: float,
                            stage: str
                            ) -> bool:
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start booking labor process')
        self.log(10, '', '--------------------------------------------------')
        self._next_start_time = start_time
        request_body = {
            'decision': {
                'id_task': id_task,
                'id_labor_process': id_labor_process,
                'rejects': rejects,
                'workstation_id': workstation_id,
                'employee_id': employee_id,
                'robot_id': robot_id,
                'start_time': start_time,
                'time_slot_length': time_slot_length
            }
        }
        payload = self._cpps_task_manager.send_http_request(
            method='POST',
            url='{}/ws/api/book'.format(self._agent_configs['workstation_gateway_url']),
            request_body=request_body
        )
        if payload is not None:
            if 'workstation_result' in payload and 'employee_result' in payload and 'picking_result' in payload:
                workstation_result = float(payload['workstation_result'])
                employee_result = float(payload['employee_result'])
                picking_result = float(payload['picking_result'])
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    stage,
                    'Finale Startzeit: {}'.format(datetime.datetime.fromtimestamp(start_time))
                )
                self.log(20,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '{:>25}: {}'.format('final_start_time', datetime.datetime.fromtimestamp(start_time))
                         )
                self.log(20,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '{:>25}: {}'.format('workstation_result', datetime.datetime.fromtimestamp(workstation_result))
                         )
                self.log(20,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '{:>25}: {}'.format('employee_result', datetime.datetime.fromtimestamp(employee_result))
                         )
                self.log(20,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '{:>25}: {}'.format('picking_result', datetime.datetime.fromtimestamp(picking_result))
                         )
                if workstation_result > 0 and employee_result > 0 and picking_result > 0:
                    self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '    Booking SUCCESSFUL')
                    return True
                else:
                    self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '    Booking UNSUCCESSFUL')
                    return False
            else:
                self.log(40,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '    Booking failed, while no result keys defined'
                         )
                return False
        else:
            self._failed = True
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                '    RequestError with NoneType by booking the offer for {}'.format(id_labor_process)
            )
            self.log(40, 'AGENT ID:{:d}'.format(self._agent_id),
                     '    Received empty response data from workstation gateway')
            return False

    def _update_priority_graph(self,
                               best_decision: dict,
                               selected_nodes: list,
                               stage: str
                               ):
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start updating for next node')
        self.log(10, '', '--------------------------------------------------')
        if best_decision and selected_nodes:
            decision = deepcopy(best_decision)
            try:
                operation = decision['offer_from_workstation']['id_labor_process']
                turning_time = self._cpps_task_manager.get_reference_turning_time()[operation]
                review = self._cpps_task_manager.get_reference_review()[operation]
                decision['reference_turning_time'] = turning_time
                decision['reference_review'] = review
            except KeyError:
                self._failed = True
                self.log(40,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '    ABORT! KeyError on setting reference parameter'
                         )
                return
            best_node = None
            selected_id_labor_process = decision['offer_from_workstation']['id_labor_process']
            for node_id in selected_nodes:
                if self._priority_graph[node_id]['operation'] == selected_id_labor_process:
                    best_node = node_id
                    self._priority_graph['start_node'] = best_node
                    self._priority_graph[best_node]['state'] = 1
                    self._priority_graph['finished_nodes'].append(best_node)
                    new_successors = selected_nodes
                    try:
                        new_successors.remove(best_node)
                        self._priority_graph[best_node]['successor'] = \
                            list(set(self._priority_graph[best_node]['successor'] + new_successors))
                    except ValueError:
                        self._failed = True
                        self.log(40,
                                 'AGENT ID:{:d}'.format(self._agent_id),
                                 '    ABORT! Failed to set new successor list for {}'.format(best_node)
                                 )
                        return
                    self.log(20,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '{:>25}: {}'.format('finished_nodes', self._priority_graph['finished_nodes'])
                             )
                    self.log(20,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '{:>25}: {}'.format(
                                 best_node + ' state',
                                 ('finished' if self._priority_graph[best_node]['state'] else 'open'))
                             )
                    self.log(20,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '{:>25}: {}'.format('new_start_node', self._priority_graph['start_node'])
                             )
                    self.log(20,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '{:>25}: {}'.format(best_node + ' successors',
                                                 self._priority_graph[best_node]['successor'])
                             )
                    break
            # Update sequence number
            decision['sequence_number'] = self._priority_graph_index
            self._priority_graph_index += 1
            # Set next completion time
            start_time = decision['start_time']
            skill_time_length = decision['offer_from_workstation']['skill_time']
            self._next_completion_time = start_time + skill_time_length
            self.log(20,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '{:>25}: {}'.format('next_completion_time',
                                         datetime.datetime.fromtimestamp(self._next_completion_time))
                     )
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                stage,
                'Successfully update the priority graph'
            )
            self._cpps_task_manager.update_states(
                self._task.task_id,
                best_node,
                decision
            )
        else:
            self._failed = True
            log_text = ''
            if best_decision is None:
                log_text = log_text + 'selected_nodes'
            if selected_nodes is None:
                log_text = log_text + 'best_decision'
            self.log(20,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    ABORT! Received empty argument(s): {}'.format(log_text)
                     )
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                stage,
                'ABORT updating the priority graph! Received empty argument(s): {}'.format(log_text)
            )

    def wait_for_task_end_time(self,
                               stage: str,
                               target: str
                               ):
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start sleeping process')
        self.log(10, '', '--------------------------------------------------')
        if self._demo_mode:
            self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '    Skip sleeping process. Demo scenario is ACTIVE')
        else:
            self.log(10, 'AGENT ID:{:d}'.format(self._agent_id),
                     '    Run sleeping process. Realtime scenario is ACTIVE')
            time_dif = self._next_completion_time - time.time()
            if time_dif < 20:
                self._failed = True
                self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '    ABORT! Because agent is too late')
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    stage,
                    'ABORT! Because agent is too late'
                )
            else:
                self.log(10, 'AGENT ID:{:d}'.format(self._agent_id),
                         '    Sleep for {:0.0f} seconds ...'.format(time_dif))
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    stage,
                    '{} Sleep for {} seconds ...'.format(
                        time_dif,
                        self._priority_graph[self._priority_graph['start_node']]['operation']
                    )
                )
                time.sleep(time_dif)
            self._cpps_task_manager.send_http_request(
                method='POST',
                url='{}/fms/api/robot/drive_to_workstation'.format(self._agent_configs['fms_gateway_url']),
                request_body={
                    'robot_id': self._task.robot['robot_id'],
                    'target': '/vicon/{}/{}'.format(target, target)
                }
            )
            time_dif = self._next_start_time - time.time()
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Wait {:0.0f} seconds for next start_time ...'.format(time_dif)
                     )
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                stage,
                '{:0.0f} Wait {} seconds for next start_time ... ...'.format(
                    time_dif,
                    self._priority_graph[self._priority_graph['start_node']]['operation']
                )
            )
            time.sleep(time_dif)

    def reset_to_default(self, workstation_vicon_id: str):
        # Update database and log
        self._cpps_task_manager.update_states(self._task.task_id, 'stage2', 'Reset to default...')
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Reset to default')
        # Reset robot
        klt_arriving_time = None
        request_body = {
            'robot_id': self._task.robot['robot_id'],
            'demo_mode': str(self._demo_mode),
            'task_end_time': self._next_completion_time,
            'workstation_vicon_id': workstation_vicon_id
        }
        url = '{}/fms/api/taskrobot/unblock'.format(self._agent_configs['fms_gateway_url'])
        payload = self._cpps_task_manager.send_http_request(
            url=url,
            method='POST',
            request_body=request_body
        )
        if payload is not None and 'SUCCESS' in payload:
            klt_arriving_time = payload['SUCCESS']['klt_arriving_home']
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'taskrobot_arriving_home',
                float(payload['SUCCESS']['taskrobot_arriving_home'])
            )
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage2',
                'Reset robot (ID: {}) SUCCESSFULLY'.format(self._task.robot['robot_id'][18:])
            )
            robot_status = bool(payload['SUCCESS']['robot_status'])
            if robot_status:
                text = 'FAILED'
            else:
                text = 'SUCCESSFULLY'
            self.log(20,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Reset robot (ID: {}) {}'.format(self._task.robot['robot_id'], text)
                     )
            self.log(20,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '{:>25}: {:0.2f} sec'.format('taskrobot_arriving_home',
                                                  round(float(payload['SUCCESS']['taskrobot_arriving_home']), 2)
                                                  )
                     )
        else:
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage2',
                'Reset robot (ID: {}) to default FAILED!!!'.format(self._task.empty_klt_phyaddr)
            )
            self.log(40,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Reset robot (ID: {}) to default FAILED!!!'.format(self._task.empty_klt_phyaddr)
                     )
        if self._virtual_phynode_mode:
            self._cpps_task_manager.restore_free_klt(self._task.empty_klt_phyaddr)
            return
        else:
            self.restore_phyaddr()
        if self._demo_mode:
            self.log(10, 'AGENT ID:{:d}'.format(self._agent_id),
                     '    Skip waiting for arrival. Demo scenario is ACTIVE')
        else:
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage2',
                '    Wait {} second(s) for klt arrival ...'.format(klt_arriving_time)
            )
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Wait {} second(s) for klt arrival ...'.format(klt_arriving_time)
                     )
            time.sleep(klt_arriving_time)
            klt = self._klt_enum[self._task.empty_klt_phyaddr]
            attempts = 0
            max_attempts = self._agent_configs['max_sleep_time_klt_reset']
            # Check if robot arrived at klt home position
            while True:
                distance = self.get_distance(destination_one=klt, destination_two='home_position_{}'.format(klt))
                if attempts <= max_attempts:
                    if distance is not None and distance < 0.3:
                        break
                    else:
                        sleep_time = 2
                        self.log(10,
                                 'AGENT ID:{:d}'.format(self._agent_id),
                                 '    Wait {} second(s) for klt arrival ...'.format(sleep_time)
                                 )
                    time.sleep(sleep_time)
                else:
                    self._failed = True
                    # Update database
                    self._cpps_task_manager.update_states(
                        self._task.task_id,
                        'stage2',
                        'ABORT! Failed to reset the phynode (ADDR: {:d}) while not arriving'.format(
                            self._task.empty_klt_phyaddr
                        )
                    )
                    self.log(40,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '    Failed to reset the phynode (ADDR: {:d}) while not arriving'.format(
                                 self._task.empty_klt_phyaddr
                             )
                             )
                    return
                attempts += 1

    def restore_phyaddr(self):
        # Reset phynode
        request_body = {
            'addr': self._task.empty_klt_phyaddr,
            'buttonId': 1
        }
        url = '{}/gateway/BUTN'.format(self._agent_configs['phynode_gateway_url'])
        payload = self._cpps_task_manager.send_http_request(
            url=url,
            method='POST',
            request_body=request_body
        )
        if payload is not None and 'SUCCESS' in payload:
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '... Reset phynode (ADDR: {}) SUCCESSFULLY'.format(self._task.empty_klt_phyaddr)
                     )
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage2',
                'Reset phynode (ADDR: {}) SUCCESSFULLY'.format(self._task.empty_klt_phyaddr)
            )
        else:
            self.log(10,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '... Reset phynode (ADDR: {}) FAILED!!!'.format(self._task.empty_klt_phyaddr)
                     )
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage2',
                'Reset phynode (ADDR: {}) FAILED!!!'.format(self._task.empty_klt_phyaddr)
            )

    def stage_1(self):
        self.log(10,
                 'AGENT ID:{:d}'.format(self._agent_id),
                 '>>> Start generate new cycle id ...'
                 )
        self.log(10, '', '--------------------------------------------------')
        id_cycle = self._cpps_task_manager.random_generator()
        self.log(20,
                 'AGENT ID:{:d}'.format(self._agent_id),
                 '{:>25}: {}'.format('id_cycle', id_cycle)
                 )
        start_time = time.time()
        selected_nodes = [self._priority_graph['start_node']]
        rejects = []
        offers = {}
        best_decision = {}
        id_labor_process = self._priority_graph[self._priority_graph['start_node']]['operation']
        # Update database and log
        self._cpps_task_manager.update_states(self._task.task_id, 'stage1', 'Start stage 1 process..')
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> S t a r t   w i t h   s t a g e   1')
        # Find free klt
        if not self._failed:
            self._get_phynode()
        # Reserve phynode
        if not self._failed:
            self._set_phynode(stage='stage1')
        # Request to fms gateway for initial start time
        if not self._failed:
            self._set_initial_start_time()
        # Calculate task end time
        if not self._failed:
            self._set_task_end_time()
        # Request to workstation gateway for initial offer
        if not self._failed:
            self._cpps_task_manager.lock.acquire()
            offers = self._get_offer(id_cycle=id_cycle,
                                     id_labor_process=id_labor_process,
                                     completion_time=self._next_completion_time,
                                     stage='stage1'
                                     )
        # Find best decision
        if not self._failed:
            best_decision = self._decision_finding(offers=offers, stage='stage1')
        # Create reject list without best decision
        if not self._failed:
            self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start updating reject list')
            self.log(10, '', '--------------------------------------------------')
            for key in offers:
                if best_decision['workstation_id'] != key:
                    self._cpps_task_manager.mqtt_publish(offers[key]['offer_from_workstation']['target'], 60,
                                                         '#00FF00', 1, 1.2, 'none', 'false')
                    rejects.append((offers[key]['offer_from_workstation']['id_labor_process'], key))
            self.log(20,
                     'AGENT ID:{:d}'.format(self._agent_id),
                     '    Create reject list: {}'.format(rejects)
                     )
        # Book the best decision
        if not self._failed:
            self._book_labor_process(
                id_task=self._task.task_id,
                id_labor_process=id_labor_process,
                rejects=rejects,
                workstation_id=best_decision['workstation_id'],
                employee_id=best_decision['offer_from_employee']['employee_id'],
                robot_id=best_decision['offer_from_picking']['robot_id'],
                start_time=best_decision['start_time'],
                time_slot_length=best_decision['offer_from_workstation']['skill_time'],
                stage='stage1'
            )
            self._cpps_task_manager.lock.release()
        # Start sleep process
        if not self._failed:
            self.wait_for_task_end_time(stage='stage1', target=best_decision['offer_from_workstation']['target'])
        # Update priority graph for next step
        if not self._failed:
            self._update_priority_graph(best_decision=best_decision,
                                        selected_nodes=selected_nodes,
                                        stage='stage1')
        end_time = time.time()
        if not self._failed:
            # Update database and log
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                'Finished stage 1 after {:0.0f} second(s)'.format(end_time - start_time)
            )
        else:
            if self._cpps_task_manager.lock.locked():
                self._cpps_task_manager.lock.release()
        self.log(10,
                 'AGENT ID:{:d}'.format(self._agent_id),
                 '<<< E n d   w i t h   s t a g e   1   a f t e r   {:0.0f}   s e c o n d s '.format(
                     end_time - start_time)
                 )

    def stage_2(self):
        start_time = time.time()
        # Update database and log
        self._cpps_task_manager.update_states(self._task.task_id, 'stage2', 'Start stage 2 process..')
        self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> S t a r t   w i t h   s t a g e   2')
        while not self._is_finished():
            selected_nodes = []
            rejects = []
            offers = {}
            best_offer = {}
            if not self._failed and not self._block:
                self._cpps_task_manager.lock.acquire()
                self._cpps_task_manager.mqtt_publish(self._klt_enum[self._task.empty_klt_phyaddr], 60,
                                                     'magenta', 0.9, 2.5, 'none', 'true')
                self.log(10,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '>>> Start generate new cycle id ...'
                         )
                self.log(10, '', '--------------------------------------------------')
                id_cycle = self._cpps_task_manager.random_generator()
                self.log(20,
                         'AGENT ID:{:d}'.format(self._agent_id),
                         '{:>25}: {}'.format('id_cycle', id_cycle)
                         )
                for node in self._priority_graph[self._priority_graph['start_node']]['successor']:
                    self.log(10,
                             'AGENT ID:{:d}'.format(self._agent_id),
                             '>>> Start calculate node {} with cycle id {}'.format(
                                 self._priority_graph[node]['node_id'], id_cycle)
                             )
                    self.log(10, '', '--------------------------------------------------')
                    id_labor_process = self._priority_graph[node]['operation']
                    selected_nodes.append(self._priority_graph[node]['node_id'])
                    precondition = True
                    if len(self._priority_graph[node]['preconditions']) > 0:
                        for key in self._priority_graph[node]['preconditions']:
                            log_text = ''
                            result = int(self._priority_graph[key]['state'])
                            if result == 1:
                                log_text = 'SUCCESSFUL'
                            elif result == 0:
                                log_text = 'FAILED'
                                precondition = False
                            self.log(20,
                                     'AGENT ID:{:d}'.format(self._agent_id),
                                     '{:>25}: {}'.format('precondition {}'.format(key), log_text)
                                     )
                    if precondition:
                        # Request to workstation gateway for initial offer
                        if not self._failed:
                            received_offer = self._get_offer(id_cycle=id_cycle,
                                                             id_labor_process=id_labor_process,
                                                             completion_time=self._next_completion_time,
                                                             stage='stage2'
                                                             )
                            if received_offer:
                                for key in received_offer:
                                    offer = received_offer[key]
                                    rejects.append(
                                        (offer['offer_from_workstation']['id_labor_process'],
                                         offer['offer_from_workstation']['workstation_id']
                                         )
                                    )
                                    offers['{}_{}'.format(id_labor_process, key)] = offer
                    else:
                        self.log(30,
                                 'AGENT ID:{:d}'.format(self._agent_id, node),
                                 '    Failed precondition check'
                                 )
                # Find best decision
                if not self._failed:
                    best_offer = self._decision_finding(offers=offers, stage='stage2')
                if not self._failed:
                    # Laser show
                    for key in offers:
                        if offers[key]['offer_from_workstation']['target'] != \
                                best_offer['offer_from_workstation']['target']:
                            self._cpps_task_manager.mqtt_publish(offers[key]['offer_from_workstation']['target'], 60,
                                                                 '#00FF00', 1, 1.2, 'none', 'false')
                # Update reject list without best decision
                if not self._failed:
                    self.log(10, 'AGENT ID:{:d}'.format(self._agent_id), '>>> Start updating reject list')
                    self.log(10, '', '--------------------------------------------------')
                    if rejects:
                        for reject in rejects:
                            if reject[0] == best_offer['offer_from_workstation']['id_labor_process'] and \
                                    reject[1] == best_offer['offer_from_workstation']['workstation_id']:
                                rejects.remove(reject)
                        self.log(20,
                                 'AGENT ID:{:d}'.format(self._agent_id),
                                 '    Create reject list: {}'.format(rejects)
                                 )
                    else:
                        self._failed = True
                        self.log(40, 'AGENT ID:{:d}'.format(self._agent_id), '    ABORT! Reject list is empty')
                # Book the best decision
                if not self._failed:
                    # print(json.dumps(best_decision, indent=3))
                    self._book_labor_process(
                        id_task=self._task.task_id,
                        id_labor_process=best_offer['offer_from_workstation']['id_labor_process'],
                        rejects=rejects,
                        workstation_id=best_offer['workstation_id'],
                        employee_id=best_offer['offer_from_employee']['employee_id'],
                        robot_id=best_offer['offer_from_picking']['robot_id'],
                        start_time=best_offer['start_time'],
                        time_slot_length=best_offer['offer_from_workstation']['skill_time'],
                        stage='stage2'
                    )
                    self._cpps_task_manager.lock.release()
                # Start sleep process
                if not self._failed:
                    self.wait_for_task_end_time(stage='stage2',
                                                target=best_offer['offer_from_workstation']['target'])
                # Update priority graph for next step
                if not self._failed:
                    self._update_priority_graph(best_decision=best_offer,
                                                selected_nodes=selected_nodes,
                                                stage='stage2')
                else:
                    self._cpps_task_manager.lock.release()
                if self._is_finished():
                    # Reset to default (unblock taskrobot, reset phynode
                    self.reset_to_default(workstation_vicon_id=best_offer['offer_from_workstation']['target'])
        # Track end time
        end_time = time.time()
        if not self._failed:
            # Update database and log
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage2',
                'Finished stage 2 after {:0.0f} second(s)'.format(end_time - start_time)
            )
        self.log(10,
                 'AGENT ID:{:d}'.format(self._agent_id),
                 '<<< E n d   w i t h   s t a g e   2   a f t e r   {:0.0f}   s e c o n d s '.format(
                     end_time - start_time)
                 )

    def get_distance(self, destination_one, destination_two):
        position_available = True
        result = None
        destination_one_coordinates = None
        destination_two_coordinates = None
        try:
            vicon_id = 'vicon/{}/{}'.format(destination_one, destination_one)
            destination_one_coordinates = numpy.array([
                self._positions[vicon_id]['translation']['x'],
                self._positions[vicon_id]['translation']['y']
            ])
            self.log(10,
                     'DISTANCE',
                     '{:>25}: {}'.format('{} coordinates'.format(destination_one), str(destination_one_coordinates))
                     )
        except KeyError:
            position_available = False
            self.log(40,
                     'DISTANCE',
                     '    KeyError! No position for {} found'.format(destination_one)
                     )
        try:
            vicon_id = 'vicon/{}/{}'.format(destination_two, destination_two)
            destination_two_coordinates = numpy.array([
                self._positions[vicon_id]['translation']['x'],
                self._positions[vicon_id]['translation']['y']
            ])
            self.log(10,
                     'DISTANCE',
                     '{:>25}: {}'.format('{} coordinates'.format(destination_two), str(destination_two_coordinates))
                     )
        except KeyError:
            position_available = False
            self.log(40,
                     'DISTANCE',
                     '    KeyError! No position for {} found'.format(destination_two)
                     )
        if position_available:
            result = numpy.linalg.norm(destination_one_coordinates - destination_two_coordinates)
            self.log(20,
                     'DISTANCE',
                     '{:>25}: {:0.2f}'.format('distance', result)
                     )
        return result
