#!/usr/bin/env python3

from crypt import methods
import threading, _thread
import os, sys, subprocess, time
import paho.mqtt.client as mqtt

from flask import Flask, jsonify, make_response, request, abort, json, Response
from gateway_interface import CCPhyParser, RadioStats, DHCP, Preserver, LineReader, GatewayHandler, configparser, \
    APPacket, CCPacket, gs_config
from models import log, shell_font_style

'''
############################################################
'''

# MQTT
mqtt_host = 'gopher.phynetlab.com'
mqtt_port = 8883
mqtt_topic = '/fms/order'
mqttc = mqtt.Client('GatewayServer')


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    log(
        20,
        'MQTT_CLIENT',
        "Connected with result code " + str(rc))


def connect_to_mqtt_broker():
    rc = mqttc.connect(host=mqtt_host, port=mqtt_port, keepalive=60, bind_address="")
    if rc == 0:
        log(
            20,
            'MQTT_CLIENT',
            'Connect to broker: {} on port: {:d} and topic: {}'.format(mqtt_host, mqtt_port, mqtt_topic)
        )
        mqttc.loop_start()
        time.sleep(.2)
    else:
        log(
            40,
            'MQTT_CLIENT',
            'Connection failed with status code: {:d}'.format(rc)
        )


mqttc.on_connect = on_connect
connect_to_mqtt_broker()

# APPacket
# Only fallback option!
# module = gs_config.getint('module')

# Initialize dependency's
preserver = Preserver(mqttc)
proto = CCPhyParser()
stats = RadioStats(proto)
dhcp = DHCP(proto)
parser = LineReader(stats, dhcp, preserver, proto)
gateway = GatewayHandler(proto, stats, dhcp, parser, mqttc)
app = Flask(__name__)

'''
############################################################
'''


@app.route('/', methods=['GET'])
def welcome():
    return 'Welcome, I`m the gateway server!'


'''
############################################################
'''


# MQTT
@app.route('/gateway/MQTT', methods=['POST'])
def mqtt_publish():
    request_data = json.loads(request.data)
    if request_data is None:
        return 'Body not defined!'

    if request.method == 'POST':
        topic = request_data['topic']
        payload = request_data['payload']
        mqttc.publish(
            topic=topic,
            payload=json.dumps(payload),
            qos=0,
            retain=False
        )

        return json.dumps(payload)


'''
############################################################
'''


# BECN phyaddr                              (M mode)
@app.route('/gateway/BECN', methods=['POST'])
def becn():
    req_data = json.loads(request.data)

    if request.method == 'POST':
    
        addr = None
        module = None
        
        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # If phyaddr not defined, abort.
        if 'addr' not in req_data:
            return make_response(jsonify(FAILURE='No addr defined. For example "addr": 21 (8bit)'), 400)
        else:
            addr = req_data['phyaddr']

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        payload = proto.create_beacon_request(addr=addr)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
            return make_response(
                jsonify(SUCCESS='BECN send on address: {:d}'.format(addr)), 200
            )
        except Exception as err:
            return make_response(
                jsonify(FAILURE='{}'.format(err)), 400
            )


'''
############################################################
'''


# DUID Q seq                                (RR mode)
#   >> DUID R seq uid phyaddr
@app.route('/gateway/DUID', methods=['POST'])
def duid():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        addr = 0

        # Check if request have an json-body and an address option. 
        # If no option is defined, send to broadcast.
        if req_data is not None and 'addr' in req_data:
            addr = int(req_data['addr'])

        payload = proto.create_duid_request(addr=addr)
        preserver.publish_information()
        try:
            packet = APPacket(1, addr, payload)
            packet.send()
            packet = APPacket(2, addr, payload)
            packet.send()
            packet = APPacket(3, addr, payload)
            packet.send()
            packet = APPacket(4, addr, payload)
            packet.send()
            return make_response(
                jsonify(SUCCESS='DUID send on address: {:d}'.format(addr)), 200
            )
        except Exception as err:
            return make_response(
                jsonify(FAILURE='{}'.format(err)), 400
            )


'''
############################################################
'''


# SADR Q seq uid phyaddr                    (RR mode)
#   >> SADR R seq ACK
# SADR uid phyaddr                          (M mode)
@app.route('/gateway/SADR', methods=['POST'])
def sadr():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        uid = None
        addr = None
        newAddr = None
        module = None

        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # If uid not defined, abort.
        if 'uid' not in req_data:
            return make_response(jsonify(FAILURE='No uid defined. For example "uid": 21 (16bit)'), 400)
        else:
            uid = req_data['uid']

        # If phyaddr not defined, abort.
        if 'addr' not in req_data:
            return make_response(jsonify(FAILURE='No destination addr defined. For example "addr": 170 (8bit)'), 400)
        else:
            addr = req_data['addr']

        # If new_phyaddr not defined, abort.
        if 'newAddr' not in req_data:
            return make_response(jsonify(FAILURE='No new Address defined. For example "newAddr": 21 (16bit)'), 400)
        else:
            newAddr = req_data['newAddr']

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        seqnr = proto.get_seqnr()
        payload = proto.create_sadr_request(addr=addr, uid=uid, newaddr=newAddr)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
        except Exception as err:
            return make_response(
                jsonify(FAILURE='{}'.format(err)), 400
            )
        time.sleep(.1)
        reply = proto.get_by_seqnr(seqnr=seqnr)
        return make_response(
            jsonify(ack=str(reply)), 200
        )


'''
############################################################
'''


# CHNL Q seq channel                        (RR mode)
#   >> CHNL R seq ACK
# CHNL channel                              (M mode)
@app.route('/gateway/CHNL', methods=['POST'])
def chnl():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        channel = None
        module = None

        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # If channel not defined, abort.
        if 'channel' not in req_data:
            return make_response(jsonify(FAILURE='No channel defined. For example "channel": 0'), 400)
        else:
            channel = req_data['channel']

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        seqnr = proto.get_seqnr()
        # TODO: Why always addr=0? No possibility to only access phyNodes on spec. channel?
        payload = proto.create_chnl_request(addr=0, channel=channel)
        try:
            packet = APPacket(module, 0, payload)
            packet.send()
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)
        time.sleep(.1)
        reply = proto.get_by_seqnr(seqnr=seqnr)
        return make_response(
            jsonify(ack=str(reply)), 200
        )


'''
############################################################
'''


# SETI Q seq itemdescr [amount]             (RR mode)
#   >> SETI R seq
# SETI M itemdescr [energy]                 (M mode)
@app.route('/gateway/SETI', methods=['POST'])
def seti():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        addr = None
        itemdescr = None
        module = None
        amount = 0

        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # If addr not defined, abort
        if 'addr' not in req_data:
            return make_response(jsonify(FAILURE='No addr defined. For example "addr": 170'), 400)
        else:
            addr = int(req_data['addr'])
            if addr < 1:
                return make_response(
                    jsonify(FAILURE='Address is out of range. Please select an address greater as 0!'), 400
                )

        if 'itemdescr' not in req_data:
            return make_response(jsonify(FAILURE='No itemdescr defined. For example "itemdescr": 1010'), 400)
        else:
            itemdescr = int(req_data['itemdescr'])

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        if 'amount' not in req_data:
            return make_response(jsonify(FAILURE='No amount defined. For example "amout": 9'), 400)
        else:
            amount = req_data['amount']

        seqnr = proto.get_seqnr()
        payload = proto.create_set_item_request(addr, itemdescr, amount)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)
        time.sleep(.1)
        reply = proto.get_by_seqnr(seqnr=seqnr)
        return make_response(
            jsonify(ack=str(reply)), 200
        )


'''
############################################################
'''


# PING Q seq
@app.route('/gateway/PING', methods=['POST'])
def ping():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        addr = 0
        module = None

        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # If addr not defined, abort
        if 'addr' not in req_data:
            return make_response(jsonify(FAILURE='No addr defined. For example "addr": 170'), 400)
        else:
            addr = int(req_data['addr'])
            if addr < 1:
                return make_response(
                    jsonify(FAILURE='Address is out of range. Please select an address greater as 0!'), 400
                )

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        payload = proto.create_ping_request(0)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
            return make_response(jsonify(SUCCESS='PING send on address: {:2d}'.format(addr)), 200)
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)


'''
############################################################
'''


# POLL Q seq ordernumber itemdescr      (RR mode)
#   >> POLL R seq ordernumber amount phyaddr [energy]
@app.route('/gateway/POLL', methods=['POST'])
def poll():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        ordernumber = None
        itemdescr = None
        addr = 0

        # Check if request have an json-body
        if req_data is None:
            return make_response(jsonify(FAILURE='No data received'), 400)

        # Check if ordernumber is defined
        if 'ordernumber' not in req_data:
            return make_response(jsonify(FAILURE='Ordernumber is not defined!'), 400)
        else:
            ordernumber = req_data['ordernumber']

        # Check if itemdescr is defined
        if 'itemdescr' not in req_data:
            return make_response(jsonify(FAILURE='Ordernumber is not defined!'), 400)
        else:
            itemdescr = req_data['itemdescr']

        payload = proto.create_poll_request(addr, ordernumber, itemdescr)
        try:
            result = preserver.get_by_ordernumber(int(ordernumber))
            packet = APPacket(1, addr, payload)
            packet.send()
            packet = APPacket(2, addr, payload)
            packet.send()
            packet = APPacket(3, addr, payload)
            packet.send()
            packet = APPacket(4, addr, payload)
            packet.send()
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)

        time.sleep(1)

        result = preserver.get_by_ordernumber(int(ordernumber))
        if len(result) == 0:
            return make_response(jsonify(FAILURE='No data from phynodes received!'), 400)
        else:
            return Response(json.dumps(result), mimetype='application/json')


'''
############################################################
'''


# ISRT Q seq amount                         (RR mode)
#   >> ISRT R seq
# ISRT M amount                             (M mode)
@app.route('/gateway/ISRT', methods=['POST', 'GET'])
def isrt():
    pass


'''
############################################################
'''


# DLVR Q seq amount                         (RR mode)
#   >> DLVR R seq
# DLVR M amount                             (M mode)
@app.route('/gateway/DLVR', methods=['POST', 'GET'])
def dlvr():
    pass


'''
############################################################
'''


# ENUM Q seq                                (RR mode)
#   >> ENUM R seq itemdescr amount [phyaddr] ordernumber orderamount
@app.route('/gateway/ENUM', methods=['POST'])
def enum():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        addr = 0
        module = None

        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # Check if request have an address option. 
        # If no option is defined, send to broadcast.
        if 'addr' in req_data:
            addr = int(req_data['addr'])
            if addr < 0:
                return make_response(jsonify(FAILURE='Address is smaller then 0'), 400)

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        payload = proto.create_enum_request(addr=addr)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
            return make_response(
                jsonify(SUCCESS='ENUM send on address: {:2d}'.format(addr)), 200
            )
        except Exception as err:
            return make_response(
                jsonify(FAILURE='{}'.format(err)), 400
            )


'''
############################################################
'''


# RSTO M phyaddr uid [energy]               (M mode)
@app.route('/gateway/RSTO', methods=['GET', 'DELETE'])
def rsto():
    req_data = json.loads(request.data)

    if request.method == 'GET':
        # Check if request have an json-body and the instructions
        if req_data is None:
            return make_response(jsonify(FAILURE='No data received'), 400)

        # If no phyaddr defined, abort. This address is needed for matchinh the right restore message.
        if 'phyaddr' not in req_data:
            return make_response(jsonify(FAILURE='No phyaddr defined'), 400)
        else:
            phyaddr = int(req_data['phyaddr'])

        # Collect the information from the preserver
        result = preserver.get_rsto_status(phyaddr)
        if result:
            return make_response(jsonify(rsto=result), 200)
        else:
            return make_response(jsonify(rsto=result), 400)
    elif request.method == 'DELETE':
        payload = proto.create_butn_request(addr=0, buttonid=1)
        try:
            packet = APPacket(1, 0, payload)
            packet.send()
            packet = APPacket(2, 0, payload)
            packet.send()
            packet = APPacket(3, 0, payload)
            packet.send()
            packet = APPacket(4, 0, payload)
            packet.send()
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)

        time.sleep(1)
        preserver.reset()
        return make_response(jsonify(SUCCESS='True'), 200)


'''
############################################################
'''


# BATS Q seq energy                         (RR mode)
#   >> BATS R seq
# BATS M energy                             (M mode)
@app.route('/gateway/BATS', methods=['POST'])
def bats():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        energy = None
        addr = None
        module = None

        # Check if request have an json-body
        if req_data is None:
            return make_response(jsonify(FAILURE='No data received'), 400)

        # Check if energy is defined
        if 'energy' not in req_data:
            return make_response(jsonify(FAILURE='Energy is not defined!'), 400)
        else:
            energy = req_data['energy']

        # Check if addr is defined
        if 'addr' not in req_data:
            return make_response(jsonify(FAILURE='addr is not defined!'), 400)
        else:
            addr = req_data['addr']

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        payload = proto.create_bats_request(addr, energy)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
            return make_response(jsonify(SUCCESSFULL='True'), 200)
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)


'''
############################################################
'''


# BUTN Q seq buttonid                       (RR mode)
#   >> BUTN R seq 
# BUTN M buttonId                           (M mode)
@app.route('/gateway/BUTN', methods=['POST'])
def butn():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        addr = 0
        module = None

        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # Check if request have an address option. 
        # If no option is defined, send to broadcast.
        if 'addr' in req_data:
            addr = int(req_data['addr'])
            if addr < 0:
                return make_response(jsonify(FAILURE='Address is smaller then 0'), 400)

        if 'buttonId' not in req_data:
            return make_response(jsonify(FAILURE='No buttonId defined. For example "buttonId": 1'), 400)
        else:
            buttonId = int(req_data['buttonId'])

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        payload = proto.create_butn_request(addr=addr, buttonid=buttonId)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
            return make_response(
                jsonify(SUCCESS='BUTN send on address: {:2d}'.format(addr)), 200
            )
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)


'''
############################################################
'''


# LOWE M buttonId                           (M mode) 
# !!!From phynode to AP!!!
@app.route('/gateway/LOWE', methods=['GET'])
def lowe():
    pass


'''
############################################################
'''


# FULE M phyaddr [energy]                   (M mode) 
# !!!From phynode to AP!!!
@app.route('/gateway/FULE', methods=['GET'])
def fule():
    pass


'''
############################################################
'''


# RSVE Q seq ordernumber amount             (RR mode)
#   >> RSVE R seq 
# RSVE M ordernumber amount                 (M mode)
@app.route('/gateway/RSVE', methods=['POST', 'GET'])
def rsve():
    req_data = json.loads(request.data)

    if request.method == 'POST':
        addr = None
        ordernumber = None
        module = None
        amount = 0

        # If no data in body defined, abort.
        if req_data is None:
            return make_response(jsonify(FAILURE='No body defined'), 400)

        # If addr not defined, abort
        if 'addr' not in req_data:
            return make_response(jsonify(FAILURE='No addr defined. For example "addr": 170(8bit)'), 400)
        else:
            addr = int(req_data['addr'])
            if addr < 1:
                return make_response(
                    jsonify(FAILURE='Address is out of range. Please select an address greater as 0!'), 400
                )

        if 'ordernumber' not in req_data:
            return make_response(jsonify(FAILURE='No ordernumber defined. For example "ordernumber": 21'), 400)
        else:
            ordernumber = int(req_data['ordernumber'])

        if 'amount' not in req_data:
            return make_response(jsonify(FAILURE='No amount defined. For example "amout": 9'), 400)
        else:
            amount = req_data['amount']

        # If module not defined, abort.
        if 'module' not in req_data:
            return make_response(jsonify(FAILURE='No module (antenna) defined. For example "module": 2'), 400)
        else:
            module = req_data['module']

        preserver.rsve_by_phyaddr(addr, ordernumber)
        payload = proto.create_reserve_request(addr, ordernumber, amount)
        try:
            packet = APPacket(module, addr, payload)
            packet.send()
            return make_response(
                jsonify(SUCCESS='RSVE send on address: {:d}'.format(addr)), 200
            )
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)

        # Unreachable code
        #time.sleep(1)

        #result = preserver.is_blocked(phyaddr)
        #if not result:
        #    return make_response(jsonify(blocked=result), 400)
        #else:
        #    return Response(jsonify(blocked=result), mimetype='application/json')


'''
############################################################
'''

# TODO: Why always 0?

# RESE M phyaddr uid [energy]               (M mode)
@app.route('/gateway/RESE', methods=['DELETE'])
def rese():
    if request.method == 'DELETE':
        payload = proto.create_butn_request(addr=0, buttonid=1)
        try:
            packet = APPacket(2, 0, payload)
            packet.send()
        except Exception as err:
            return make_response(jsonify(FAILURE='{}'.format(err)), 400)

        time.sleep(1)
        preserver.reset()
        return make_response(jsonify(SUCCESS='True'), 200)


'''
############################################################
'''


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Route not found'}), 404)


'''
############################################################
'''

if __name__ == '__main__':
    log(
        20,
        'GATEWAY_SERVER',
        'Prozess start with {}PID {:d}{}'.format(
            shell_font_style.BOLD,
            os.getpid(),
            shell_font_style.END))

    # Start the radio driver as subprozess
    # radio_driver = subprocess.run(['../../../../SFB/CC1200_interface/SFBGateway.app', str(module), '0'], shell=True)
    # proc = subprocess.call(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # td = subprocess.call(['sudo ../../../../SFB/CC1200_interface/SFBGateway.app', str(-1), str(0)], shell=True)

    try:
        gateway.run()
    except IOError as err:
        log(40, 'GATEWAY_SERVER', '{}'.format(str(err)))
        sys.exit(-1)

    time.sleep(1)

    connect_to_mqtt_broker()

    app.run(host='0.0.0.0', port=8760)
