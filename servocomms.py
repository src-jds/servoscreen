#!/usr/bin/python3

import enum

import logging


class ServoCIE(object):
    _endOfTransmission = b'\x04'
    _endFlag = b'\x7F'
    _phaseFlag = b'\x81'
    _valueFlag = b'\x80'
    _errorFlag = b'\xE0'
    _inspPhase = b'\x10'
    _pausePhase = b'\x20'
    _expPhase = b'\x30'

    _dataCategories = ('C', 'B', 'T', 'S', 'A')

    class Debug(enum.Enum):
        NONE = 0
        INFO = 1
        FULL = 2

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
        TX_CHKSUM = 18
        BUFFER_FUll = 19
        RX_CHKSUM = 20

    def __init__(self, port):
        self._port = port
        self._extendedModeActive = False
        self._debug = self.Debug.INFO
        self._openChannels = {category: [] for category in self._dataCategories}

    @staticmethod
    def _calculateChecksum(message):
        """
        Determines checksum value for a given message.
        """
        checksum = 0
        for i in range(len(message)):
            checksum = checksum ^ message[i]
        # Ensure checksum is a byte string with upper-case chars and is at least 2 ASCII chars long, ie: b'09' NOT b'9'
        checksum = bytes(hex(checksum), 'ASCII')[2:].upper().zfill(2)
        logging.debug('Checksum: ' + str(checksum, 'ASCII'))
        return checksum

    def _checkErrors(self, message):
        """
        Check received messages for errors.
        """
        if message[:2] == b'ER':
            status = self.Error(int(message[2:4]))
            logging.error('Error code in received message: ' + status)
            return status
        elif message[-3:-1] != self._calculateChecksum(message[:-3]):
            logging.error('Last received message failed checksum validation. Received checksum was ' +
                          str(message[-3:-1], 'ASCII') + ', calculated checksum is ' +
                          str(self._calculateChecksum(message[:-3]), 'ASCII') + '.')
            return self.Error.RX_CHKSUM
        else:
            return self.Error.NO_ERROR

    def flushBuffer(self):
        pass

    def readCIType(self):
        """
        When CIE is in BASIC mode, set CIE to EXTENDED mode. Also used to check Servo<->CIE internal communication
        status.
        """
        logging.info('Reading Servo CI type.')

        message = b'RCTY'
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logging.debug('Message to Servo: ' + str(message, 'ASCII'))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logging.debug('Servo response: ' + str(response, 'ASCII'))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            if response[7] == '0':
                if not self._extendedModeActive:
                    self._extendedModeActive = True
                    logging.info('Servo EXTENDED mode activated.')
                else:
                    logging.info('Servo already in EXTENDED mode, internal communication okay.')
                return status
            else:
                logging.warning('Servo<->CIE internal communication error.')
                return self.Error.CIE_ERROR
        else:
            logging.warning('Failed to read CI type with error ' + status + '.')
            return status

    def generalCall(self):
        """
        Sends HELLO command, used to check Servo(CIE)<->External equipment connection. When the CIE is in EXTENDED
        mode, this command will cause it to return to BASIC mode.
        """
        logging.info('Sending general call.')

        message = b'HO'
        message = message + self._endOfTransmission

        logging.debug('Message to Servo: ' + str(message, 'ASCII'))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logging.debug('Servo response: ' + str(response, 'ASCII'))

        status = self._checkErrors(response)
        if b'900PCI' in response:
            if self._extendedModeActive:
                self._extendedModeActive = False
                logging.info('Servo EXTENDED mode deactivated.')
            else:
                logging.info('CIE<->external equipment communication okay.')
        else:
            logging.error('General call failed with error ' + status + '. Check external equipment connection to Servo.')

        return status

    def getMaxProtocol(self):
        """
        EXTENDED MODE CMD. Requests highest available CIE protocol version available from Servo.
        """
        logging.info('Getting highest available protocol version available.')

        message = b'RHVE'
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logging.debug('Message to Servo: ' + str(message, 'ASCII'))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logging.debug('Servo response: ' + str(response, 'ASCII'))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            logging.info('Highest available protocol version is ' + str(response[:-3], 'ASCII') + '.')
            return response[:-3]
        else:
            logging.warning('Failed to get highest protocol version.')
            return status

    def setProtocol(self, version):
        """
        EXTENDED MODE CMD. Configures CIE to use a specific protocol version.
        """
        logging.info('Setting CIE protocol version.')

        message = b'SPVE' + bytes(version)
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logging.debug('Message to Servo: ' + str(message, 'ASCII'))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logging.debug('Servo response: ' + str(response, 'ASCII'))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            logging.info('Servo CIE set to protocol version ' + str(version, 'ASCII') + '.')
        else:
            logging.warning('Failed to set CIE protocol version. ' + status)

        return status

    def defineAcquiredData(self, category, channels=[]):
        """
        EXTENDED MODE CMD. Defines the data channels to be read from the Servo. Channels may contain curve, breath,
        trend, settings and alarm data. Only 4 curve channels can be selected, for all others the limit is 50 channels.

        Curves = 'C'
        Breath = 'B'
        Trend = 'T'
        Settings = 'S'
        Alarms = 'A'
        """
        logging.info('Defining data acquisition tables.')

        if category not in self._dataCategories:
            logging.warning('Incorrect data category given.')
            return self.Error.INVALID

        message = b'SDAD' + bytes(category.upper(), 'ASCII')

        channels = list(channels)  # Ensures channels are presented as a <mutable> list.
        for channel in channels:
            message = message + b'%i' % channel

        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logging.debug('Message to Servo: ' + str(message, 'ASCII'))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logging.debug('Servo response: ' + str(response, 'ASCII'))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            if len(channels) > 0:  # Defining 0 channels clears previously defined data acquisition table.
                self._openChannels[category] = channels
                logging.info('Data channels ' + category + str(channels) + ' opened.')
            else:
                self._openChannels[category] = []
                logging.info('Closing ' + category + ' data channels.')
        else:
            logging.warning('Failed to define data acquisition table. ' + status)

        """
        Example _openChannels structure
        
        _openChannels = {'C': [],
                         'B': [200, 205, 209], 
                         'T': [], 
                         'S': [], 
                         'A': []
                         }
        """
        return status

    def readAcquiredData(self, category, samples='', trig='', trigend=''):
        """
        EXTENDED MODE CMD. This command reads the data, i.e. curve-, breath-, settings-, trend- or alarm data,
        according to the channel table setup via the command Set Data Acquisition Definition.
        """
        logging.info('Reading defined data channels.')

        category = category.upper()
        if category not in self._dataCategories:
            logging.warning('Incorrect data category given.')
            return self.Error.INVALID

        if category == 'C':  # Reading data uses category 'UC' rather than 'C'. Everywhere else uses 'C'.
            category = 'UC'

        message = b'RADA' + bytes(category, 'ASCII') \
                          + bytes(str(samples), 'ASCII') \
                          + bytes(str(trig), 'ASCII') \
                          + bytes(str(trigend), 'ASCII')

        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logging.debug('Message to Servo: ' + str(message, 'ASCII'))
        self._port.write(message)

        response = self._port.read_until(self._endFlag)
        logging.debug('Servo response: ' + str(response, 'ASCII'))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            logging.info('Successfully read defined data channels.')
            return response[:-1]
        else:
            logging.warning('Failed to read defined data channels. ' + status)
            return status

    def streamAcquiredData(self):
        """
        """

    def readChannelConfig(self, channel):
        """
        EXTENDED MODE CMD. This command reads the channel configuration, e.g. gain, offset, either for a specific
        channel or for all available channels.
        """
        logging.info('Reading defined channel configurations.')

        message = b'RCCO' + bytes(channel, 'ASCII')
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logging.debug('Message to Servo: ' + str(message, 'ASCII'))
        self._port.write(message)

        response = self._port.read_until(self._endFlag)
        logging.debug('Servo response: ' + str(response, 'ASCII'))

        """
        Example _openChannels structure
                                <ch_num>,<gain>,<offset>,<unit>,<type>,<name>
        _openChannels = {'C': [],
                         'B': [('200', '+1000E-004', '+0000E+000', '06', 'BT'), 
                               ('205', '+1000E-004', '+0000E+000', '04', 'BT')
                               ('209', '+1000E-003', '+0000E+000', '07', 'BT')], 
                         'T': [], 
                         'S': [], 
                         'A': []
                         }
        """

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            logging.info('Successfully read defined data channels configurations.')
            return response[:-1]
        else:
            logging.warning('Failed to read defined data channels configurations. ' + status)
            return status

    def setsamplingtime(self):
        """
        """

    def getservotime(self):
        """
        """
