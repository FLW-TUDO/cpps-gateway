#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import sys
import pickle
import json
import numpy
import requests
import time
import math
import threading
import datetime
import paho.mqtt.client as mqtt

from copy import deepcopy
from cpps_workstation import Workstation
from cpps_workstation import Entry

'''
##################################################

Required files

'''

directory = 'logfiles'
filename = 'workstation_logfile_{}.log'.format(time.strftime('%Y.%m.%d_%H:%M:%S', time.localtime()))
if not os.path.isdir(directory):
    os.mkdir(directory)

fh = logging.FileHandler(directory + '/' + filename)
fh.setLevel(logging.DEBUG)
fm = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s')
fh.setFormatter(fm)
logger = logging.getLogger('workstation')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)


def log(level, topic, message, print_out=True):
    log_msg = '[{}]: {}'.format('{:<20}'.format(topic), message)
    if level == 10:
        logger.debug(log_msg)
    elif level == 20:
        logger.info(log_msg)
    elif level == 30:
        logger.warning(log_msg)
    elif level == 40:
        logger.error(log_msg)
    elif level == 50:
        logger.critical(log_msg)
    else:
        logger.debug(log_msg)

    if print_out:
        print('[{}]: {}'.format('{:<20}'.format(topic), message))


'''
##################################################
'''


class WorkstationGateway(threading.Thread):
    def __init__(self, config_parser, restore: bool, ws_configuration: str):
        super().__init__()
        self._workstation_configs = config_parser['DEFAULT']
        self._mqtt_client = mqtt.Client('WorkstationGateway')
        self._workstations = []
        self._positions = {}
        self._delta = float(self._workstation_configs['delta'])
        self._initialize(restore, ws_configuration)

    def _initialize(self, restore: bool, ws_configuration: str):
        self.mqtt_connect()
        time.sleep(0.5)
        if restore and os.path.isfile(self._workstation_configs['ser_file_name']):
            try:
                binary_file = open(self._workstation_configs['ser_file_name'], 'rb')
                self._workstations = pickle.load(binary_file)
                binary_file.close()
                log(
                    20,
                    'WORKSTATION_GATEWAY',
                    '... Workstations restored!'
                )
            except IOError as e:
                print(e)
        else:
            try:
                workstations = json.loads(self._workstation_configs[ws_configuration])
                for workstation in workstations:
                    # print(json.dumps(value, indent=4, sort_keys=True))
                    value = list(workstation.values())[0]
                    # print(value)
                    workstation_id = str(value['workstation_id'])
                    vicon_id = str(value['vicon_id'])
                    skills = list(value['skills'])
                    costs = float(value['costs'])
                    active = bool(value['active'])
                    self._workstations.append(
                        Workstation(
                            workstation_id=workstation_id,
                            vicon_id=vicon_id,
                            skills=skills,
                            costs=costs,
                            active=active
                        )
                    )
            except KeyError:
                log(40, 'WORKSTATION_GATEWAY', '    KeyError! No configuration for {} found'.format(ws_configuration))
                sys.exit(2)
            log(20,
                'WORKSTATION_GATEWAY',
                '... Load settings from config file'
                )
            self.save_workstations()
        time.sleep(1)
        self.check_vicon_connection()
        log(
            20,
            'WORKSTATION_GATEWAY',
            '... Initialization completed\n'
        )
        self.print_workstation_list()
        time.sleep(2)
        # print(json.dumps(self._positions, indent=4, sort_keys=True))

    def check_vicon_connection(self):
        for workstation in self._workstations:
            vicon_id = workstation.get_vicon_id()
            if '/vicon/{}/{}'.format(vicon_id, vicon_id) in self._positions:
                workstation.activate()
            else:
                workstation.deactivate()

    def add_workstation(self,
                        workstation_id: str,
                        vicon_id: str,
                        skills: list,
                        costs: float,
                        active: bool
                        ) -> bool:
        for ws in self._workstations:
            if ws.get_workstation_id() == workstation_id:
                return False
        self._workstations.append(
            Workstation(
                workstation_id=workstation_id,
                vicon_id=vicon_id,
                skills=skills,
                costs=costs,
                active=active
            )
        )
        self.save_workstations()
        return True

    def change_workstation_skills(self, workstation_id: str, new_skills: list) -> bool:
        for ws in self._workstations:
            if ws.get_workstation_id() == workstation_id:
                self.save_workstations()
                return ws.change_skills(new_skills)
        return False

    def delete_workstation(self, workstation_id: str) -> bool:
        for index, ws in enumerate(self._workstations):
            if ws.get_workstation_id() == workstation_id:
                self._workstations.pop(index)
                self.save_workstations()
                return True
            else:
                return False

    def get_workstation(self, workstation_id: str) -> Workstation:
        for workstation in self._workstations:
            if workstation.get_workstation_id() == workstation_id:
                return workstation
        return Workstation()

    def get_workstations(self) -> list:
        workstations = []
        for workstation in self._workstations:
            workstations.append(workstation.attributes_to_dict())
        return workstations

    def mqtt_connect(self):
        host = str(self._workstation_configs['mqtt_host'])
        port = int(self._workstation_configs['mqtt_port'])
        topic_of_positions = str(self._workstation_configs['mqtt_topic_position'])
        self._mqtt_client.message_callback_add(
            topic_of_positions,
            self.set_positions
        )
        rc = self._mqtt_client.connect(host, port)
        if rc == 0:
            log(
                20,
                'MQTT_CLIENT',
                '... Connected to broker: {} on port: {}'.format(
                    host,
                    port
                )
            )
            log(
                20,
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

    def get_offer(self,
                  alpha_time: float,
                  alpha_costs: float,
                  completion_time: float,
                  id_cycle: str,
                  id_task: int,
                  id_labor_process: str,
                  robot: dict,
                  components: dict,
                  last_workstation_id: str
                  ) -> dict:
        """
        :param last_workstation_id:
        :param id_cycle: (str)
        :param components: (dict)
        :param alpha_time: (float)
        :param alpha_costs: (float)
        :param completion_time: (float)
        :param id_task: (int)
        :param id_labor_process: (str)
        :param robot: (dict)
            id_robot': (str)
            average_speed': (float),
            operating_cost': (float)
        :return: (dict)
            'ws_id': {
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
            }, ...

        """
        log(10, 'OFFER ID:{}'.format(str(id_task)), '>>> Start offer...')
        log(10, '', '--------------------------------------------------')
        offers = {}
        offer = {}
        if last_workstation_id == '':
            last_workstation_vicon_id = ''
        else:
            last_workstation_vicon_id = self.get_workstation(last_workstation_id).get_vicon_id()
        # Ask all workstations for an offer
        for workstation in self._workstations:
            offer = {}
            if workstation.has_skill(id_labor_process):
                desired_availability_date = self.reserve_workstation(id_cycle=id_cycle,
                                                                     id_task=id_task,
                                                                     id_labor_process=id_labor_process,
                                                                     completion_time=completion_time,
                                                                     robot=robot,
                                                                     workstation=workstation,
                                                                     last_workstation_vicon_id=last_workstation_vicon_id
                                                                     )
                desired_availability_date['alpha_time'] = alpha_time
                desired_availability_date['alpha_costs'] = alpha_costs
                desired_availability_date['components'] = components
                if 'desired_availability_date' in desired_availability_date:
                    self.mqtt_publish(workstation.get_vicon_id(), 60, 'magenta', 1.1, 2.5, 'none', 'true')
                    try:
                        request_data = {
                            'task': desired_availability_date
                        }
                        payload_from_employee = self.send_http_request(
                            url='{}/emp/api/offer'.format(self._workstation_configs['employee_gateway_url']),
                            method='POST',
                            request_body=request_data
                        )
                        log(10, 'OFFER ID:{}'.format(str(id_task)), '    Received response from employee gateway ...')
                        payload_from_picking = self.send_http_request(
                            url='{}/pck/api/offer'.format(self._workstation_configs['picking_gateway_url']),
                            method='POST',
                            request_body=request_data
                        )
                        log(10, 'OFFER ID:{}'.format(str(id_task)), '    Received response from picking gateway ...')
                    except requests.exceptions.RequestException as err:
                        log(40, 'OFFER ID:{}'.format(str(id_task)), '    Request error: {}'.format(str(err)))
                        break
                    if payload_from_employee is None:
                        log(30,
                            'OFFER ID:{}'.format(str(id_task)),
                            '    ATTENTION! Received no offer from employee gateway'
                            )
                    if payload_from_picking is None:
                        log(30,
                            'OFFER ID:{}'.format(str(id_task)),
                            '    ATTENTION! Received no offer from picking gateway'
                            )
                    picking_availability_date = payload_from_picking
                    employee_availability_date = payload_from_employee
                    offer = {
                        'offer_from_workstation': desired_availability_date,
                        'offer_from_picking': picking_availability_date,
                        'offer_from_employee': employee_availability_date
                    }
                    result = self.calculate_valuation_result(alpha_time=alpha_time,
                                                             alpha_costs=alpha_costs,
                                                             offer=offer
                                                             )
                    offers['{}'.format(workstation.get_workstation_id())] = result
            time.sleep(0.5)
        log(10, 'OFFER ID:{}'.format(str(id_task)), '    Reply {} offer(s)'.format(len(offers.keys())))
        return offers

    def reserve_workstation(self,
                            id_cycle: str,
                            id_task: int,
                            id_labor_process: str,
                            completion_time: float,
                            robot: dict,
                            workstation: Workstation,
                            last_workstation_vicon_id: str
                            ) -> dict:
        """
        :param last_workstation_vicon_id:
        :param id_cycle:
        :param id_task:
        :param id_labor_process:
        :param completion_time:
        :param robot:
            average_vel: (float)
            operation_costs: (float)
            robot_id: (str)
        :param workstation:
        :return: (dict)
            buffer_time: (float)
            completion_time: (float)
            costs_ial_transport: (float)
            costs_workstation: (float)
            desired_availability_date: (float)
            id_task: (int)
            id_labor_process: (str)
            skill_time: (float)
            time_slot_length: (float)
            target: (str)
            workstation_id: (str)
        """
        robot_coordinates = []
        workstation_coordinates = []
        position_available = False
        desired_availability_date = {}
        log(10,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '>>> Starting reservation ...'
            )
        log(10, '', '--------------------------------------------------')
        log(20,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '{:>25}: {}'.format('id_cycle', id_cycle)
            )
        log(20,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '{:>25}: {}'.format('id_task', id_task)
            )
        log(20,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '{:>25}: {}'.format('id_labor_process', id_labor_process)
            )
        log(20,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '{:>25}: {}'.format('completion_time', datetime.datetime.fromtimestamp(completion_time))
            )
        log(20,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '{:>25}: {}'.format('robot_id', robot['robot_id'])
            )
        robot_average_vel = float(robot['average_vel'])
        log(20,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '{:>25}: {}'.format('robot_average_vel', robot_average_vel)
            )
        robot_operation_costs = float(robot['operation_costs'])
        log(20,
            'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
            '{:>25}: {} EUR'.format('robot_operation_costs', robot_operation_costs)
            )
        if last_workstation_vicon_id == '':
            vicon_id = '/vicon/{}/{}'.format(robot['robot_id'], robot['robot_id'])
        else:
            vicon_id = '/vicon/{}/{}'.format(last_workstation_vicon_id, last_workstation_vicon_id)
        try:
            robot_coordinates = numpy.array([
                self._positions[vicon_id]['translation']['x'],
                self._positions[vicon_id]['translation']['y']
            ])
            position_available = True
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {}'.format('robot_coordinates', str(robot_coordinates))
                )
        except KeyError:
            position_available = False
            log(40,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '    KeyError! No position for {}'.format(robot['robot_id'])
                )
        vicon_id = '/vicon/{}/{}'.format(workstation.get_vicon_id(), workstation.get_vicon_id())
        try:
            workstation_coordinates = numpy.array([
                self._positions[vicon_id]['translation']['x'],
                self._positions[vicon_id]['translation']['y']
            ])
            position_available = True
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {}'.format('workstation_coordinates', str(workstation_coordinates))
                )
        except KeyError:
            position_available = False
            log(40,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '    KeyError! No position for {} found'.format(vicon_id)
                )
        if position_available:
            distance = self.get_distance(
                position_of_robot=robot_coordinates,
                position_of_workstation=workstation_coordinates
            )
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {:0.2f} m'.format('distance', distance)
                )
            if distance < 0.5:
                desired_start_time = completion_time + 5
            else:
                desired_start_time = completion_time + (distance / robot_average_vel) * 2
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {}'.format('desired_start_time', datetime.datetime.fromtimestamp(desired_start_time))
                )
            costs_ial_transport = distance * robot_operation_costs
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {:.2f} EUR'.format('costs_ial_transport', costs_ial_transport)
                )
            desired_availability_date = workstation.reservation(id_cycle=id_cycle,
                                                                id_task=id_task,
                                                                id_labor_process=id_labor_process,
                                                                desired_start_time=desired_start_time,
                                                                desired_skill=id_labor_process,
                                                                delta=self._delta
                                                                )
            desired_availability_date['costs_ial_transport'] = costs_ial_transport
            desired_availability_date['completion_time'] = completion_time
            desired_availability_date['target'] = workstation.get_vicon_id()
            desired_availability_date['workstation_id'] = workstation.get_workstation_id()
            desired_availability_date['desired_start_time'] = desired_start_time
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {} sec'.format('buffer_time', desired_availability_date['buffer_time'])
                )
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {}'.format('costs_workstation', desired_availability_date['costs_workstation'])
                )
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {}'.format(
                    'desired_availability_date',
                    datetime.datetime.fromtimestamp(desired_availability_date['desired_availability_date']))
                )
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {} sec'.format('time_slot_length', desired_availability_date['time_slot_length'])
                )
            log(20,
                'OFFER ID:{} | {}'.format(str(id_task), workstation.get_workstation_id()),
                '{:>25}: {} sec'.format('skill_time', desired_availability_date['skill_time'])
                )
        return desired_availability_date

    def book_workstation(self,
                         id_task: int,
                         id_labor_process: str,
                         rejects: list,
                         workstation_id: str,
                         employee_id: str,
                         robot_id: str,
                         start_time: float,
                         time_slot_length: float
                         ):
        workstation_result = False
        picking_result = 0
        employee_result = 0
        response_from_employee = None
        response_from_picking = None
        payload_from_employee = None
        payload_from_picking = None
        log(10, 'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process), '>>> Start booking ...')
        log(10, '', '--------------------------------------------------')
        if rejects:
            for workstation in self._workstations:
                # log(10, 'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process), '
                # {:>25}: {}'.format(workstation.get_workstation_id(), workstation.get_calendar()))
                for reject in rejects:
                    if workstation.get_workstation_id() == reject[1]:
                        count = workstation.reject(id_task=id_task, id_labor_process=reject[0])
                        log(20,
                            'WORKSTATION ID:{}'.format(str(workstation.get_workstation_id())),
                            '    Step 1: reject {} time slot(s) for {}'.format(count, reject)
                            )
        tuple_for_log = [id_labor_process, workstation_id]
        workstation = self.get_workstation(workstation_id)
        if workstation.has_skill(id_labor_process):
            if workstation.get_workstation_id() == workstation_id:
                book_result = workstation.book(id_task=id_task,
                                               id_labor_process=id_labor_process,
                                               start_time=start_time
                                               )
                if book_result is not None:
                    workstation_result = book_result.start_time
                else:
                    workstation_result = 0
                if workstation_result > 0:
                    log(20,
                        'WORKSTATION ID:{}'.format(str(workstation.get_workstation_id())),
                        '    Step 2: update time slot for {}:'.format(tuple_for_log)
                        )
                    log(20,
                        'WORKSTATION ID:{}'.format(str(workstation.get_workstation_id())),
                        '{:>25}: {}'.format('start_time', datetime.datetime.fromtimestamp(book_result.start_time))
                        )
                    log(20,
                        'WORKSTATION ID:{}'.format(str(workstation.get_workstation_id())),
                        '{:>25}: {}'.format('time_slot_length', book_result.time_slot_length)
                        )
                    log(20,
                        'WORKSTATION ID:{}'.format(str(workstation.get_workstation_id())),
                        '{:>25}: {}'.format('end_time', datetime.datetime.fromtimestamp(book_result.start_time + book_result.time_slot_length))
                        )
                else:
                    log(30,
                        'WORKSTATION ID:{}'.format(str(workstation.get_workstation_id())),
                        '    Step 2: no time slot for {} found, but it should be one'.format(id_labor_process)
                        )
        # Send booking command to fms and employee gateway
        # Create modified rejects for fms
        rejects_for_fms = deepcopy(rejects)
        for reject in rejects_for_fms:
            ws = self.get_workstation(reject[1])
            reject[1] = ws.get_vicon_id()
        ws = self.get_workstation(workstation_id)
        request_data = {
            'decision': {
                'id_task': id_task,
                'id_labor_process': id_labor_process,
                'rejects': rejects,
                'rejects_for_fms': rejects_for_fms,
                'workstation_id': workstation_id,
                'workstation_vicon_id': ws.get_vicon_id(),
                'employee_id': employee_id,
                'robot_id': robot_id,
                'start_time': start_time,
                'time_slot_length': time_slot_length
            }
        }
        try:
            log(10,
                'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process),
                '    Send request to employee gateway ...'
                )
            response_from_employee = requests.post(
                url='{}/emp/api/book'.format(self._workstation_configs['employee_gateway_url']),
                data=json.dumps(request_data))
            log(10,
                'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process),
                '    Received response from employee gateway ...'
                )
            log(10,
                'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process),
                '    Send request to picking gateway ...'
                )
            response_from_picking = requests.post(
                url='{}/pck/api/book'.format(self._workstation_configs['picking_gateway_url']),
                data=json.dumps(request_data))
            log(10,
                'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process),
                '    Received response from picking gateway ...'
                )
            time.sleep(0.5)
        except requests.exceptions.RequestException as err:
            log(40,
                'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process),
                '    Request error: {}'.format(str(err))
                )
        if response_from_employee.status_code == 200 and response_from_picking.status_code == 200:
            if response_from_employee is not None and response_from_picking is not None:
                try:
                    payload_from_employee = dict(response_from_employee.json())
                    payload_from_picking = dict(response_from_picking.json())
                except ValueError as err:
                    log(40, 'OFFER ID:{}'.format(str(id_task)), '    Value error: {}'.format(str(err)))
                if 'SUCCESS' in payload_from_employee:
                    employee_result = float(payload_from_employee['SUCCESS'])
                if 'SUCCESS' in payload_from_picking:
                    picking_result = float(payload_from_picking['SUCCESS'])
        log(10, 'BOOK ID:{} | OP: {}'.format(str(id_task), id_labor_process), '>>> Finished booking ...')
        return {
            'workstation_result': workstation_result,
            'employee_result': employee_result,
            'picking_result': picking_result
        }

    def save_workstations(self):
        try:
            binary_file = open(self._workstation_configs['ser_file_name'], 'wb')
            pickle.dump(self._workstations, binary_file)
            binary_file.close()
            log(20,
                'WORKSTATION_GATEWAY',
                '... Workstations saved!'
                )
        except IOError as e:
            print(e)

    def set_positions(self, client, userdata, message):
        payload = message.payload
        data = json.loads(payload.decode())
        self._positions['/{}'.format(data['child_frame_id'])] = {
            'translation': data['transform']['translation']
        }

    def export_calendar(self) -> str:
        result = ''
        if self._workstations:
            for workstation in self._workstations:
                result += 'workstation {}<br>'.format(workstation.get_workstation_id())
                result += 'desired_availability_date:<br>'
                calendar = workstation.get_calendar()
                if calendar:
                    for entry in calendar:
                        text = str(entry['desired_availability_date'])
                        result += '{}<br>'.format(text.replace('.', ','))
                    result += 'time_slot_length:<br>'
                    calendar = workstation.get_calendar()
                    for entry in calendar:
                        text = str(entry['time_slot_length'])
                        result += '{}<br>'.format(text.replace('.', ','))
                    result += '<br><br>'
                else:
                    result += 'No calendar entry found<br><br>'#
        else:
            result += 'No workstations initialized'
        return result

    def print_workstation_list(self):
        print('\n[{:<20}]: {}\n\n{:<15} {:<15} {}'.format('PRINT LIST', '...', 'workstation_id', 'active',
                                                          'skills {operation: time}'))
        print('--------------- --------------- ------------------------')
        if len(self._workstations) > 0:
            for ws in self._workstations:
                skills = []
                for skill in ws.get_skills():
                    skills.append(
                        {
                            '{}'.format(skill['skill']):'{:3d}'.format(int(skill['time']))
                        }
                    )
                print('{:15} {:15} {}'.format(ws.get_workstation_id(), str(ws.is_active()), skills))
        print('\n[END]\n')

    '''
        Calculates the distance of the order agent to the workstation
        position_of_robot: numpy.array((x,y,z))
        position_of_robot: numpy.array((x, y, z))
        '''

    @staticmethod
    def calculate_valuation_result(alpha_time: float,
                                   alpha_costs: float,
                                   offer: dict
                                   ) -> dict:
        """
        :param alpha_time:
        :param alpha_costs:
        :param offer:
        :return:
            offer_from_workstation:
            offer_from_picking:
            offer_from_employee:
            start_time:
            completion_time_j:
            throughput_time_j:
            throughput_time_j_normalized:
            total_costs:
            total_costs_normalized:
            valuation_result:
        """
        id_task = offer['offer_from_workstation']['id_task']
        if offer['offer_from_employee'] is not None and offer['offer_from_picking'] is not None:
            harmonized = True
            log(10, 'OFFER ID:{}'.format(str(id_task)), '>>> Start calculate valuation result ...')
            log(10, '', '--------------------------------------------------')
            if offer and \
                    'offer_from_workstation' in offer and \
                    'offer_from_picking' in offer and \
                    'offer_from_employee' in offer:
                log(20, 'OFFER ID:{}'.format(str(id_task)), '    Offer from workstation ...')
                print(json.dumps(offer['offer_from_workstation'], indent=2))
                log(20, 'OFFER ID:{}'.format(str(id_task)), '    Offer from picking ...')
                print(json.dumps(offer['offer_from_picking'], indent=2))
                log(20, 'OFFER ID:{}'.format(str(id_task)), '    Offer from employee ...')
                print(json.dumps(offer['offer_from_employee'], indent=2))
                completion_time_i = offer['offer_from_workstation']['completion_time']
                availability_start_time_robot = offer['offer_from_picking']['start_time']
                availability_start_time_employee = offer['offer_from_employee']['availability_time']
                if availability_start_time_robot >= availability_start_time_employee:
                    availability_start_time = float(availability_start_time_robot)
                    buffer_time_earlier_resource = availability_start_time_employee
                    availability_start_time_earlier_resource = availability_start_time_employee
                    log(20, 'OFFER ID:{}'.format(str(id_task)), '    Choose availability start time from robot')
                else:
                    availability_start_time = float(availability_start_time_employee)
                    buffer_time_earlier_resource = availability_start_time_robot
                    availability_start_time_earlier_resource = availability_start_time_robot
                    log(20, 'OFFER ID:{}'.format(str(id_task)), '    Choose availability start time from picking')
                difference_1 = (abs(offer['offer_from_workstation']['desired_availability_date'] - availability_start_time))
                log(20, 'OFFER ID:{}'.format(str(id_task)), '{:>25}: {:0.2f} sec'.format('difference_1', difference_1))
                if offer['offer_from_workstation']['buffer_time'] < difference_1:
                    harmonized = False
                    log(20,
                        'OFFER ID:{}'.format(str(id_task)),
                        '    Failed harmonisation! buffer time to small'
                        )
                difference_2 = (abs(availability_start_time - availability_start_time_earlier_resource))
                log(20, 'OFFER ID:{}'.format(str(id_task)), '{:>25}: {:0.2f} sec'.format('difference_2', difference_2))
                if buffer_time_earlier_resource < difference_2:
                    harmonized = False
                    log(20,
                        'OFFER ID:{}'.format(str(id_task)),
                        '    Failed harmonisation! buffer time earlier resource to small'
                        )
                start_time = availability_start_time
                log(20,
                    'OFFER ID:{}'.format(str(id_task)),
                    '{:>25}: {}'.format('start_time', datetime.datetime.fromtimestamp(start_time))
                    )
                completion_time_j = start_time + float(offer['offer_from_workstation']['skill_time'])
                log(20,
                    'OFFER ID:{}'.format(str(id_task)),
                    '{:>25}: {}'.format('completion_time_i+1', datetime.datetime.fromtimestamp(completion_time_j))
                    )
                throughput_time_j = completion_time_j - completion_time_i
                log(20,
                    'OFFER ID:{}'.format(str(id_task)),
                    '{:>25}: {:0.2f} sec'.format('throughput_time_i+1', throughput_time_j)
                    )
                throughput_time_j_normalized = math.exp(-10 / throughput_time_j)
                log(20,
                    'OFFER ID:{}'.format(str(id_task)),
                    '{:>25}: {:0.2f} sec'.format('throughput_time_i+1_norm.', throughput_time_j_normalized)
                    )
                total_costs = (float(offer['offer_from_workstation']['costs_workstation']) +
                               float(offer['offer_from_workstation']['costs_ial_transport']) +
                               float(offer['offer_from_employee']['costs']) +
                               float(offer['offer_from_picking']['robot_costs'])
                               )
                log(20,
                    'OFFER ID:{}'.format(str(id_task)),
                    '{:>25}: {:0.2f} EUR'.format('total_costs', total_costs)
                    )
                total_costs_normalized = math.exp(-1 / total_costs)
                log(20,
                    'OFFER ID:{}'.format(str(id_task)),
                    '{:>25}: {:0.2f} EUR'.format('total_costs:norm', total_costs_normalized)
                    )
                valuation_result = alpha_time * throughput_time_j_normalized + alpha_costs * total_costs_normalized
                log(20,
                    'OFFER ID:{}'.format(str(id_task)),
                    '{:>25}: {:0.3f}'.format('VALUATION_RESULT', valuation_result)
                    )
                offer['start_time'] = start_time
                offer['completion_time_j'] = completion_time_j
                offer['throughput_time_j'] = throughput_time_j
                offer['throughput_time_j_normalized'] = throughput_time_j_normalized
                offer['total_costs'] = total_costs
                offer['total_costs_normalized'] = total_costs_normalized
                offer['valuation_result'] = valuation_result
                if harmonized:
                    return offer
                else:
                    copy_offer = deepcopy(offer)
                    copy_offer['valuation_result'] = 999
                    log(30, 'OFFER ID:{}'.format(str(id_task)), '    Failed harmonisation ...')
                    log(30,
                        'OFFER ID:{}'.format(str(id_task)),
                        '{:>25}: {}'.format('valuation_result', copy_offer['valuation_result'])
                        )
                    return copy_offer
        else:
            copy_offer = deepcopy(offer)
            copy_offer['valuation_result'] = 999
            log(30, 'OFFER ID:{}'.format(str(id_task)), '    Failed calculate valuation result ...')
            log(30,
                'OFFER ID:{}'.format(str(id_task)),
                '{:>25}: {}'.format('valuation_result', copy_offer['valuation_result'])
                )
            return copy_offer

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
        else:
            log(40, 'HTTP', '    Receive wrong status code: {}'.format(response.status_code))
        return payload

    @staticmethod
    def get_distance(position_of_robot, position_of_workstation) -> float:
        distance = numpy.linalg.norm(position_of_workstation - position_of_robot)
        return distance

    @staticmethod
    def validate_task(task):
        alpha_time = task['alpha_time']
        alpha_costs = task['alpha_costs']
        completion_time = task['completion_time']
        id_task = task['id_task']
        id_labor_process = task['id_labor_process']
        robot = task['robot']
        if id_task is None or \
                not isinstance(id_task, str):
            return False
        elif id_labor_process is None or \
                not isinstance(id_labor_process, str):
            return False
        elif completion_time is None or \
                not isinstance(completion_time, float) or \
                completion_time < time.time():
            return False
        elif alpha_time is None or \
                not isinstance(alpha_time, float) or \
                (0 > alpha_time > 1):
            return False
        elif alpha_costs is None or \
                not isinstance(alpha_costs, float) or \
                (0 > alpha_costs > 1):
            return False
        elif robot is None or \
                not isinstance(robot, dict):
            return False
        return True
