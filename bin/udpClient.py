#!/usr/bin/python3
# -*- coding: utf-8 -*-

from time import sleep
import socket
import signal
import json



def main():
    print("start udp-client...")
    server_addr = "localhost"
    server_port = 26106
    # socket machen
    sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM)
    addr = (server_addr,server_port)

    try:
        print("get alert-01 states...")
        req = dict()
        req['get'] = [ 'alert-01' ]
        msgb = json.dumps(req).encode(encoding='utf-8')
        print("send data to server: <%s>..." % msgb.decode('utf-8'))
        sent = sock.sendto(msgb, addr)
        print("await response...")
        data, server = sock.recvfrom(4094)
        rec_msg = data.decode('utf-8')
        print("recived {}".format(rec_msg))
        print("get alert-01 states...OK")

        # print("get all states...")
        # req = dict()
        # req['get'] = [ 'all' ]
        # msgb = json.dumps(req).encode(encoding='utf-8')
        # print("send data to server: <%s>..." % msgb.decode('utf-8'))
        # sent = sock.sendto(msgb, addr)
        # print("await response...")
        # data, server = sock.recvfrom(4094)
        # rec_msg = data.decode('utf-8')
        # print("recived {}".format(rec_msg))
        # print("get all states...OK")

        # sleep(10)

        #print("get single states...")
        #req = dict()
        #req['get'] = [ {'channel': 'GR00'}, {'channel': 'GR01'}, {'name': 'Garage hinten'} ]
        #msgb = json.dumps(req).encode(encoding='utf-8')
        #print("send data to server: <%s>..." % msgb.decode('utf-8'))
        #sent = sock.sendto(msgb, addr)
        #print("await response...")
        #data, server = sock.recvfrom(4094)
        #rec_msg = data.decode('utf-8')
        #print("recived {}".format(rec_msg))
        #print("get single states...OK")

        # sleep(10)

        # req = dict()
        # req['set'] = [ { 'name': 'Schlafzimmer','state': 'down' }, { 'name': 'Flur','state': 'down' }, {'channel': 'GR01','state': 'down' }, {'channel': 'GR03','state': 'down' } ]
        # msgb = json.dumps(req).encode(encoding='utf-8')
        # print("send data to server: <%s>..." % msgb.decode('utf-8'))
        # sent = sock.sendto(msgb, addr)
        # print("await response...")
        # data, server = sock.recvfrom(4094)
        # rec_msg = data.decode('utf-8')
        # print("recived {}".format(rec_msg))

        # sleep(30)

        # req = dict()
        # req['set'] = [  {'channel': 'GR00','state': 'up' }, {'channel': 'GR01','state': 'up' } ]
        # msgb = json.dumps(req).encode(encoding='utf-8')
        # print("send data to server: <%s>..." % msgb.decode('utf-8'))
        # sent = sock.sendto(msgb, addr)
        # print("await response...")
        # data, server = sock.recvfrom(4094)
        # rec_msg = data.decode('utf-8')
        # print("recived {}".format(rec_msg))


        # req = dict()
        # req['set'] = [ {'channel': 'GR00','state': 'down' }, {'channel': 'GR01','state': 'down' } ]
        # msgb = json.dumps(req).encode(encoding='utf-8')
        # print("send data to server: <%s>..." % msgb.decode('utf-8'))
        # sent = sock.sendto(msgb, addr)
        # print("await response...")
        # data, server = sock.recvfrom(4094)
        # rec_msg = data.decode('utf-8')
        # print("recived {}".format(rec_msg))

    finally:
        print("close socket...")
        sock.close()
    print("END...")


if __name__ == '__main__':
    main()
