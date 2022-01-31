#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import getopt
import os
import sys
import configparser
import time

from cpps_task_manager import TaskManager
from cpps_task_manager import log
from pymongo import MongoClient
from flask import Flask

'''
##################################################

Initialization 

'''
app = Flask(__name__)

db_client = MongoClient('mongodb://192.168.2.188:27017/')
database = db_client.cpps
orders_collection = database.cpps_tasks


# Config settings
config_file_name = 'cpps_task_config.ini'
if not os.path.isfile(config_file_name):
    log(
        40,
        'TASK_SERVER',
        'No CONFIG.INI file detected, please create and set up the configurations'
    )
    sys.exit(-1)
config_parser = configparser.ConfigParser()
config_parser.read(config_file_name)


# Dependency init
cpps_task_manager = None


@app.route('/', methods=['GET'])
def welcome():
    return 'Welcome to task server API'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'dhp', ['debug', 'help', 'demo', 'virtual-phynodes'])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)
    debug_mode = False
    demo_mode = False
    virtual_phynode_mode = True
    for o, a in opts:
        print(o)
        if o in ('-d', '--debug'):
            debug_mode = True
        if o == '--demo':
            demo_mode = True
        elif o in ('-p', '--phynodes'):
            virtual_phynode_mode = False
        elif o in('-h', '--help'):
            print('Command line options ...')
            print('>>> ./cpps_task_server.py -d --debug -h --help --demo -p --phynodes')
            sys.exit(0)
        else:
            assert False, 'unhandled option'
    global cpps_task_manager
    cpps_task_manager = TaskManager(task_collection=orders_collection,
                                    config_parser=config_parser,
                                    config_file_name=config_file_name,
                                    demo_mode=demo_mode,
                                    virtual_phynode_mode=virtual_phynode_mode
                                    )
    return debug_mode


if __name__ == '__main__':
    debug_mode = main(sys.argv[1:])
    cpps_task_manager.start()
    time.sleep(0.25)
    app.run(host='0.0.0.0', port=27770, debug=debug_mode)
