#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import threading
import sys
import time
import requests
import configparser
import numpy

from cpps_task_manager import TaskManager, log
from cpps_task import Task


class TaskAgent(threading.Thread):
    def __init__(self,
                 agent_id: int,
                 task: Task,
                 task_manager: TaskManager,
                 config_parser: configparser.ConfigParser,
                 positions: dict
                 ):
        super().__init__()
        self._cpps_task_manager = task_manager
        self._agent_configs = config_parser['DEFAULT']
        self._klt_enum = dict(eval(self._agent_configs['KLT_ENUM']))
        self._priority_graph = dict(eval(self._agent_configs['PRIORITY_GRAPH']))
        self._failed = False
        self._block = False
        self._agent_id = agent_id
        self._task = task
        self._next_completion_time = None
        self._positions = positions
        log(
            10,
            'TASK_AGENT ID:{:d}'.format(self._agent_id),
            'Initialization completed'
        )

    def run(self):
        # Starting stage 1
        if not self._failed:
            self.stage_1()
        # # Starting stage 2
        # if not self.failed:
        #     self.stage_2()
        if not self._failed:
            log(
                20,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'Finished...'
            )
        else:
            log(
                20,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'Failed...'
            )

    def _decision_finding(self, offers: dict) -> dict:
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
        if offers is not {}:
            best_decision = None
            for key in offers:
                offer = offers[key]
                if best_decision is None:
                    best_decision = key
                else:
                    if offers[best_decision]['valuation_result'] > offer[key]['valuation_result']:
                        best_decision = key
            log(
                40,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'Best decision {} from {}'.format(offers[best_decision]['valuation_result'], best_decision)
            )
            return offers[best_decision]
        else:
            log(
                40,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'Got an empty offer argument!'
            )
            return {}

    def _get_offer(self,
                   id_labor_process: str,
            completion_time: float,
            alpha_time: float,
            alpha_costs: float
    ):
        request_body = {
            'alpha_time': alpha_time,
            'alpha_costs': alpha_costs,
            'completion_time': completion_time,
            'id_task': self._task.task_id,
            'id_labor_process': id_labor_process,
            'robot': self._task.robot
        }
        response = self._cpps_task_manager.send_http_request(
            method='POST',
            url='{}/ws/api/offer'.format(self._agent_configs['WORKSTATION_GATEWAY_URL']),
            request_body=request_body
        )
        if response is not None:
            try:
                payload = response.json()
            except ValueError as err:
                log(40, 'TASK_AGENT ID:{:d}'.format(self._agent_id), 'Value error: {}'.format(str(err)))
        return payload

    # Return a boolean if task will be finished
    def _is_finished(self) -> bool:
        if self._priority_graph['end_node']['state'] == 0:
            return False
        return True

    # Request for a free phynode
    def _poll_phynode(self):
        url = '{}/gateway/POLL'.format(self._agent_configs['PHYNODE_GATEWAY_URL'])
        request_body = {
            'ordernumber': self._task.task_id,
            'itemdescr': 0
        }
        max_attempts = int(self._agent_configs['FAILED_ATTEMPTS_POLLING'])
        attempts = 1
        successful = False
        while not successful and attempts <= max_attempts:
            # Search for a free klt
            response = self._cpps_task_manager.send_http_request('POST', url, request_body)
            if response is not None:
                try:
                    payload = response.json()
                except ValueError:
                    break
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
                sys.stdout.write('\r[{}]: {}'.format(
                    '{:<20}'.format('TASK_PROCESS {:d}]'.format(self._task.task_id)),
                    'Polling, abort after {:4d} attempt(s)'.format(max_attempts - attempts))
                )
                sys.stdout.flush()
                time.sleep(.5)
                attempts += 1
        else:
            # If FAILURE
            if attempts > max_attempts:
                self._failed = True
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'stage1',
                    'timeout! Empty phynodes dont respond'
                )
                log(
                    10,
                    'TASK_AGENT ID:{:d}'.format(self._agent_id),
                    'POLL abort after {:d} attempts to set a phynode!'.format(max_attempts)
                )
            # If SUCCESS
            else:
                # Update database
                self._cpps_task_manager.update_states(
                    self._task.task_id,
                    'stage1',
                    'Polling phynode complete!'
                )
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
                log(
                    10,
                    'TASK_AGENT ID:{:d}'.format(self._agent_id),
                    'Set phynode (ADDR: {})\n'.format(self._task.empty_klt_phyaddr)
                )

    # Reserve the free phynode
    def _reserve_phynode(self):
        url = '{}/gateway/RSVE'.format(self._agent_configs['PHYNODE_GATEWAY_URL'])
        request_body = {
            'phyaddr': self._task.empty_klt_phyaddr,
            'ordernumber': self._task.task_id,
            'amount': 0
        }
        response = self._cpps_task_manager.send_http_request('POST', url, request_body)
        if response.status_code == 200:
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                'Reserving phynode complete!'
            )
            log(
                10,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'Reserve phynode (ADDR: {:d})'.format(self._task.empty_klt_phyaddr)
            )
        else:
            self._failed = True
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                'Abort! Failed by blocking the phynode (ADDR: {:d})'.format(self._task.empty_klt_phyaddr)
            )
            log(
                10,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'Failed by blocking the phynode (ADDR: {:d})'.format(self._task.empty_klt_phyaddr)
            )

    def _set_alpha_time(self):
        pass
        # todo: Unterscheidung zwischen initialem vorgang und prioritätsgraphen

    # Task end time will be the time, when the task could be finished
    def _set_task_end_time(self):
        current_time = time.time()
        average = 0
        for key in self._cpps_task_manager.get_reference_turning_time().keys():
            average += self._cpps_task_manager.get_average_turning_time(key)
        self._task.task_end_time = current_time + average
        log(
            10,
            'TASK_AGENT ID:{:d}'.format(self._agent_id),
            'Calculate task end time: {}'.format(self._task.task_end_time)
        )

    # Request the initial start time and update the next completion time attribute
    def _set_initial_start_time(self):
        target_vicon_list = []
        response_from_workstation_gateway = self._cpps_task_manager.send_http_request(
            method='GET',
            url='{}/ws/api/workstations'.format(self._agent_configs['WORKSTATION_GATEWAY_URL']),
            request_body={}
        )
        if response_from_workstation_gateway.status_code == 200 and response_from_workstation_gateway is not None:
            for workstation in response_from_workstation_gateway.json():
                if workstation['active']:
                    target_vicon_list.append(workstation['vicon_id'])
        else:
            self._failed = True
            # Update database
            self._cpps_task_manager.update_states(
                self._task.task_id,
                'stage1',
                'FAILURE! Workstation gateway reply with status code {}'.format(
                    response_from_workstation_gateway.status_code
                )
            )
            log(
                10,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'FAILURE! Workstation gateway reply with status code {}'.format(
                    response_from_workstation_gateway.status_code
                )
            )
        request_body = {
            'id_robot': self._task.task_id,
            'id_klt': self._task.empty_klt_phyaddr,
            'target': target_vicon_list
        }
        response_from_fms_gateway = self._cpps_task_manager.send_http_request(
            method='POST',
            url='{}/ws/api/offer'.format(self._agent_configs['WORKSTATION_GATEWAY_URL']),
            request_body=request_body
        )
        if response_from_fms_gateway.status_code == 200 and response_from_fms_gateway is not None:
            try:
                payload = response_from_fms_gateway.json()
                if payload is not None and 'completion_time' in payload:
                    self._next_completion_time = payload['completion_time']
                    log(
                        10,
                        'TASK_AGENT ID:{:d}'.format(self._agent_id),
                        'Set initial start time: {}'.format(self._next_completion_time)
                    )
            except ValueError:
                self._failed = True
        else:
            self._failed = True
            log(
                10,
                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                'Set initial start time failed by getting fms reply'
            )

    def stage_1(self):
        # Update database
        self._cpps_task_manager.update_states(
            self._task.task_id,
            'stage1',
            'Waiting for empty phynode reply..'
        )
        log(
            10,
            'ORDER_PROCESS {:d}'.format(self._task.task_id),
            'Start with stage 1 ...'
        )
        # Find free klt
        if not self._failed:
            self._poll_phynode()
        # Reserve phynode
        if not self._failed:
            self._reserve_phynode()
        # Request to fms gateway for initial start time
        self._set_initial_start_time()
        # Calculate task end time
        self._set_task_end_time()
        # Request to workstation gateway for initial offer
        if not self._failed:
            best_decision = self._get_offer(
                id_labor_process=self._priority_graph[self._priority_graph['start_node']]['operation'],
                completion_time=self._next_completion_time
            )
            if best_decision is {}:
                self._failed = True
        # Booking
        if not self._failed:
            pass    # todo:

    def stage_2(self):
        candidate = None
        while not self._is_finished():
            if not self._failed and not self._block:
                candidates = []
                best_candidate = None
                for node in self._priority_graph['start_node']['successor']:
                    node_id = str(self._task.task_id) + node['operation']
                    precondition = True
                    if len(node['preconditions']) > 0:
                        for precondition in node['preconditions']:
                            if self._priority_graph[precondition]['state'] == 0:
                                precondition = False
                    if precondition:
                        request_data = {
                            'task': self._task,
                            'id_labor_process': node_id,
                            'skill': node['operation']
                        }
                        try:
                            response_from_workstation = requests.post(
                                url=self._agent_configs['WORKSTATION_GATEWAY_URL'],
                                data=json.dumps(request_data)
                            )
                        except requests.exceptions.RequestException as err:
                            log(
                                'TASK_AGENT ID:{:d}'.format(self._agent_id),
                                'Request ERROR!\n{}'.format(err)
                            )
                            break
                        # todo: Kandidaten erstellen und in die Liste einfügen um dann den besten zu wählen
                    candidates.append(candidate)  # Node will be insert in the list
                for candidate in candidates:
                    if candidate is None:
                        best_candidate = candidate
                    else:
                        if best_candidate['costs'] > candidate['costs']:
                            best_candidate = candidate
                # todo: Reservierung bestätigen
            time.sleep(1)

    @staticmethod
    def get_distance(position_of_robot, position_of_workstation):
        return numpy.linalg.norm(position_of_workstation - position_of_robot)
