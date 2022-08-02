#!/usr/bin/python3

import enum
import binascii
import logging.config

logging.config.fileConfig('logging.ini', disable_existing_loggers=False)
logger = logging.getLogger(__name__)


class ServoCIE(object):
    _endOfTransmission = b'\x04'
    _escape = b'\x1B'
    _endFlag = b'\x7F'
    _phaseFlag = b'\x81'
    _valueFlag = b'\x80'
    _errorFlag = b'\xE0'
    _inspPhase = b'\x10'
    _pausePhase = b'\x20'
    _expPhase = b'\x30'

    dataCategories = ('C', 'B', 'T', 'S', 'A', 'E')

    units = {1: 'ml', 2: 'ml/s', 3: 'ml/min', 4: 'cmH2O', 5: 'ml/cmH2O', 6: 'breaths/min', 7: '%', 8: 'l/min',
             9: 'cmH2O/l/s', 10: 'mmHg', 11: 'kPa', 12: 'mbar', 13: 'mV', 14: 's', 15: 'l/s', 16: 'cmH2O/l', 17: 'l',
             18: 'Joule/l', 19: 'μV', 20: 'no unit', 21: 'cmH2O/μV', 22: 'breaths/min/l', 23: 'min'}

    ventilationMode = {2: "Pressure Control",
                       3: "Volume Control",
                       4: "Pressure Reg. Volume Control",
                       5: "Volume Support",
                       6: "SIMV (Vol. Cont.) + Pressure Support",
                       7: "SIMV (Pressure Control) + Pressure Support",
                       8: "Pressure Support / CPAP",
                       9: "Ventilation mode not supported by CIE",
                       10: "SIMV (Pressure Reg. Volume Control) + Pressure Support",
                       11: "Bivent",
                       12: "Pressure Control in NIV",
                       13: "Pressure Support / CPAP in NIV",
                       14: "Nasal CPAP",
                       15: "NAVA",
                       17: "NIV NAVA",
                       18: "Pressure Control, No Patient Trigger",
                       19: "Volume Control, No Patient Trigger",
                       20: "Pressure Reg. Volume Control, No Patient Trigger",
                       21: "Pressure Support / CPAP (Switch to Pressure Control if0 No Patient Trigger)",
                       22: "Volume Support (Switch to Volume Control if No Patient Trigger)",
                       23: "Volume Support (Switch to Pressure Reg. Volume Control if No Patient Trigger)"}

    class StreamStates(enum.Enum):
        END_FLAG = 0
        CHECK_SUM = 1
        ERROR = 2
        PHASE_FLAG = 3
        PHASE_DATA = 4
        CURVE_VAL_FLAG = 5
        CURVE_FIRST_BYTE = 6
        CURVE_SECND_BYTE = 7
        DIFF_VAL_BYTE = 8
        BREATH_FLAG = 9
        BREATH_FIRST_BYTE = 10
        BREATH_SECND_BYTE = 11
        SETTING_FIRST_BYTE = 12
        SETTING_SECND_BYTE = 13

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
        self._activeProtocolVersion = 0
        self.openChannels = {category: [] for category in self.dataCategories}
        self.channelData = {category: [] for category in self.dataCategories}
        self.category = ''
        self.phase = ''
        self.channelIndex = 0
        self.value = 0
        self.state = self.StreamStates.PHASE_FLAG
        self.message = ''

    @staticmethod
    def _calculateChecksum(message, binary=False):
        """
        Determines checksum value for a given message.
        """
        checksum = 0
        for i in range(len(message)):
            checksum = checksum ^ message[i]
        # Ensure checksum is a byte string with upper-case chars and is at least 2 ASCII chars long,
        # ie: b'09' NOT b'9'.
        checksum = bytes(hex(checksum), 'ASCII')[2:].upper().zfill(2)
        if binary:
            # Need b'\x09' not b'09'.
            checksum = bytes.fromhex(checksum.decode())
        logger.debug('Checksum: ' + str(checksum))
        return checksum

    def _checkErrors(self, message, binary=False):
        """
        Check received messages for errors.
        """
        if binary:  # Check for binary encoded errors.
            if message[:1] == self._errorFlag:
                status = self.Error(ord(message[1:2]))
                logger.error('Error code in received message: ' + status)
                return status
            calculatedchecksum = self._calculateChecksum(message[:-2], True)  # Send only message bytes.
            if message[-1:] != calculatedchecksum:
                logger.error('Last received message failed checksum validation. Received checksum was ' +
                             str(message[-1:]) + ', calculated checksum is ' +
                             str(calculatedchecksum) + '.')
                return self.Error.RX_CHKSUM
        else:  # Check for ASCII encoded errors.
            if message[:2] == b'ER':
                status = self.Error(int(message[2:4]))
                logger.error('Error code in received message: ' + status)
                return status
            calculatedchecksum = self._calculateChecksum(message[:-3])  # Send only message bytes.
            if message[-3:-1] != calculatedchecksum:
                logger.error('Last received message failed checksum validation. Received checksum was ' +
                             str(message[-1:]) + ', calculated checksum is ' +
                             str(calculatedchecksum) + '.')
                return self.Error.RX_CHKSUM
        return self.Error.NO_ERROR

    def readCIType(self):
        """
        When CIE is in BASIC mode, set CIE to EXTENDED mode. Also used to check Servo<->CIE internal communication
        status.
        """
        logger.info('Reading Servo CI type.')

        message = b'RCTY'
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            if response[7:8] == b'0':
                if not self._extendedModeActive:
                    self._extendedModeActive = True
                    logger.info('Servo EXTENDED mode activated.')
                else:
                    logger.info('Servo already in EXTENDED mode, internal communication okay.')
            else:
                logger.warning('Servo<->CIE internal communication error.')
                return self.Error.CIE_ERROR
        else:
            logger.warning('Failed to read CI type with error ' + str(status) + '.')
        return status

    def generalCall(self):
        """
        Sends HELLO command, used to check Servo(CIE)<->External equipment connection. When the CIE is in EXTENDED
        mode, this command will cause it to return to BASIC mode.
        """
        logger.info('Sending general call.')

        message = b'HO'
        message = message + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logger.debug('Servo response: ' + str(response))

        if b'900PCI' in response:
            if self._extendedModeActive:
                self._extendedModeActive = False
                logger.info('Servo EXTENDED mode deactivated.')
            else:
                logger.info('CIE<->external equipment communication okay.')
        else:
            logger.error('General call failed with return ' + str(response) +
                         '. Check external equipment connection to Servo.')
        return response

    def getMaxProtocol(self):
        """
        EXTENDED MODE CMD. Requests highest available CIE protocol version available from Servo.
        """
        logger.info('Getting highest available protocol version.')

        message = b'RHVE'
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            logger.info('Highest available protocol version is ' + str(response[:-3]) + '.')
            return response[:-3]
        else:
            logger.warning('Failed to get highest protocol version.')
            return status

    def setProtocol(self, version):
        """
        EXTENDED MODE CMD. Configures CIE to use a specific protocol version.
        """
        logger.info('Setting CIE protocol version.')

        message = b'SPVE' + bytes(version)
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            self._activeProtocolVersion = version
            logger.info('Servo CIE set to protocol version ' + str(version) + '.')
        else:
            logger.warning('Failed to set CIE protocol version. ' + str(status))
        return status

    def defineAcquiredData(self, category, channels):
        """
        EXTENDED MODE CMD. Defines the data channels to be read from the Servo. Channels may contain curve, breath,
        trend, settings and alarm data. Only 4 curve channels can be selected, for all others the limit is 50 channels.

        Curves = 'C'
        Breath = 'B'
        Trend = 'T'
        Settings = 'S'
        Alarms = 'A'

        :return response:
        """
        logger.info('Defining data acquisition tables.')

        if category not in self.dataCategories:
            logger.warning('Incorrect data category given.')
            return self.Error.INVALID

        message = b'SDAD' + bytes(category.upper(), 'ASCII')

        channels = list(channels)  # Ensures channels are presented as a <mutable> list.
        for channel in channels:
            message = message + b'%i' % channel

        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endOfTransmission)
        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            if len(channels) > 0:  # Defining 0 channels clears previously defined data acquisition table.
                self.openChannels[category] = channels
                self.channelData[category] = {channel: [] for channel in self.openChannels[category]}
                logger.info('Data channels ' + category + str(channels) + ' opened.')
            else:
                self.openChannels[category] = []
                logger.info('Closing ' + category + ' data channels.')
        else:
            logger.warning('Failed to define data acquisition table. ' + str(status))

        """
        Example openChannels and channelData structure
        
        openChannels = {'C': [],
                        'B': [200, 205, 209], 
                        'T': [], 
                        'S': [], 
                        'A': []
                        }
                        
        channelData = {'C': [],
                       'B': {200: [], 205: [], 209: []}, 
                       'T': [], 
                       'S': [], 
                       'A': []
                       }
        """
        return status

    def readDataOnce(self, category, samples='', trig='', trigend=''):
        """
        EXTENDED MODE CMD. This command reads the data, i.e. curve-, breath-, settings-, trend- or alarm data,
        according to the channel table setup via the command Set Data Acquisition Definition.

        :return response:
        :return status:
        """
        logger.info('Reading defined data channel values.')

        category = category.upper()
        if category not in self.dataCategories:
            logger.warning('Incorrect data category given.')
            return self.Error.INVALID

        if category == 'C':  # Reading data uses category 'UC' rather than 'C'. Everywhere else uses 'C'.
            category = 'UC'
            if samples == '':
                samples = '0000'
            else:
                samples = str(samples).zfill(4)
            if trig == '':
                trig = '0'
            if trigend == '':
                trigend = '0'

        message = b'RADA' + bytes(category, 'ASCII') \
                  + bytes(str(samples), 'ASCII') \
                  + bytes(str(trig), 'ASCII') \
                  + bytes(str(trigend), 'ASCII')

        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        if category == 'UC':
            self._port.timeout = 5
            response = self._port.read_until(self._endFlag)
            response = response + self._port.read(1)  # Get checksum.
            self._port.timeout = 1
        else:
            response = self._port.read_until(self._endOfTransmission)

        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            logger.info('Successfully read defined data channels.')
        else:
            logger.warning('Failed to read defined data channels. ' + str(status))
        return status

    def startDataStream(self):
        """
        EXTENDED MODE CMD. This method starts up the Servos data stream.

        This command reads the data continuously, i.e. curve-, breath-, settings-, trend- or alarm data according to the
        channel table set-up via the command Set Data Acquisition Definition.
        It is possible to read 1 or more curves at the same time. Up to 4 curves are allowed.
        New breath data is transmitted when the breath is finished, i.e. when a new breath is started.
        Breath/Setting/Alarm data package is transmitted when some of the data, according to the channel table set-up,
        is updated.
        The curve data are transferred continuously. However, if an alarm occurs, a setting change, new breath data
        are available or new one-minute trend are available, the curve data transfer will be temporarily interrupted.
        If buffer overflow occurs, ESC is received or ‘Standby’ mode set, the transmission stops.

        :return response:
        :return status:
        """
        logger.info('Starting acquired data stream.')

        message = b'RADC'
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

    def readDataStream(self):
        """
        EXTENDED MODE CMD. This method is called to read serial data from the Servo. The serial port should be checked
        for available data before calling this method.

        :return status:
        """
        logger.info('Reading data stream from Servo.')
        while self._port.in_waiting:
            thisByte = str.format('0x{:02x}', int(binascii.hexlify(self._port.read(1)), 16))
            logger.debug(str(thisByte))
            self.message = self.message + thisByte[2:]

            if self.state == self.StreamStates.PHASE_FLAG:
                if thisByte == hex(int(binascii.hexlify(self._phaseFlag), 16)):
                    self.category = 'C'
                    self.state = self.StreamStates.PHASE_DATA
                elif thisByte == hex(int(binascii.hexlify(self._valueFlag), 16)):
                    self.category = 'C'
                    self.state = self.StreamStates.CURVE_FIRST_BYTE
                elif thisByte == '0x42':  # b'B'
                    self.category = 'B'
                    self.state = self.StreamStates.BREATH_FIRST_BYTE
                    logger.debug('Reading breath data.')
                elif thisByte == '0x53':  # b'S'
                    self.category = 'S'
                    self.state = self.StreamStates.SETTING_FIRST_BYTE
                    logger.debug('Reading settings data.')
                else:
                    self.state = self.StreamStates.ERROR

            elif self.state == self.StreamStates.PHASE_DATA:
                if thisByte == '0x10':
                    self.phase = 'Inspiration'
                elif thisByte == '0x20':
                    self.phase = 'Pause'
                elif thisByte == '0x30':
                    self.phase = 'Expiration'
                else:
                    self.state = self.StreamStates.ERROR
                self.state = self.StreamStates.DIFF_VAL_BYTE
                logger.debug(self.phase + ' phase.')

            elif self.state == self.StreamStates.CURVE_VAL_FLAG:
                if thisByte == hex(int(binascii.hexlify(self._valueFlag), 16)):
                    self.state = self.StreamStates.CURVE_FIRST_BYTE
                else:
                    self.state = self.StreamStates.ERROR

            elif self.state == self.StreamStates.CURVE_FIRST_BYTE:
                self.value = thisByte[2:]
                self.state = self.StreamStates.CURVE_SECND_BYTE

            elif self.state == self.StreamStates.CURVE_SECND_BYTE:
                self.value = int(self.value + thisByte[2:], 16)
                # Get value parameters.
                channel = self.openChannels[self.category][self.channelIndex][0]
                # Add new value to buffer.
                self.channelData[self.category][channel].append(self.value)
                self.channelIndex = (self.channelIndex + 1) % len(self.openChannels['C'])
                logger.debug('Got data (' + str(self.value) + ') for channel number ' + str(channel) + '.')
                self.value = 0
                self.state = self.StreamStates.DIFF_VAL_BYTE

            elif self.state == self.StreamStates.DIFF_VAL_BYTE:
                if thisByte == hex(int(binascii.hexlify(self._valueFlag), 16)):
                    self.state = self.StreamStates.CURVE_FIRST_BYTE
                elif thisByte == hex(int(binascii.hexlify(self._endFlag), 16)):
                    self.state = self.StreamStates.CHECK_SUM
                elif thisByte == hex(int(binascii.hexlify(self._phaseFlag), 16)):
                    self.state = self.StreamStates.PHASE_DATA
                else:
                    # Get value parameters.
                    channel = self.openChannels[self.category][self.channelIndex][0]
                    lastValue = self.channelData[self.category][channel][-1]
                    # Compute new value.
                    self.value = int(thisByte, 16)
                    if self.value >= 0x82:
                        self.value = self.value - 256
                    # Add new value to buffer.
                    self.channelData[self.category][channel].append(lastValue + self.value)
                    self.channelIndex = (self.channelIndex + 1) % len(self.openChannels['C'])
                    logger.debug(
                        'Got differential data (' + str(self.value) + ') for channel number ' + str(channel) + '.')
                    self.value = 0

            elif self.state == self.StreamStates.BREATH_FIRST_BYTE:
                if thisByte == hex(int(binascii.hexlify(self._endFlag), 16)):
                    self.state = self.StreamStates.CHECK_SUM
                else:
                    self.value = thisByte[2:]
                    self.state = self.StreamStates.BREATH_SECND_BYTE

            elif self.state == self.StreamStates.BREATH_SECND_BYTE:
                self.value = int(self.value + thisByte[2:], 16)
                # Get value parameters.
                channel = self.openChannels[self.category][self.channelIndex][0]
                # Add new value to buffer.
                self.channelData[self.category][channel].append(self.value)
                self.channelIndex = (self.channelIndex + 1) % len(self.openChannels['B'])
                logger.debug('Got breath data (' + str(self.value) + ') for channel number ' + str(channel) + '.')
                self.value = 0
                self.state = self.StreamStates.BREATH_FIRST_BYTE

            elif self.state == self.StreamStates.SETTING_FIRST_BYTE:
                if thisByte == hex(int(binascii.hexlify(self._endFlag), 16)):
                    self.state = self.StreamStates.CHECK_SUM
                else:
                    self.value = thisByte[2:]
                    self.state = self.StreamStates.SETTING_SECND_BYTE

            elif self.state == self.StreamStates.SETTING_SECND_BYTE:
                self.value = int(self.value + thisByte[2:], 16)
                # Get value parameters.
                channel = self.openChannels[self.category][self.channelIndex][0]
                # Add new value to buffer.
                self.channelData[self.category][channel].append(self.value)
                self.channelIndex = (self.channelIndex + 1) % len(self.openChannels['S'])
                logger.debug('Got setting data (' + str(self.value) + ') for channel number ' + str(channel) + '.')
                self.value = 0
                self.state = self.StreamStates.BREATH_FIRST_BYTE

            elif self.state == self.StreamStates.CHECK_SUM:
                self.category = ''
                self.channelIndex = 0
                # self._checkErrors(self.message, True)  # May need to comment out if noisy errors.
                self.message = ''
                self.state = self.StreamStates.PHASE_FLAG
                logger.debug('Got end flag and check sum.')

            else:  # Default case
                self.state = self.StreamStates.ERROR
                logger.error('Bad stream state, going to error.')

            if self.state == self.StreamStates.ERROR:  # Runs in same loop (same byte) as ERROR state is set.
                self.category = ''
                self.channelIndex = 0
                self.state = self.StreamStates.PHASE_FLAG
                self.message = ''
                logger.error('Data streaming error, attempting to re-sync with stream.')

    def testDataStream(self, message):
        """
        EXTENDED MODE CMD. This method is called to read serial data from the Servo. The serial port should be checked
        for available data before calling this method.

        :return status:
        """
        logger.info('Reading previous data stream from Servo.')

    def readChannelConfig(self, channel):
        """
        EXTENDED MODE CMD. This command reads channel configuration data from the Servo, e.g. gain, offset, either for
        a specific channel or for all available channels.

        :param channel:
        :return status:
        """
        logger.info('Reading defined channel configurations.')

        validChannel = False
        category = ''
        for dataCategory in self.openChannels:
            for openedChannel in self.openChannels[dataCategory]:
                if channel == openedChannel:
                    validChannel = True
                    category = dataCategory

        if not validChannel:
            logger.warning('Cannot read configuration status for channel, channel is not open.')
            return self.Error.INVALID

        position = self.openChannels[category].index(channel)  # Record position of channel.

        message = b'RCCO' + b'%i' % channel
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endFlag)
        logger.debug('Servo response: ' + str(response))

        configuration = list(str(response[4:-9], 'utf-8').split(',')) #TODO: Split out sampling time and CHKSUM <sampling_time>;<ch1>,<gain>,<offset>,<unit>,<type>,<id>;<CHK><EOT>

        ch_num = int(configuration[0])
        configuration[0] = ch_num
        if '--' in configuration[1]:
            gain = 'None'
        else:
            gain = int(configuration[1][:5]) * 10 ** int(configuration[1][-4:])
        configuration[1] = gain
        if '--' in configuration[2]:
            offset = 'None'
        else:
            offset = int(configuration[2][:5]) * 10 ** int(configuration[2][-4:])
        configuration[2] = offset
        if '--' in configuration[3]: # configuration[3].lstrip('0') == '--':
            unit = 'None'
        else:
            unit = self.units[int(configuration[3].lstrip('0'))]
        configuration[3] = unit

        self.openChannels[category].pop(position)
        self.openChannels[category].insert(position, configuration)

        """
        Example openChannels structure
                                <ch_num>,<gain>,<offset>,<unit>,<type>,<name>
        openChannels = {'C': [],
                        'B': [[200, 0.0001, 0, 'breaths/min', 'BT'], [205, 0.0001, 0, 'cmH2O', 'BT'], [209, 0.001, 0, '%', 'BT']], 
                        'T': [], 
                        'S': [], 
                        'A': []
                        }
        """

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            logger.info('Successfully read defined data channels configurations.')
        else:
            logger.warning('Failed to read defined data channels configurations. ' + str(status))
        return status

    def endDataStream(self):
        """
        """
        logger.info('Ending acquired data stream.')

        message = self._escape
        message = message + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endFlag)
        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response[-4:])
        if status == self.Error.NO_ERROR:
            # TODO: clear self.channelData tables.
            self.state = self.StreamStates.PHASE_FLAG
            logger.info('Successfully ended defined data stream.')
        else:
            logger.warning('Failed to end defined data stream. ' + str(status))
        return status

    def getServoTime(self):
        """
        """
