#! /usr/bin/python

import sys

import serial

from enum import Enum


class ServoCIE(object):
    _eot = b'\x04'
    _datacategories = ('C', 'B', 'T', 'S', 'A')
    _debug = True

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
        """ When CIE is in BASIC mode, set CIE to EXTENDED mode. Also used to check Servo<->CIE internal
        communication status.
        """
        message = b'RCTY'

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        response = self.port.read_until(self._eot)

        if self.debug:
            print(response)

        if response[7] - 48 == 0:
            if not self._extendedmodeactive:
                self._extendedmodeactive = True

            return self.Error.NO_ERROR
        else:
            return self.Error.CIE_ERROR

    def generalcall(self):
        """ Sends HELLO command, used to check Servo(CIE)<->External equipment connection. When the CIE is
        in EXTENDED mode, this command will cause it to return to BASIC mode.
        """
        message = b'HO'

        self.port.write(message + self._eot)

        response = self.port.read_until(self._eot)

        if self.debug:
            print(response)

        if b'900PCI' in response:
            if self._extendedmodeactive:
                self._extendedmodeactive = False

        return self.checkerrors(response)

    def getmaxprotocol(self):
        """ EXTENDED MODE CMD. Requests highest available CIE protocol version available from Servo. """
        message = b'RHVE'

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        response = self.port.read_until(self._eot)

        if self.debug:
            print(response)

        if message[-3:-1] == self.calculatechecksum(message[-3:]):
            return response[:-3]
        else:
            return self.Error.CHKSUM

    def setprotocol(self, version):
        """ EXTENDED MODE CMD. Configures CIE to use a specific protocol version. """
        message = b'SPVE' + bytes(version)

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        response = self.port.read_until(self._eot)

        if self.debug:
            print(response)

        return self.checkerrors(response)

    def definedata(self, category, channels):
        """ EXTENDED MODE CMD. Defines the data channels to be read from the Servo. Channels may contain
        curve, breath, trend, settings and alarm data.
        Only 4 curve channels can be selected, for all others the limit is 50 for each category.
        Curves = 'C'
        Breath = 'B'
        Trend = 'T'
        Settings = 'S'
        Alarms = 'A'
        """
        if category not in self._datacategories:
            return self.Error.INVALID

        message = b'SDAD' + bytes(category.upper(), 'ascii')

        for val in channels:
            message = message + b'%i' % val

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        response = self.port.read_until(self._eot)

        if self.debug:
            print(response)

        return self.checkerrors(response)

    def readdata(self, category):
        """ EXTENDED MODE CMD. """
        if category not in self._datacategories:
            return self.Error.INVALID

        message = b'RADA' + bytes(category.upper(), 'ascii')

        self.port.write(message + self.calculatechecksum(message) + self._eot)

        response = self.port.read_until(self._eot)

        if self.debug:
            print(response)



    def getdefineddata(self):
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
