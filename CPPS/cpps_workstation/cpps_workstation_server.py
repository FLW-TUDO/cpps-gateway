#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import getopt
import logging
import os
import atexit
import configparser
import sys
import time

import numpy
from flask import Flask, json, request, make_response, jsonify, render_template
from cpps_workstation_gateway import WorkstationGateway

'''
##################################################

Initialization 

'''
app = Flask(__name__)

# Config settings
config_file_name = 'cpps_workstation_config.ini'
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


# Dependency init
workstation_gateway = None      # type: WorkstationGateway


@app.route('/ws/ui', methods=['GET'])
def ui():
    if request.method == 'GET':
        return render_template('index.html')


@app.route('/ws/api/workstations', methods=['GET'])
def get_workstations():
    if request.method == 'GET':
        return make_response(json.dumps(workstation_gateway.get_workstations()), 200)


@app.route('/ws/api/calendar/export', methods=['GET'])
def export_calendar():
    if request.method == 'GET':
        return make_response(workstation_gateway.export_calendar(), 200)


@app.route('/ws/api/get_distance', methods=['POST'])
def get_distance():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        position_of_robot = None
        position_of_workstation = None
        # Check if request have an json-body and an address option.
        # If no option is defined, send to broadcast.
        if req_data is not None and 'pos_r' in req_data and 'pos_w' in req_data:
            position_of_robot = numpy.array(req_data['pos_r'])
            position_of_workstation = numpy.array(req_data['pos_w'])
        distance = workstation_gateway.get_distance(position_of_robot, position_of_workstation)
        print(distance)
        return make_response(
            jsonify(DISTANCE='{}'.format(distance)), 200
        )


@app.route('/ws/api/offer', methods=['POST'])
def get_offer():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)
        # If task is not defined, abort.
        if 'task' not in req_data:
            return make_response(jsonify(FAILURE='No task defined'), 400)
        else:
            task = req_data['task']
        # Task validation
        if 'alpha_time' not in task and \
                'alpha_costs' not in task and \
                'completion_time' not in task and \
                'id_cycle' not in task and \
                'id_task' not in task and \
                'id_labor_process' not in task and \
                'robot' not in task and \
                'components' not in task and \
                'last_workstation_id' not in task:
            return make_response(jsonify(FAILURE='Wrong task object'), 400)
        # if not workstation_gateway.validate_task(task=task):
        #     return make_response(jsonify(FAILURE='Task failed the validation process'), 400)
        # else:
        result = workstation_gateway.get_offer(alpha_time=float(task['alpha_time']),
                                               alpha_costs=float(task['alpha_costs']),
                                               completion_time=float(task['completion_time']),
                                               id_cycle=task['id_cycle'],
                                               id_task=int(task['id_task']),
                                               id_labor_process=str(task['id_labor_process']),
                                               robot=dict(task['robot']),
                                               components=dict(task['components']),
                                               last_workstation_id=task['last_workstation_id']
                                               )
        return make_response(json.dumps(result), 200)


@app.route('/ws/api/book', methods=['POST'])
def book_labor_process():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)
        # If decision is not defined, abort.
        if 'decision' not in req_data:
            return make_response(jsonify(FAILURE='No decision defined'), 400)
        else:
            decision = req_data['decision']
        if 'id_task' not in decision and \
                'id_labor_process' not in decision and \
                'rejects' not in decision and \
                'workstation_id' not in decision and \
                'employee_id' not in decision and \
                'robot_id' not in decision and \
                'start_time' not in decision and \
                'time_slot_length' not in decision:
            return make_response(jsonify(FAILURE='Wrong decision object'), 400)
        result = workstation_gateway.book_workstation(id_task=int(decision['id_task']),
                                                      id_labor_process=str(decision['id_labor_process']),
                                                      rejects=list(decision['rejects']),
                                                      workstation_id=str(decision['workstation_id']),
                                                      employee_id=str(decision['employee_id']),
                                                      robot_id=str(decision['robot_id']),
                                                      start_time=float(decision['start_time']),
                                                      time_slot_length=float(decision['time_slot_length'])
                                                      )
        return make_response(json.dumps(result), 200)


def terminate():
    workstation_gateway.save_workstations()


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'dhr', ['restore', 'debug', 'ws-config='])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)
    restore = False
    debug = False
    ws_config = 'workstation_init_1'
    for o, a in opts:
        print(o)
        if o in ('-d', '--debug'):
            debug = True
        elif o in ('-r', '--restore'):
            restore = True
        elif o in('-h', '--help'):
            print('Command line options ...')
            print('>>> ./cpps_workstation_server.py -d --debug -r --restore -h --help '
                  '--ws-config=<configuration name>')
            sys.exit(0)
        elif o == '--ws-config':
            ws_config = a
        else:
            assert False, 'unhandled option'
    global workstation_gateway
    workstation_gateway = WorkstationGateway(config_parser=config_parser, restore=restore, ws_configuration=ws_config)
    return debug


if __name__ == '__main__':
    debug = main(sys.argv[1:])
    # Save data before terminate the execution
    atexit.register(terminate)
    time.sleep(1)
    app.run(host='0.0.0.0', port=27772, debug=debug)
