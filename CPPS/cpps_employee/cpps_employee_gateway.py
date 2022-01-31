#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import pickle
import sys
import time

from cpps_employee import Employee

'''
##################################################

Required files

'''

emp_file_name = 'saved_employees.bin'

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

directory = 'logfiles/'
filename = 'employee_logfile_{}.log'.format(time.strftime('%Y.%m.%d_%H:%M:%S', time.localtime()))
if not os.path.isdir(directory):
    os.mkdir(directory)
fh = logging.FileHandler(directory + filename)
fh.setLevel(logging.DEBUG)
fm = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s')
fh.setFormatter(fm)
logger = logging.getLogger('employee')
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


class EmployeeGateway:
    def __init__(self, config_parser, restore: bool, emp_configuration: str):
        self._employee_configs = config_parser['DEFAULT']
        self._employees = []
        self._initialize(restore, emp_configuration)

    def _initialize(self, restore: bool, emp_configuration: str):
        if restore and os.path.isfile(emp_file_name):
            try:
                binary_file_emp = open(emp_file_name, 'rb')
                self._employees = pickle.load(binary_file_emp)
                binary_file_emp.close()
                log(20,
                    'EMPLOYEE_GATEWAY',
                    '... Employee restored!'
                    )
            except IOError as e:
                print(e)
        else:
            try:
                employees = json.loads(self._employee_configs[emp_configuration])
                for employee in employees:
                    value = list(employee.values())[0]
                    employee_id = value['employee_id']
                    vicon_id = value['vicon_id']
                    skills = value['skills']
                    costs = float(value['costs'])
                    active = bool(value['active'])
                    running_time = int(value['running_time'])
                    epsilon = float(self._employee_configs['EPSILON'])
                    self._employees.append(
                        Employee(
                            employee_id=employee_id,
                            vicon_id=vicon_id,
                            skills=skills,
                            labor_costs=costs,
                            active=active,
                            running_time=running_time,
                            epsilon=epsilon
                        )
                    )
            except KeyError:
                log(40, 'WORKSTATION_GATEWAY', '    KeyError! No configuration for {} found'.format(emp_configuration))
                sys.exit(2)
            log(20,
                'EMPLOYEE_GATEWAY',
                '... Load settings from config file'
                )
            self.save_employees()
        log(20,
            'EMPLOYEE_GATEWAY',
            '... Initialization completed'
            )
        self.print_employee_list()

    def book_employee(self,
                      id_task: int,
                      id_labor_process: str,
                      rejects: list,
                      workstation_id: str,
                      employee_id: str,
                      start_time: float,
                      time_slot_length: float
                      ):
        log(10, 'BOOK ID:{} | SKL: {}'.format(str(id_task), id_labor_process), '>>> Start booking ...')
        log(10, '', '--------------------------------------------------')
        if rejects:
            for employee in self._employees:
                for reject in rejects:
                    if employee.has_skill(reject[0]):
                        # log(10, 'BOOK', '\n{}'.format(json.dumps(employee.get_calendar(), indent=4, sort_keys=True)))
                        count = employee.reject(id_task=id_task,
                                                id_labor_process=reject[0],
                                                target=reject[1]
                                                )
                        log(20,
                            'EMPLOYEE ID:{}'.format(str(employee.get_employee_id())),
                            '    Step 1: reject {} time slot(s) for {}'.format(count, reject)
                            )
        employee = self.get_employee(employee_id)
        # log(10, 'BOOK', '\n{}'.format(json.dumps(employee.get_calendar(), indent=4, sort_keys=True)))
        triple_for_log = [id_labor_process, workstation_id, employee.get_employee_id()]
        log(10, 'BOOK', triple_for_log)
        result = employee.book(id_task=id_task,
                               id_labor_process=id_labor_process,
                               target=workstation_id,
                               start_time=start_time,
                               time_slot_length=time_slot_length
                               )
        if result > 0:
            log(20,
                'EMPLOYEE ID:{}'.format(str(employee.get_employee_id())),
                '    Step 2: update time slot with {} for {}'.format(
                    datetime.datetime.fromtimestamp(result),
                    triple_for_log)
                )
            return result
        else:
            log(30,
                'EMPLOYEE ID:{}'.format(str(employee.get_employee_id())),
                '    Step 2: no time slot for {} found, but it should be one'.format(triple_for_log)
                )
            return result
        return result

    def get_employees(self) -> list:
        employees = []
        if self._employees:
            for employee in self._employees:
                employees.append(employee.attributes_to_dict())
        return employees

    def get_employee(self, employee_id: str) -> Employee:
        if self._employees:
            for employee in self._employees:
                if employee.get_employee_id() == employee_id:
                    return employee
        return Employee('')

    def add_employee(self, employee_id, vicon_id, skills, labor_costs, active, running_time, epsilon):
        for emp in self._employees:
            if emp.get_employee_id() == employee_id:
                return False
        self._employees.append(
            Employee(
                employee_id=employee_id,
                vicon_id=vicon_id,
                skills=skills,
                labor_costs=labor_costs,
                active=active,
                running_time=running_time,
                epsilon=epsilon
            )
        )
        return True

    def delete_employee(self, employee_id: str):
        for index, emp in enumerate(self._employees):
            if emp.get_employee_id() == employee_id:
                self._employees.pop(index)
                return True
            else:
                return False

    def save_employees(self):
        try:
            binary_file = open(emp_file_name, 'wb')
            pickle.dump(self._employees, binary_file)
            binary_file.close()
            log(20,
                'EMPLOYEE_GATEWAY',
                '... Saved employees!'
                )
        except IOError as e:
            print(e)

    def login_employee(self, employee_id: str, cookie_id: str):
        employee = self.get_employee(employee_id=employee_id)
        result = employee.block(cookie_id)
        log(10,
            'EMPLOYEE_{}'.format(employee.get_employee_id()),
            '    Worker block with cookie {}: {}'.format(cookie_id, str(result))
            )
        return result

    def logout_employee(self,  employee_id: str, cookie_id: str):
        employee = self.get_employee(employee_id=employee_id)
        result = employee.unblock(cookie_id)
        log(10,
            'EMPLOYEE_{}'.format(employee.get_employee_id()),
            '    Worker unblock with cookie {}: {}'.format(cookie_id, str(result))
            )
        return result

    def change_employee_skills(self, employee_id, new_skills):
        for emp in self._employees:
            if emp.get_employee_id() == employee_id:
                return emp.change_skills(new_skills)
        return False

    def get_offer(self,
                  alpha_time: float,
                  alpha_costs: float,
                  buffer_time_workstation: float,
                  desired_availability_date: float,
                  id_cycle: str,
                  id_task: int,
                  id_labor_process: str,
                  skill_time: float,
                  target: str
                  ) -> dict:
        """
        :param id_cycle: (str)
        :param alpha_time: (float)
        :param alpha_costs: (float)
        :param buffer_time_workstation: (float)
        :param desired_availability_date: (float)
        :param id_task: (int)
        :param id_labor_process: (str)
        :param skill_time: (float)
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
        offers = []
        valuation_result_best = {}
        log(10, 'OFFER ID:{} SKL: {}'.format(id_task, id_labor_process), '>>> Start offer ...')
        log(10, '', '--------------------------------------------------')
        for employee in self._employees:
            if employee.has_skill(id_labor_process):
                offer = employee.reservation(id_cycle=id_cycle,
                                             id_task=id_task,
                                             id_labor_process=id_labor_process,
                                             desired_availability_time=desired_availability_date,
                                             alpha_time=alpha_time,
                                             alpha_costs=alpha_costs,
                                             skill_time=skill_time,
                                             target=target,
                                             buffer_time_workstation=buffer_time_workstation
                                             )
                # log(10, 'BOOK', '\n{}'.format(json.dumps(employee.get_calender(), indent=4, sort_keys=True)))
                offers.append(offer)
        # Find best valution result
        if offers:
            for offer in offers:
                if not bool(valuation_result_best):
                    valuation_result_best = offer
                else:
                    val_offer = offer['valuation_result']
                    val_best = valuation_result_best['valuation_result']
                    if val_best > val_offer:
                        valuation_result_best = offer
            log(
                20,
                'OFFER ID:{} SKL: {}'.format(id_task, id_labor_process),
                '    CHOOSE EMPLOYEE {} AS BEST CANDIDATE'.format(valuation_result_best['employee_id'])
            )
            # Reject calendar entries from other candidates
            for offer in offers:
                employee_id = offer['employee_id']
                if employee_id != valuation_result_best['employee_id']:
                    employee = self.get_employee(employee_id)
                    if employee.get_employee_id() != '':
                        count = employee.reject(id_task=id_task,
                                                id_labor_process=id_labor_process,
                                                target=target
                                                )
                        log(
                            10,
                            'OFFER ID:{} SKL: {}'.format(id_task, id_labor_process),
                            '    {} Rejected {} time slot(s)'.format(str(employee.get_employee_id()), count)
                        )
        else:
            log(
                30,
                'OFFER ID:{} SKL: {}'.format(id_task, id_labor_process),
                '    Could not find any candidate for this offer!'
            )
        return valuation_result_best

    def print_employee_list(self):
        print('\n[{:<20}]: {}\n\n{:<15} {:<15} {}'.format('PRINT LIST', '...', 'employee_id', 'active',
                                                          'skills {operation: time}'))
        print('--------------- --------------- ------------------------')
        if len(self._employees) > 0:
            for emp in self._employees:
                print('{:15} {:15} {}'.format(emp.get_employee_id(), str(emp.is_active()), str(emp.get_skills())))
        print('\n[END]\n')

    def export_calendar(self) -> str:
        result = ''
        if self._employees:
            for employee in self._employees:
                result += 'employee {}<br>'.format(employee.get_employee_id())
                result += 'employee_start_time:<br>'
                calendar = employee.get_calendar()
                if calendar:
                    for entry in calendar:
                        text = str(entry['employee_start_time'])
                        result += '{}<br>'.format(text.replace('.', ','))
                    result += 'time_slot_length:<br>'
                    calendar = employee.get_calendar()
                    for entry in calendar:
                        text = str(entry['time_slot_length'])
                        result += '{}<br>'.format(text.replace('.', ','))
                    result += '<br><br>'
                else:
                    result += 'No calendar entry found<br><br>'
        else:
            result += 'No employees initialized'
        return result

    @staticmethod
    def validate_task(task):
        id_task = task['id_task']
        id_labor_process = task['id_labor_process']
        desired_availability_date = task['desired_availability_date']
        skill = task['skill']
        alpha_time = task['alpha_time']
        alpha_costs = task['alpha_costs']
        if id_task is None or \
                not isinstance(id_task, str):
            return False
        elif id_labor_process is None or \
                not isinstance(id_labor_process, str):
            return False
        elif desired_availability_date is None or \
                not isinstance(desired_availability_date, float) or \
                desired_availability_date < time.time():
            return False
        elif skill is None or \
                not isinstance(skill, str):
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
