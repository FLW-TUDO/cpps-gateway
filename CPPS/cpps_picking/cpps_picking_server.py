#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import json
import os
import sys

from flask import Flask, request, make_response, jsonify
from cpps_picking_gateway import PickingGateway

app = Flask(__name__)

# Config settings
config_file_name = 'cpps_klt_config.ini'
if not os.path.isfile(config_file_name):
    raise FileNotFoundError(config_file_name)
config_parser = configparser.ConfigParser()
config_parser.read(config_file_name)


@app.route('/pck/api/', methods=['GET'])
def welcome():
    return 'Welcome to picking api'


@app.route('/pck/api/picking_tasks', methods=['GET'])
def get_picking_tasks():
    if request.method == 'GET':
        return make_response(json.dumps(picking_gateway.get_picking_tasks()), 200)


@app.route('/pck/api/klt_arrived', methods=['POST'])
def arrived():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)
        # If phyaddr is not defined, abort.
        if 'phyaddr' not in req_data:
            return make_response(jsonify(FAILURE='No phyaddr defined'), 400)
        else:
            phyaddr = req_data['phyaddr']
        # If id_task is not defined, abort.
        if 'id_task' not in req_data:
            return make_response(jsonify(FAILURE='No id_task defined'), 400)
        else:
            id_task = req_data['phyaddr']
        if picking_gateway.klt_arrived(id_task=id_task, phyaddr=phyaddr):
            return make_response(jsonify(ACK=True), 200)
        else:
            return make_response(jsonify(ACK=False), 200)


@app.route('/pck/api/offer', methods=['POST'])
def get_offer():
    req_data = json.loads(request.data.decode('utf-8'))

    if request.method == 'POST':
        # If data is not in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined for picking offer'), 400)
        # If task is not defined, abort.
        if 'task' not in req_data:
            return make_response(jsonify(FAILURE='No task defined for picking offer'), 400)
        else:
            task = dict(req_data['task'])
        # Task validation
        if 'alpha_time' not in task and \
                'alpha_costs' not in task and \
                'id_task' not in task and \
                'id_labor_process' not in task and \
                'desired_availability_date' not in task and \
                'skill_time' not in task and \
                'target' not in task and \
                'workstation_id' not in task and \
                'components' not in task and \
                'buffer_time' not in task:
            return make_response(jsonify(FAILURE='Wrong task object'), 400)
        # if not picking_gateway.validate_task(task=task):
        #     return make_response(jsonify(FAILURE='Task failed the validation process'), 400)
        # else:
        result = picking_gateway.get_offer(alpha_time=float(task['alpha_time']),
                                           alpha_costs=float(task['alpha_costs']),
                                           desired_availability_date=float(task['desired_availability_date']),
                                           id_cycle=task['id_cycle'],
                                           id_task=int(task['id_task']),
                                           id_labor_process=str(task['id_labor_process']),
                                           skill_time=float(task['skill_time']),
                                           target='/vicon/' + task['target'] + '/' + task['target'],
                                           workstation_id=task['workstation_id'],
                                           components=dict(task['components']),
                                           buffer_time_workstation=float(task['buffer_time'])
                                           )
        if 'FAILURE' not in result:
            return make_response(json.dumps(result), 200)
        else:
            return make_response(jsonify(result), 400)


@app.route('/pck/api/book', methods=['POST'])
def book_labor_process():
    # req_data = json.loads(request.data)
    req_data = json.loads(request.data.decode('utf-8'))

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
                'robot_id' not in decision and \
                'start_time' not in decision and \
                'time_slot_length' not in decision and \
                'rejects_for_fms' not in decision and \
                'workstation_vicon_id' not in decision:
            return make_response(jsonify(FAILURE='Wrong decision object'), 400)
        # print(json.dumps(req_data, indent=4))
        result = picking_gateway.book_picking_task(id_task=int(decision['id_task']),
                                                   id_labor_process=str(decision['id_labor_process']),
                                                   rejects=list(decision['rejects']),
                                                   workstation_id=str(decision['workstation_id']),
                                                   employee_id=str(decision['employee_id']),
                                                   robot_id=str(decision['robot_id']),
                                                   start_time=float(decision['start_time']),
                                                   time_slot_length=float(decision['time_slot_length']),
                                                   rejects_for_fms=list(decision['rejects_for_fms']),
                                                   workstation_vicon_id=decision['workstation_vicon_id']
                                                   )
        if 'SUCCESS' in result:
            return make_response(json.dumps(result), 200)
        else:
            return make_response(json.dumps(result), 400)


# Main init
picking_gateway = None


def main(argv):
    demo_mode = False
    if len(argv) == 0:
        demo_mode = False
    elif len(argv) == 1:
        if argv[0] == '--demo':         # Start realtime scenario
            demo_mode = True
    else:
        print('cpps_picking_server.py --demo')
        sys.exit()
    global picking_gateway
    picking_gateway = PickingGateway(config_parser=config_parser, demo_mode=demo_mode)


if __name__ == '__main__':
    main(sys.argv[1:])
    app.run(host='0.0.0.0', port=27775, debug=False)
