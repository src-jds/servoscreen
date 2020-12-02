#! /usr/bin/python

import sys
import time
import serial

print('===== Servo CIE test program =====\n')

print('Conecting to serial port.')
print('8E1, 9600 baud.')
#serial configuration
try:
	ser = serial.Serial(
		port='/dev/ttyUSB0',
		baudrate=9600,
		parity=serial.PARITY_EVEN,
		stopbits=serial.STOPBITS_ONE,
		bytesize=serial.EIGHTBITS,
#		xonxoff=True,
		timeout=1
	)
except serial.SerialException as e:
	sys.stderr.write('Could not open serial port {}: {}\n'.format(ser.name, e))
	sys.exit(1)

if ser.isOpen():
	print('Serial port open.\n')

print('Sending HELLO command, HO.')
print('Expected response: 900PCI')
ser.write(b'HO\x04')

print('Vent response: ' + str(ser.read_until('\x04')) + '\n')


print('Sending BATTERY CHECK command, BC')
print('Expected response: 380')
ser.write(b'BC\x04')

print('Vent Response: ' + str(ser.read_until('\x04')) + '\n')



print('Closing serial port')
print('===== End Servo CIE test program =====')

ser.close()
