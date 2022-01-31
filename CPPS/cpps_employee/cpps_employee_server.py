#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import getopt
import logging
import os
import atexit
import configparser
import sys

from flask import Flask, json, request, make_response, jsonify, render_template
from cpps_employee_gateway import EmployeeGateway

'''
##################################################

Initialization 

'''
app = Flask(__name__)

# Config settings
config_file_name = 'cpps_employee_config.ini'
if not os.path.isfile(config_file_name):
    raise FileNotFoundError(config_file_name)
config_parser = configparser.ConfigParser()
config_parser.read(config_file_name)

directory = 'logfiles/'
flask_filename = 'flask_logfile.log'
if not os.path.isdir(directory):
    os.mkdir(directory)
fh = logging.FileHandler(directory + flask_filename)
fh.setLevel(logging.DEBUG)
flask_logger = logging.getLogger('flask')
flask_logger.addHandler(fh)
flask_logger.setLevel(logging.INFO)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(fh)
werkzeug_logger.setLevel(logging.INFO)

# Main init
employee_gateway = None     # type: EmployeeGateway


@app.route('/emp/ui', methods=['GET'])
def ui():
    if request.method == 'GET':
        return render_template('index.html')


@app.route('/emp/api/employees', methods=['GET'])
def get_employees():
    if request.method == 'GET':
        return make_response(json.dumps(employee_gateway.get_employees()), 200)


@app.route('/emp/api/calendar/export', methods=['GET'])
def export_calendar():
    if request.method == 'GET':
        return make_response(employee_gateway.export_calendar(), 200)


@app.route('/emp/api/employee/session', methods=['PUT', 'POST'])
def session_employee():
    req_data = json.loads(request.data)
    if request.method == 'PUT':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined for employee update'), 400)
        employee_gateway.logout_employee(employee_id=req_data['employee_id'],
                                         cookie_id=req_data['cookie_id']
                                         )
    if request.method == 'POST':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined for employee update'), 400)
        employee_gateway.login_employee(employee_id=req_data['employee_id'],
                                        cookie_id=req_data['cookie_id']
                                        )


@app.route('/emp/api/offer', methods=['POST'])
def get_offer():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined for employee offer'), 400)

        # If task is not defined, abort.
        if 'task' not in req_data:
            return make_response(jsonify(FAILURE='No task defined for employee offer'), 400)
        else:
            task = dict(req_data['task'])
        # Task validation
        if 'alpha_time' not in task and \
                'alpha_costs' not in task and \
                'id_cycle' not in task and \
                'id_task' not in task and \
                'id_labor_process' not in task and \
                'desired_availability_date' not in task and \
                'skill_time' not in task and \
                'buffer_time' not in task and \
                'workstation_id' not in task:
            return make_response(jsonify(FAILURE='Wrong task object'), 400)
        # if not employee_gateway.validate_task(task=task):
        #     return make_response(jsonify(FAILURE='Task failed the validation process'), 400) todo: Korrektur
        # else:
        result = employee_gateway.get_offer(alpha_time=float(task['alpha_time']),
                                            alpha_costs=float(task['alpha_costs']),
                                            buffer_time_workstation=float(task['buffer_time']),
                                            desired_availability_date=float(task['desired_availability_date']),
                                            id_cycle=task['id_cycle'],
                                            id_task=int(task['id_task']),
                                            id_labor_process=str(task['id_labor_process']),
                                            skill_time=float(task['skill_time']),
                                            target=task['workstation_id']
                                            )
        return make_response(json.dumps(result), 200)


@app.route('/emp/api/book', methods=['POST'])
def book_labor_process():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)
        # If task is not defined, abort.
        if 'decision' not in req_data:
            return make_response(jsonify(FAILURE='No decision defined'), 400)
        else:
            decision = req_data['decision']
        if 'id_task' not in decision and \
                'id_labor_process' not in decision and \
                'rejects' not in decision and \
                'workstation_id' not in decision and \
                'employee_id' not in decision and \
                'start_time' not in decision and \
                'time_slot_length' not in decision:
            return make_response(jsonify(FAILURE='Wrong decision object'), 400)
        result = employee_gateway.book_employee(id_task=int(decision['id_task']),
                                                id_labor_process=str(decision['id_labor_process']),
                                                rejects=list(decision['rejects']),
                                                workstation_id=str(decision['workstation_id']),
                                                employee_id=str(decision['employee_id']),
                                                start_time=float(decision['start_time']),
                                                time_slot_length=float(decision['time_slot_length'])
                                                )
        if result > 0:
            return make_response(jsonify(SUCCESS=result), 200)
        else:
            return make_response(jsonify(FAILURE=result), 400)


def terminate():
    employee_gateway.save_employees()


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'dhr', ['restore', 'debug', 'emp-config='])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)
    restore = False
    debug = False
    emp_config = 'employee_init_1'
    for o, a in opts:
        print(o)
        if o in ('-d', '--debug'):
            debug = True
        elif o in ('-r', '--restore'):
            restore = True
        elif o in('-h', '--help'):
            print('Command line options ...')
            print('>>> ./cpps_employee_server.py -d --debug -r --restore -h --help '
                  '--emp-config=<configuration name>')
            sys.exit(0)
        elif o == '--emp-config':
            emp_config = a
        else:
            assert False, 'unhandled option'
    global employee_gateway
    employee_gateway = EmployeeGateway(config_parser=config_parser, restore=restore, emp_configuration=emp_config)
    return debug


if __name__ == '__main__':
    debug = main(sys.argv[1:])
    main(sys.argv[1:])
    # Save data before terminate the execution
    atexit.register(terminate)

    app.run(host='0.0.0.0', port=27773, debug=debug)
