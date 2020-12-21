#!/usr/bin/python

import sys

import serial

import servocomms

# serial configuration
print('\nOpening serial port.')
try:
    port = serial.Serial(
        port='COM10',
        baudrate=9600,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        #xonxoff=True,
        timeout=1
    )
except serial.SerialException as e:
    sys.stderr.write('\nCould not open serial port {}: {}\n'.format(port.name, e))
    sys.exit(1)

print('\nInitialising Servo Comms.')
servo = servocomms.ServoCIE(port)

print('\nCommanding CIE to enter EXTENDED mode.')
servo.generalCall()

servo.readcitype()

print('\nSetting CIE to highest protocol version.')
ret = servo.getmaxprotocol()
if ret != servo.Error.CHKSUM:
    print('\nHighest protocol version available is ' + str(ret, 'ASCII'))
else:
    print('\nFailed to get CIE protocol version.')

servo.setProtocol(ret)

print('\nEstablishing data tables.')
servo.defineaccuireddata('B', [200, 205, 209])
servo.defineaccuireddata('C', [100])

print('\nReading Servo data.')
servo.readAccuiredData('B')
servo.readAccuiredData('UC', 100, 1, 4)

port.close()