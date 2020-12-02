#! /usr/bin/python

import sys

import serial

from enum import Enum


class ServoSerial(object):
    _eot = b'\x04'

    class Error(Enum):
        NO_ERROR = 0
        CIE_ERROR = 9
        INVALID = 10
        SYNTAX = 11
        OUT_OF_RANGE = 12
        NO_DATA = 13
        TREND_BUF_OVF = 14
        CH_UNDEFINED = 15
        CIE_NOTCONF = 16
        STANDBY = 17
        CHKSUM = 18
        BUFFER_FUll = 19

    def __init__(self, port):
        self.port = port
        self._extendedmodeactive = False

    @staticmethod
    def calculatechecksum(message):
        """ Determines checksum value. """
        checksum = 0

        for i in range(len(message)):
            checksum = checksum ^ message[i]

        return checksum

    def checkerrors(self, message):
        """ Checks received messages for errors. """
        if message[:2] == b'ER':
            return self.Error(int(message[2:4]))
        else:
            return self.Error.NO_ERROR

    def readcitype(self):
        """ When CIE is in BASIC mode, set CIE to EXTENDED mode. Also used to check Servo internal communication
        status.
        """
        message = b'RCTY'

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        response = self.port.read_until(self._eot)

        if response[7] - 48 == 0:
            if not self._extendedmodeactive:
                self._extendedmodeactive = True

            return self.Error.NO_ERROR
        else:
            return self.Error.CIE_ERROR

    def getmaxprotocol(self):
        """ Requests highest available CIE protocol version available from Servo. EXTENDED MODE CMD """
        message = b'RHVE'

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        response = self.port.read_until(self._eot)

        if message[-3:-1] == self.calculatechecksum(message[-3:]):
            return response[:-3]
        else:
            return self.Error.CHKSUM

    def setprotocol(self, version):
        """ Configures CIE to use a specific protocol version. EXTENDED MODE CMD """
        message = b'SPVE' + bytes(version)

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        return self.checkerrors(self.port.read_until(self._eot))

    def definebreath(self):
        """  """

    def readbreath(self):
        """  """

    def getsamplingtime(self):
        """  """

    def setsamplingtime(self):
        """  """

    def definecurve(self):
        """  """

    def readcurve(self):
        """  """

    def getservotime(self):
        """  """


# serial configuration
try:
    ser = serial.Serial(
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

ser.close()
