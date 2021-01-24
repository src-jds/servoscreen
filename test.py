#!/usr/bin/python

import sys

from datetime import datetime

import serial

import ciedriver

# serial configuration
print('\nOpening serial _port.')
try:
    ser = serial.Serial(
        port='COM10',
        baudrate=9600,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        #xonxoff=True,
        timeout=1
    )
except serial.SerialException as err:
    sys.stderr.write('\nCould not open serial _port: {}\n'.format(err))
    sys.exit(1)

print('\nInitialising Servo Comms.')
servo = ciedriver.ServoCIE(ser)

print('\nCommanding CIE to enter EXTENDED mode.')
servo.generalCall()

servo.readCIType()

print('\nSetting CIE to highest protocol version.')
ret = servo.getMaxProtocol()
if ret != servo.Error.RX_CHKSUM:
    print('\nHighest protocol version available is ' + str(ret, 'ASCII'))
else:
    print('\nFailed to get CIE protocol version.')

servo.setProtocol(ret)

print('\nEstablishing data tables.')
servo.defineAcquiredData('B', [200, 205, 209])
servo.defineAcquiredData('C', [100])

print('\nReading Servo data channel configurations.')
for key in servo.openChannels:
    for channel in servo.openChannels[key]:
        print('\n%s : %s' % (key, channel))
        servo.readChannelConfig(channel)

for item in servo.openChannels:
    print(item, servo.openChannels[item])

#print('\nReading Servo data.')
#servo.readDataOnce('B')
#servo.readDataOnce('C', 1000, 1, 2)

print('\nStarting data stream.')
servo.startDataStream()

try:
    while True:
        if ser.in_waiting:
            servo.readDataStream()
            print(datetime.now())
            for category in servo.data:
                print(category, ':', servo.data[category])
except KeyboardInterrupt:
    ser.close()
    sys.exit()
