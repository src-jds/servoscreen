#!/usr/bin/python

import sys

import serial

import servocomms

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
servo = servocomms.ServoCIE(ser)

print('\nCommanding CIE to enter EXTENDED mode.')
servo.generalCall()

servo.readCIType()

print('\nSetting CIE to highest protocol version.')
ret = servo.getMaxProtocol()
if ret != servo.Error.CHKSUM:
    print('\nHighest protocol version available is ' + str(ret, 'ASCII'))
else:
    print('\nFailed to get CIE protocol version.')

servo.setProtocol(ret)

print('\nEstablishing data tables.')
servo.defineAcquiredData('B', [200, 205, 209])
servo.defineAcquiredData('C', [100])

print('\nReading Servo data.')
servo.readAcquiredData('B')
servo.readAcquiredData('C', 100, 1, 4)

ser.close()