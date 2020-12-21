#!/usr/bin/python3

import enum


class ServoCIE(object):
    _eot = b'\x04'
    _endFlag = b'\x7F'
    _dataCategories = ('C', 'UC', 'B', 'T', 'S', 'A')

    class Debug(enum.Enum):
        NONE = 0
        INFO = 1
        FULL = 2

    _debug = Debug.INFO

    class Error(enum.Enum):
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
        self._extendedModeActive = False

    def calculateChecksum(self, message):
        """
        Determines checksum value.
        """
        checksum = 0

        for i in range(len(message)):
            checksum = checksum ^ message[i]

        """ 
        Ensure checksum is a byte string with upper-case chars and 
        is at least 2 ASCII chars long, ie: b'09' NOT b'9' 
        """
        checksum = bytes(hex(checksum), 'ASCII')[2:].upper().zfill(2)

        if self._debug.value >= self.Debug.FULL.value:
            print('Checksum: ' + str(checksum))

        return checksum

    def checkErrors(self, message):
        """
        Checks received messages for errors.
        """
        if message[:2] == b'ER':
            return self.Error(int(message[2:4]))
        else:
            return self.Error.NO_ERROR

    def flushbuffer(self):
        self._debug

    def readcitype(self):
        """
        When CIE is in BASIC mode, set CIE to EXTENDED mode. Also used to check Servo<->CIE internal
        communication status.
        """
        message = b'RCTY'

        message = message + self.calculateChecksum(message) + self._eot

        if self._debug.value >= self.Debug.INFO.value:
            print('Message to Servo: ' + str(message))

        self.port.write(message)

        response = self.port.read_until(self._eot)

        if self._debug.value >= self.Debug.INFO.value:
            print('Servo response: ' + str(response))

        if response[7] - 48 == 0:
            if not self._extendedModeActive:
                self._extendedModeActive = True
                if self._debug.value >= self.Debug.INFO.value:
                    print('Servo EXTENDED mode activated.')

            return self.Error.NO_ERROR
        else:
            return self.Error.CIE_ERROR

    def generalCall(self):
        """
        Sends HELLO command, used to check Servo(CIE)<->External equipment connection. When the CIE is
        in EXTENDED mode, this command will cause it to return to BASIC mode.
        """
        message = b'HO'

        message = message + self._eot

        if self._debug.value >= self.Debug.INFO.value:
            print('Message to Servo: ' + str(message))

        self.port.write(message)

        response = self.port.read_until(self._eot)

        if self._debug.value >= self.Debug.INFO.value:
            print('Servo response: ' + str(response))

        if b'900PCI' in response:
            if self._extendedModeActive:
                self._extendedModeActive = False
                if self._debug.value >= self.Debug.INFO.value:
                    print('Servo EXTENDED mode deactivated.')

        return self.checkErrors(response)

    def getmaxprotocol(self):
        """
        EXTENDED MODE CMD. Requests highest available CIE protocol version available from Servo.
        """
        message = b'RHVE'

        message = message + self.calculateChecksum(message) + self._eot

        if self._debug.value >= self.Debug.INFO.value:
            print('Message to Servo: ' + str(message))

        self.port.write(message)

        response = self.port.read_until(self._eot)

        if self._debug.value >= self.Debug.INFO.value:
            print('Servo response: ' + str(response))

        if response[3:5] == self.calculateChecksum(response[:-3]):
            return response[:-3]
        else:
            return self.Error.CHKSUM

    def setProtocol(self, version):
        """
        EXTENDED MODE CMD. Configures CIE to use a specific protocol version.
        """
        message = b'SPVE' + bytes(version)

        message = message + self.calculateChecksum(message) + self._eot

        if self._debug.value >= self.Debug.INFO.value:
            print('Message to Servo: ' + str(message))

        self.port.write(message)

        response = self.port.read_until(self._eot)

        if self._debug.value >= self.Debug.INFO.value:
            print('Servo response: ' + str(response))

        return self.checkErrors(response)

    def defineaccuireddata(self, category, channels):
        """
        EXTENDED MODE CMD. Defines the data channels to be read from the Servo. Channels may contain
        curve, breath, trend, settings and alarm data.
        Only 4 curve channels can be selected, for all others the limit is 50 for each category.
        Curves = 'C'
        Breath = 'B'
        Trend = 'T'
        Settings = 'S'
        Alarms = 'A'
        """
        if category not in self._dataCategories:
            return self.Error.INVALID

        message = b'SDAD' + bytes(category.upper(), 'ascii')

        for channel in channels:
            message = message + b'%i' % channel

        message = message + self.calculateChecksum(message) + self._eot

        if self._debug.value >= self.Debug.INFO.value:
            print('Message to Servo: ' + str(message))

        self.port.write(message)

        response = self.port.read_until(self._eot)

        if self._debug.value >= self.Debug.INFO.value:
            print('Servo response: ' + str(response))

        return self.checkErrors(response)

    def readAccuiredData(self, category, channel='', trig='', trigend=''):
        """
        EXTENDED MODE CMD.
        """
        if category not in self._dataCategories:
            return self.Error.INVALID

        message = b'RADA' + bytes(category.upper(), 'ascii') \
                  + bytes(str(channel), 'ASCII') \
                  + bytes(str(trig), 'ASCII') \
                  + bytes(str(trigend), 'ASCII')

        message = message + self.calculateChecksum(message) + self._eot

        if self._debug.value >= self.Debug.INFO.value:
            print('Message to Servo: ' + str(message))

        self.port.write(message)

        response = self.port.read_until(self._endFlag)

        if self._debug.value >= self.Debug.INFO.value:
            print('Servo response: ' + str(response))

        return response[:-1]

    def streamAcquiredData(self):
        """
        """

    def getsamplingtime(self):
        """
        """

    def setsamplingtime(self):
        """
        """

    def getservotime(self):
        """
        """
