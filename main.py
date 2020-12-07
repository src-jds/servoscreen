#! /usr/bin/python

import sys

import serial

import servocomms

# serial configuration
print('Opening serial port.')
try:
    port = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate=9600,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        #xonxoff=True,
        timeout=1
    )
except serial.SerialException as e:
    sys.stderr.write('Could not open serial port {}: {}\n'.format(ser.name, e))
    sys.exit(1)

print('Initialising Servo Comms.')
servo = servocomms.ServoCIE(port)

print('Commanding CIE to enter EXTENDED mode.')
print(servo.generalcall())

print(servo.readcitype())

print('Setting CIE to highest protocol version.')
ret = servo.getmaxprotocol()
if ret not in servo.Error:
    print('Highest protocol version available is ' + ret)
else:
    print('Failed to get CIE protocol version.')

print(servo.setprotocol(ret))

print('Establishing data tables.')
print(servo.definedata('B', [200, 205, 209]))

print('Reading Servo data.')
print(servo.readdata())

port.close()