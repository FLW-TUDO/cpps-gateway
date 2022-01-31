#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import time
import math
import logging


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
filename = 'employee_logfile_{}.log'.format(time.strftime('%Y.%m.%d_%H:%M:%S', time.localtime()))
if not os.path.isdir(directory):
    os.mkdir(directory)
logger = logging.getLogger('employee')


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


class Entry:
    def __init__(self,
                 id_cycle: str,
                 id_task: int,
                 id_labor_process: str,
                 target: str,
                 start_time: float,
                 employee_start_time: float,
                 time_slot_length: float,
                 skill_time: float
                 ):
        """
        :param id_cycle: (str)
        :param id_task: (int)
        :param id_labor_process: (str)
        :param target: (str)
        :param start_time: (float)
        :param employee_start_time: (float)
        :param time_slot_length: (float)
        :param skill_time: (float)
        """
        self.id_cycle = id_cycle
        self.id_task = id_task
        self.id_labor_process = id_labor_process
        self.target = target
        self.start_time = start_time
        self.employee_start_time = employee_start_time
        self.time_slot_length = time_slot_length
        self.skill_time = skill_time

    def to_dict(self) -> dict:
        """
        :return result: (dict)
            id_cycle: (str)
            id_task: (int)
            id_labor_process: (str)
            target: (str)
            start_time: (float)
            employee_start_time: (float)
            time_slot_length: (float)
            skill_time: (float)
        """
        result = {
            'id_cycle': self.id_cycle,
            'id_task': self.id_task,
            'id_labor_process': self.id_labor_process,
            'target': self.target,
            'availability_time': self.start_time,
            'employee_start_time': self.employee_start_time,
            'time_slot_length': self.time_slot_length,
            'skill_time': self.skill_time
        }
        return result


class Node:
    def __init__(self, entry, prev, nex):
        """
        :param entry: (Entry)
            The value of the Node as entry object.
        :param prev: (Node)
            The previous node. None if head of the list.
        :param nex: (Node)
            The next node. None if tail of the list.
        """
        self.entry = entry
        self.prev = prev
        self.next = nex

    def has_next(self) -> bool:
        """
        :return: (bool)
            Return true if the current node has an successor, else False.
        """
        if self.next is None:
            return False
        else:
            return True


class Calendar:
    def __init__(self):
        self.head = None
        self.tail = None

    def append(self, new_entry: Entry) -> Entry:
        """
        :param new_entry: (Entry)
            New calendar entry that define the start time.
        :return: (Entry)
            Returns an entry object with new availability start time.
        """
        new_node = Node(new_entry, None, None)
        temp_iterator = None
        iterator = self.head
        # Falls die Doppeltverketteteliste keine Einträge enthaelt
        if iterator is None:
            self.head = new_node
            self.tail = new_node
            return new_node.entry
        # Falls nur ein Eintrag in der Liste exestiert
        elif iterator == self.tail:
            if iterator.entry.id_cycle == new_node.entry.id_cycle:
                # Wird danach eingehangen
                append_before = False
            else:
                new_node_end_time = new_node.entry.employee_start_time + new_node.entry.time_slot_length
                # Am Anfang der Liste einfuegen, falls Endzeitpunkt des neuen Eintrags kleiner ist
                if iterator.entry.employee_start_time > new_node_end_time:
                    append_before = True
                # Sonst am Ende der Liste einfuegen, ggf Startzeit anpassen
                else:
                    iterator_end_time = iterator.entry.employee_start_time + iterator.entry.time_slot_length
                    if iterator_end_time > new_node.entry.employee_start_time:
                        new_start_time = iterator_end_time
                        difference = new_start_time - new_node.entry.employee_start_time
                        new_node.entry.employee_start_time = new_start_time
                        new_node.entry.start_time += difference
                    append_before = False
            if append_before:
                self.head = new_node
                self.head.next = self.tail
                self.tail.prev = self.head
                self.tail.next = None
            else:
                self.tail = new_node
                self.tail.prev = self.head
                self.head.next = self.tail
                self.head.prev = None
            return new_node.entry
        # Es existieren mehrere Einträge im Kalender
        else:
            # Iteriert über die Liste und sucht passenden Slot
            while iterator.has_next():
                # Eintrag mit gleicher Zyklus Id gefunden
                if iterator.entry.id_cycle == new_node.entry.id_cycle:
                    if temp_iterator is None:
                        if iterator == self.head:
                            temp_iterator = Node(iterator.entry, iterator.prev, iterator.next)
                        else:
                            temp_iterator = Node(iterator.prev.entry, iterator.prev.prev, iterator.prev.next)
                    iterator = iterator.next
                    continue
                # Eintrag mit unterschiedlicher Zyklus Id
                else:
                    new_node_end_time = new_node.entry.employee_start_time + new_node.entry.time_slot_length
                    # Vorlaufig passende Position gefunden
                    if iterator.entry.employee_start_time > new_node_end_time:
                        if temp_iterator is None:
                            prev_iterator = iterator.prev
                        else:
                            if temp_iterator == self.head:
                                prev_iterator = None
                            else:
                                prev_iterator = Node(temp_iterator.entry, temp_iterator.prev, temp_iterator.next)
                            temp_iterator = None
                        if prev_iterator is None:
                            new_node.prev = iterator.prev
                            new_node.next = iterator
                            iterator.prev = new_node
                            self.head = new_node
                            return new_node.entry
                        else:
                            prev_end_time = prev_iterator.entry.employee_start_time + \
                                            prev_iterator.entry.time_slot_length
                            # Zeitslot passt in die Luecke
                            if prev_end_time <= new_node.entry.employee_start_time:
                                new_node.prev = iterator.prev
                                new_node.next = iterator
                                iterator.prev.next = new_node
                                iterator.prev = new_node
                                return new_node.entry
                            # Startzeitpunkt muss angepasst werden, falls möglich
                            else:
                                new_start_time = prev_end_time
                                new_end_time = new_start_time + new_node.entry.time_slot_length
                                difference = new_start_time - new_node.entry.employee_start_time
                                if new_end_time < iterator.entry.employee_start_time:
                                    new_node.entry.employee_start_time = new_start_time
                                    new_node.entry.start_time += difference
                                    new_node.prev = iterator.prev
                                    new_node.next = iterator
                                    iterator.prev.next = new_node
                                    iterator.prev = new_node
                                    return new_node.entry
                    else:
                        temp_iterator = None
                iterator = iterator.next
            # Neuer Eintrag wird ans Ende der Liste hinzugefuegt
            else:
                # Eintrag mit gleicher Zyklus Id gefunden
                if iterator.entry.id_cycle == new_node.entry.id_cycle:
                    if temp_iterator is None:
                        prev_iterator = iterator.prev
                    else:
                        if temp_iterator == self.head:
                            prev_iterator = None
                        else:
                            prev_iterator = Node(temp_iterator.entry, temp_iterator.prev, temp_iterator.next)
                        temp_iterator = Node
                    if prev_iterator is not None:
                        prev_end_time = prev_iterator.entry.employee_start_time + prev_iterator.entry.time_slot_length
                        # Startzeitpunkt muss angepasst werden
                        if prev_end_time > new_node.entry.employee_start_time:
                            new_start_time = prev_end_time
                            difference = new_start_time - new_node.entry.employee_start_time
                            new_node.entry.employee_start_time = new_start_time
                            new_node.entry.start_time += difference
                    new_node.prev = iterator
                    iterator.next = new_node
                    self.tail = new_node
                    return new_node.entry
                # Eintrag mit unterschiedlicher Zyklus Id
                else:
                    new_node_end_time = new_node.entry.employee_start_time + new_node.entry.time_slot_length
                    if iterator.entry.employee_start_time > new_node_end_time:
                        if temp_iterator is None:
                            prev_iterator = iterator.prev
                        else:
                            if temp_iterator == self.head:
                                prev_iterator = None
                            else:
                                prev_iterator = Node(temp_iterator.entry, temp_iterator.prev, temp_iterator.next)
                            temp_iterator = Node
                        if prev_iterator is None:
                            new_node.prev = iterator.prev
                            new_node.next = iterator
                            iterator.prev = new_node
                            self.head = new_node
                            return new_node.entry
                        else:
                            prev_end_time = prev_iterator.entry.employee_start_time + \
                                            prev_iterator.entry.time_slot_length
                            # Zeitslot passt in die Luecke
                            if prev_end_time <= new_node.entry.employee_start_time:
                                new_node.prev = iterator.prev
                                new_node.next = iterator
                                iterator.prev.next = new_node
                                iterator.prev = new_node
                                return new_node.entry
                            # Startzeitpunkt muss angepasst werden, falls möglich
                            else:
                                new_start_time = prev_end_time
                                new_end_time = new_start_time + new_node.entry.time_slot_length
                                difference = new_start_time - new_node.entry.employee_start_time
                                if new_end_time < iterator.entry.employee_start_time:
                                    new_node.entry.employee_start_time = new_start_time
                                    new_node.entry.start_time += difference
                                    new_node.prev = iterator.prev
                                    new_node.next = iterator
                                    iterator.prev.next = new_node
                                    iterator.prev = new_node
                                    return new_node.entry
                    iterator_end_time = iterator.entry.employee_start_time + iterator.entry.time_slot_length
                    # Startzeitpunkt muss angepasst werden
                    if iterator_end_time > new_node.entry.employee_start_time:
                        new_start_time = iterator_end_time
                        difference = new_start_time - new_node.entry.employee_start_time
                        new_node.entry.employee_start_time = new_start_time
                        new_node.entry.start_time += difference
                    new_node.prev = iterator
                    iterator.next = new_node
                    self.tail = new_node
                    return new_node.entry

    # This function deletes all entries with the same task and labor process id
    def delete(self,
               id_task: int,
               id_labor_process: str,
               target: str
               ) -> int:
        count = 0
        iterator = self.head
        if iterator is not None:
            if iterator == self.tail:
                if iterator.entry.id_task == id_task and \
                        iterator.entry.id_labor_process == id_labor_process and \
                        iterator.entry.target == target:
                    self.head = self.tail = None
                    return count + 1
                else:
                    return count
            else:
                while iterator.has_next():
                    if iterator.entry.id_task == id_task and \
                            iterator.entry.id_labor_process == id_labor_process and \
                            iterator.entry.target == target:
                        if iterator == self.head:
                            self.head = iterator.next
                            iterator.next.prev = None
                        else:
                            iterator.prev.next = iterator.next
                            iterator.next.prev = iterator.prev
                        return count + 1
                    iterator = iterator.next
                else:
                    if iterator.entry.id_task == id_task and \
                            iterator.entry.id_labor_process == id_labor_process and \
                            iterator.entry.target == target:
                        if iterator.prev is None:
                            self.head = self.tail = None
                        else:
                            iterator.prev.next = None
                            self.tail = iterator.prev
                        count += 1
                    return count
        return count

    def update(self,
               id_task: int,
               id_labor_process: str,
               target: str,
               new_start_time: float,
               new_time_slot_length: float,
               running_time: float
               ) -> float:
        iterator = self.head
        if iterator is not None:
            if iterator == self.tail:
                if iterator.entry.id_task == id_task and \
                        iterator.entry.id_labor_process == id_labor_process and \
                        iterator.entry.target == target:
                    difference = new_start_time - iterator.entry.start_time
                    iterator.entry.start_time = new_start_time
                    iterator.entry.employee_start_time += difference
                    iterator.entry.time_slot_length = new_time_slot_length + running_time
                    return iterator.entry.start_time
                else:
                    return 0.0
            else:
                while iterator.has_next():
                    if iterator.entry.id_task == id_task and \
                            iterator.entry.id_labor_process == id_labor_process and \
                            iterator.entry.target == target:
                        difference = new_start_time - iterator.entry.start_time
                        iterator.entry.start_time = new_start_time
                        iterator.entry.employee_start_time += difference
                        iterator.entry.time_slot_length = new_time_slot_length + running_time
                        return iterator.entry.start_time
                    iterator = iterator.next
                else:
                    if iterator.entry.id_task == id_task and \
                            iterator.entry.id_labor_process == id_labor_process and \
                            iterator.entry.target == target:
                        difference = new_start_time - iterator.entry.start_time
                        iterator.entry.start_time = new_start_time
                        iterator.entry.employee_start_time += difference
                        iterator.entry.time_slot_length = new_time_slot_length + running_time
                        return iterator.entry.start_time
                    else:
                        return 0.0
        return 0.0

    def to_dict_list(self) -> list:
        iterator = self.head
        result = []
        if iterator is not None:
            while iterator.has_next():
                result.append(iterator.entry.to_dict())
                iterator = iterator.next
            else:
                result.append(iterator.entry.to_dict())
        return result


class Employee(object):
    """
    skills = [
        {
            'skill': string,
            'period_time': seconds
        },
        ...
    ]
    """

    def __init__(self,
                 employee_id,
                 vicon_id='',
                 skills=None,
                 active=False,
                 labor_costs=0.0,
                 running_time=0,
                 epsilon=0.5
                 ):
        if skills is None:
            skills = []
        self._employee_id = employee_id
        self._vicon_id = vicon_id
        self._skills = skills
        self._labor_costs = labor_costs
        self._running_time = running_time
        self._epsilon = epsilon
        self._active = active
        self._blocked = False
        self._cookie_id = None
        self._calendar = Calendar()

    def attributes_to_dict(self) -> dict:
        return {
            'employee_id': self._employee_id,
            'vicon_id': self._vicon_id,
            'skills': self._skills,
            'labor_costs': self._labor_costs,
            'running_time': self._running_time,
            'epsilon': self._epsilon,
            'active': self._active,
            'blocked': self._blocked,
            'cookie_id': self._cookie_id,
            'calendar': self.get_calendar()
        }

    def get_employee_id(self) -> str:
        return self._employee_id

    def get_vicon_id(self) -> str:
        return self._vicon_id

    def get_skills(self) -> list:
        return self._skills

    def has_skill(self, searched_skill) -> bool:
        for skill in self._skills:
            if skill == searched_skill:
                return True
        return False

    def get_labor_costs(self) -> float:
        return self._labor_costs

    def get_running_time(self) -> float:
        return self._running_time

    def get_calendar(self) -> list:
        return self._calendar.to_dict_list()

    def set_vicon_id(self, new_vicon_id) -> bool:
        if new_vicon_id is not None and isinstance(new_vicon_id, str):
            self._vicon_id = new_vicon_id
            return True
        return False

    def set_skills(self, new_skills) -> bool:
        if new_skills is not None and isinstance(new_skills, list):
            self._skills = new_skills
            return True
        return False

    def set_costs(self, new_costs) -> float:
        if new_costs is not None and isinstance(new_costs, float):
            self._labor_costs = new_costs
        return self._labor_costs

    def activate(self) -> bool:
        self._active = True
        return self._active

    def deactivate(self) -> bool:
        self._active = False
        return self._active

    def is_active(self) -> bool:
        return self._active

    def block(self, cookie_id: str) -> bool:
        self._blocked = True
        self._cookie_id = cookie_id
        return self._blocked

    def unblock(self, cookie_id: str) -> bool:
        self._blocked = False
        if self._cookie_id == cookie_id:
            self._cookie_id = None
        return self._blocked

    def reservation(self,
                    alpha_time: float,
                    alpha_costs: float,
                    desired_availability_time: float,
                    id_cycle: str,
                    id_task: int,
                    id_labor_process: str,
                    skill_time: float,
                    target: str,
                    buffer_time_workstation: float
                    ) -> dict:
        """
        :param buffer_time_workstation: (float)
        :param id_cycle: (str)
        :param alpha_time: (float)
        :param alpha_costs: (float)
        :param desired_availability_time: (float)
        :param id_task: (int)
        :param id_labor_process: (str)
        :param skill_time:
        :param target: (str)
        :return: (dict)
            buffer_time: (float)
            costs: (float)
            employee_id: (str)
            id_task: (int)
            id_labor_process: (str)
            availability_time: (float)
            time_slot_length: (float)
            valuation_result: (float)
        """
        log(10, 'EMPLOYEE ID:{}'.format(self._employee_id), '>>> Start reservation ...')
        log(10, '', '--------------------------------------------------')
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('id_cycle', id_cycle)
        )
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('id_task', id_task)
        )
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('id_labor_process', id_labor_process)
        )
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('target', target)
        )
        # Desired availability time
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('desired_availability_time', datetime.datetime.fromtimestamp(desired_availability_time))
        )
        # Desired start time
        desired_start_time = desired_availability_time - self._running_time
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('desired_start_time', datetime.datetime.fromtimestamp(desired_start_time))
        )
        # Work duration
        work_duration = skill_time + self._running_time
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {:0.2f} sec'.format('work_duration', work_duration)
        )
        # Buffer time
        buffer_time = work_duration * self._epsilon
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {:0.2f} sec'.format('buffer_time', buffer_time)
        )
        # Time slot length
        time_slot_length = work_duration + buffer_time
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {:0.2f} sec'.format('time_slot_length', time_slot_length)
        )
        # Create new entry object
        new_entry = Entry(
            id_cycle=id_cycle,
            id_task=id_task,
            id_labor_process=id_labor_process,
            target=target,
            start_time=desired_availability_time,
            employee_start_time=desired_start_time,
            time_slot_length=time_slot_length,
            skill_time=skill_time
        )
        # Set print_out to False for disable console output
        availability_date = self._calendar.append(new_entry=new_entry)
        # Parse availability date into a dict
        availability_date_dict = availability_date.to_dict()
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('employee_start_time',
                                datetime.datetime.fromtimestamp(availability_date_dict['employee_start_time'])
                                )
        )
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {}'.format('availability_time',
                                datetime.datetime.fromtimestamp(availability_date_dict['availability_time'])
                                )
        )
        # Start deviation
        start_deviation = availability_date_dict['availability_time'] - desired_availability_time
        if start_deviation == 0:
            start_deviation = 0.01
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {:0.2f} sec'.format('start_deviation', start_deviation)
        )
        # Costs for this duration
        costs = self._labor_costs * work_duration
        log(
            20,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {:0.2f} EUR'.format('costs', costs)
        )
        # Normalized start deviation
        start_deviation_normalized = math.exp(-1 / start_deviation)
        log(
            10,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {:0.2f}'.format('start_deviation_normal.', start_deviation_normalized)
        )
        # Normalized costs
        costs_normalized = math.exp(-1 / costs)
        log(
            10,
            'EMPLOYEE ID:{}'.format(self._employee_id),
            '{:>25}: {:0.2f}'.format('costs_normal.', costs_normalized)
        )
        # Valuation result
        if start_deviation > buffer_time_workstation:
            valuation_result = 999
            log(30,
                'EMPLOYEE ID:{}'.format(self._employee_id),
                '{:>25}: {:0.2f}'.format('VALUATION_RESULT', valuation_result)
                )
        else:
            valuation_result = (alpha_time * start_deviation_normalized) + (alpha_costs * costs_normalized)
            log(20,
                'EMPLOYEE ID:{}'.format(self._employee_id),
                '{:>25}: {:0.2f}'.format('VALUATION_RESULT', valuation_result)
                )
        availability_date_dict['valuation_result'] = valuation_result   # Append valuation result into dict
        availability_date_dict['employee_id'] = self._employee_id       # Append employee id into dict
        availability_date_dict['buffer_time'] = buffer_time             # Append buffer time into dict
        availability_date_dict['costs'] = costs                         # Append costs into dict
        return availability_date_dict

    def reject(self,
               id_task: int,
               id_labor_process: str,
               target: str
               ) -> int:
        result = self._calendar.delete(
            id_task=id_task,
            id_labor_process=id_labor_process,
            target=target
        )
        return result

    def book(self,
             id_task: int,
             id_labor_process: str,
             target: str,
             start_time: float,
             time_slot_length: float
             ) -> float:
        return self._calendar.update(
            id_task=id_task,
            id_labor_process=id_labor_process,
            target=target,
            new_start_time=start_time,
            new_time_slot_length=time_slot_length,
            running_time=self._running_time
        )
