###############################################################################
## All code excluding the websocket sections was written by Chung-Hay Luk.
##  Copyright 2013
##  Licensed under the Apache License, Version 2.0 (the "License").
##  See below for license details.
##
## Websocket sections of the code (classes, creating factory sections) are
## modified from example code for AutobahnPython found here:
## https://github.com/tavendo/AutobahnPython/blob/master/examples/websocket/broadcast/server.py
##
##  It is licensed as such:
##
##  Copyright 2011,2012 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import argparse
import json
import serial
import sys
import threading
from autobahn import websocket
from twisted.internet import reactor
from twisted.python import log


class BroadcastServerProtocol(websocket.WebSocketServerProtocol):

   def onOpen(self):
      self.factory.register(self)

   def onMessage(self, msg, binary):
      if not binary:
         self.factory.broadcast("'%s' from %s" % (msg, self.peerstr))

   def connectionLost(self, reason):
      websocket.WebSocketServerProtocol.connectionLost(self, reason)
      self.factory.unregister(self)


class BroadcastServerFactory(websocket.WebSocketServerFactory):
   """
   Simple broadcast server broadcasting any message it receives to all
   currently connected clients.
   """

   def __init__(self, url, debug = False, debugCodePaths = False):
      websocket.WebSocketServerFactory.__init__(self, url, debug=debug, 
                                      debugCodePaths=debugCodePaths)
      self.clients = []
      self.tickcount = 0
      self.tick()

   def tick(self):
      self.tickcount += 1
      self.broadcast("'tick %d' from server" % self.tickcount)
      reactor.callLater(1, self.tick)

   def register(self, client):
      if not client in self.clients:
         print "registered client " + client.peerstr
         self.clients.append(client)

   def unregister(self, client):
      if client in self.clients:
         print "unregistered client " + client.peerstr
         self.clients.remove(client)

   def broadcast(self, msg):
      print "broadcasting message '%s' .." % msg
      for c in self.clients:
         c.sendMessage(msg)
         print "message sent to " + c.peerstr


# Read serial data.
def readSerialData(serial_input, factory):
  while True:
    data = serial_input.readline().strip()
    
    # Check that data is formatted correctly.
    try:
      obj = validateData(data)
    except ValueError, e:
      print e
    else:
      # Broadcast json data for websocket.
      factory.broadcast(obj)


# Validate the serial data.
def validateData(data):
  # Check that data is in proper json format.
  try:
    obj = json.loads(data)
  except ValueError:
    raise ValueError, "Invalid json data: " + data

  # Check object is dictionary.
  if not isinstance(obj, dict):
    raise ValueError, "Object is not a dictionary"

  # Validate desired keys in object.
  keys = ('clear', 'red', 'green', 'blue')
  missing_keys = []
  for key in keys:
    if key not in obj:
      missing_keys.append(key)
      
  if missing_keys:
    raise ValueError, "Missing keys: %s" % missing_keys

  # Validate values of desired keys are integers.
  for key, value in obj.iteritems():
    if not isinstance(value, int):
      raise ValueError, "Value for %s is not an integer: %s" % (key, value)
  
  return obj


# Get input arguments.
def getArguments():
  # Enable parsing of arguments for this script.
  parser = argparse.ArgumentParser(description=
                                   'Set settings for running this script.')
  parser.add_argument('-s', '--serial_port_name',
                      default='/dev/ttyS0', #Arduino: '/dev/tty.usbmodemfa131',
                      help='serial port (default: /dev/tty.usbmodemfa131)')
  parser.add_argument('-b', '--baud_rate', type=int,
                      default=9600,
                      help='serial port\'s baud rate (default: 9600)')
  parser.add_argument('-a', '--address',
                      default='[::]',
                      help='address of interfaces (default: [::], all)')
  parser.add_argument('-p', '--port_number', type=int,
                      default=9000,
                      help='port number of server (default: 9000)')
  args = parser.parse_args()
  
  print 'Serial port %s at baud rate %d' % (args.serial_port_name, 
                                             args.baud_rate)
  print 'Interfaces %s on port %d' % (args.address, args.port_number)
  
  return args


def main():
  # Add fancy time logging.
  log.startLogging(sys.stdout)
  
  # Get arguments, some of which can be set as flag options.
  args = getArguments()
  
  # Create connection to serial port.
  serial_input = serial.Serial(args.serial_port_name, args.baud_rate)

  # Create factory.
  factory = BroadcastServerFactory("ws://%s:%d" % (args.address,
                                   args.port_number),
                                   debug = False)
  factory.protocol = BroadcastServerProtocol
  websocket.listenWS(factory)
  
  # Create one more thread. There's a main thread already.
  thread = threading.Thread(target=readSerialData, args=(serial_input, factory))
  thread.daemon = True
  thread.start()
  
  # Start handling requests across websocket.
  reactor.run()


if __name__ == '__main__':
  main()
