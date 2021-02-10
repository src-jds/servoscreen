#!/usr/bin/python3

import enum
import binascii
from servologging import getLogger

logger = getLogger(__name__)


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

    units = {1: 'ml',
             2: 'ml/s',
             3: 'ml/min',
             4: 'cmH2O',
             5: 'ml/cmH2O',
             6: 'breaths/min',
             7: '%',
             8: 'l/min',
             9: 'cmH2O/l/s',
             10: 'mmHg',
             11: 'kPa',
             12: 'mbar',
             13: 'mV',
             14: 's',
             15: 'l/s',
             16: 'cmH2O/l',
             17: 'l',
             18: 'Joule/l',
             19: 'μV',
             20: 'no unit',
             21: 'cmH2O/μV',
             22: 'breaths/min/l',
             23: 'min'
             }

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
        self.openChannels = {category: [] for category in self.dataCategories}
        self.channelData = {category: [] for category in self.dataCategories}
        self.lastByte = ''
        self.expectedByte = ''
        self.category = ''
        self.phase = ''
        self.breathPosition = 0
        self.curvePosition = 0
        self.diffPosition = 0
        self.value = 0

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
            calcChkSum = self._calculateChecksum(message[:-1], True)
            if message[-1:] != calcChkSum:
                logger.error('Last received message failed checksum validation. Received checksum was ' +
                             str(message[-1:]) + ', calculated checksum is ' +
                             str(calcChkSum) + '.')
                return self.Error.RX_CHKSUM
        else:  # Check for ASCII encoded errors.
            if message[:2] == b'ER':
                status = self.Error(int(message[2:4]))
                logger.error('Error code in received message: ' + status)
                return status
            calcChkSum = self._calculateChecksum(message[-3:-1])
            if message[-3:-1] != calcChkSum:
                logger.error('Last received message failed checksum validation. Received checksum was ' +
                             str(message[-1:]) + ', calculated checksum is ' +
                             str(calcChkSum) + '.')
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
            if response[7] == int(b'0'):
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
        logger.info('Getting highest available protocol version available.')

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
            logger.info('Servo CIE set to protocol version ' + str(version) + '.')
        else:
            logger.warning('Failed to set CIE protocol version. ' + str(status))
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

        response = self._port.read_until(self._endFlag)
        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            # TODO: clear self.channelData tables.
            logger.info('Successfully started defined data stream.')
        else:
            logger.warning('Failed to start defined data stream. ' + str(status))
        return status

    def readDataStream(self):
        """
        EXTENDED MODE CMD. This method is called to read serial data from the Servo. The serial port should be checked
        for available data before calling this method.

        :return status:
        """
        logger.info('Reading data stream from Servo.')

        while self._port.in_waiting():
            thisByte = hex(int(binascii.hexlify(self._port.read(1)), 16))
            nextByte = self.expectedByte
            if thisByte == '0x81' and self.category == '':  # 0x81 = phase flag, Curve data.
                self.category = 'C'
                nextByte = 'phase'
                logger.debug('Reading curve data.')
            elif thisByte == '0x42' and self.category == '':  # 0x42 = 'B', Breath data.
                self.category = 'B'
                nextByte = 'breathVal1'
                logger.debug('Reading breath data.')
            elif thisByte == '0x53' and self.category == '':  # 0x53 = 'S', Settings data.
                self.category = 'S'
                nextByte = 'value'
                logger.debug('Reading settings data.')

            if self.expectedByte == 'data' and thisByte == '0x81':  # Diff data new phase flag.
                nextByte = 'phase'
                logger.debug('Got new phase flag.')
            elif self.category == 'C' and thisByte == '0x7f':  # Diff data end flag.
                self.category = ''
                nextByte = 'checksum'
                logger.debug('Got curve data end flag. Clearing category for new data.')
            elif self.expectedByte == 'data' and thisByte != '0x80':  # Reading differential values.
                if self.curvePosition != 0:
                    self.curvePosition = 0
                channel = self.openChannels[self.category][self.diffPosition][0]
                lastValue = self.channelData[self.category][channel][-1]
                diffValue = int(thisByte, 16)
                if diffValue >= 0x82:
                    diffValue = diffValue - 256
                self.channelData[self.category][channel].append(round(lastValue + diffValue, 3))
                self.diffPosition = (self.diffPosition + 1) % len(self.openChannels['C'])
                logger.debug('Got differential data for channel number ' + str(channel) + '.')

            if self.lastByte == '0x81' and self.category == 'C' and self.expectedByte == 'phase':  # Reading phase.
                if thisByte == '0x10':
                    self.phase = 'insp'
                    nextByte = 'data'
                    logger.debug('Inspiration phase.')
                elif thisByte == '0x20':
                    self.phase = 'paus'
                    nextByte = 'data'
                    logger.debug('Pause phase.')
                elif thisByte == '0x30':
                    self.phase = 'exp'
                    nextByte = 'data'
                    logger.debug('Expiration phase.')

            if self.expectedByte == 'data' and thisByte == '0x80':  # Reading whole values.
                if self.diffPosition != 0:
                    self.diffPosition = 0
                nextByte = 'curveVal1'
            elif self.expectedByte == 'curveVal1':  # Got first byte of value data.
                nextByte = 'curveVal2'
                self.value = thisByte[2:]
            elif self.expectedByte == 'curveVal2':  # Got second byte of value data.
                nextByte = 'data'
                channel = self.openChannels[self.category][self.curvePosition][0]
                self.value = int(self.value + thisByte[2:], 16)
                gain = self.openChannels[self.category][self.curvePosition][1]
                offset = self.openChannels[self.category][self.curvePosition][2]
                self.channelData[self.category][channel].append(round(self.value * gain - offset, 3))
                self.value = 0
                self.curvePosition = (self.curvePosition + 1) % len(self.openChannels['C'])
                logger.debug('Got data for channel number ' + str(channel) + '.')

            if self.category == 'B' and thisByte == '0x7f':  # Got all diff data, got end flag.
                self.category = ''
                nextByte = 'checksum'
                logger.debug('Got breath data end flag. Clearing category for new data.')
            elif self.category == 'B' and self.expectedByte == 'breathVal1':  # Reading breath data.
                nextByte = 'breathVal2'
                self.value = thisByte[2:]
            elif self.expectedByte == 'breathVal2':
                nextByte = 'breathVal1'
                channel = self.openChannels[self.category][self.breathPosition][0]
                self.value = int(self.value + thisByte[2:], 16)
                gain = self.openChannels[self.category][self.breathPosition][1]
                offset = self.openChannels[self.category][self.breathPosition][2]
                self.channelData[self.category][channel].append(round(self.value * gain - offset, 3))
                self.breathPosition = (self.breathPosition + 1) % len(self.openChannels['B'])

            if self.expectedByte == 'checksum':
                nextByte = ''
                self.breathPosition = 0
                self.curvePosition = 0
                self.diffPosition = 0

            self.expectedByte = nextByte
            self.lastByte = thisByte

    def testDataStream(self, message):
        """
        EXTENDED MODE CMD. This method is called to read serial data from the Servo. The serial port should be checked
        for available data before calling this method.

        :return status:
        """
        logger.info('Reading previous data stream from Servo.')

        for _ in message:
            thisByte = hex(_)
            nextByte = self.expectedByte
            if thisByte == '0x81' and self.category == '':  # 0x81 = phase flag, Curve data.
                self.category = 'C'
                nextByte = 'phase'
                logger.debug('Reading curve data.')
            elif thisByte == '0x42' and self.category == '':  # 0x42 = 'B', Breath data.
                self.category = 'B'
                nextByte = 'breathVal1'
                logger.debug('Reading breath data.')
            elif thisByte == '0x53' and self.category == '':  # 0x53 = 'S', Setting data.
                self.category = 'S'
                nextByte = 'value'
                logger.debug('Reading settings data.')

            if self.expectedByte == 'data' and thisByte == '0x81':  # Diff data new phase flag.
                nextByte = 'phase'
                logger.debug('Got new phase flag.')
            elif self.category == 'C' and thisByte == '0x7f':  # Diff data end flag.
                self.category = ''
                nextByte = 'checksum'
                logger.debug('Got curve data end flag. Clearing category for new data.')
            elif self.expectedByte == 'data' and thisByte != '0x80':  # Reading differential values.
                if self.curvePosition != 0:
                    self.curvePosition = 0
                channel = self.openChannels[self.category][self.diffPosition][0]
                lastValue = self.channelData[self.category][channel][-1]
                diffValue = int(thisByte, 16)
                if diffValue >= 0x82:
                    diffValue = diffValue - 256
                self.channelData[self.category][channel].append(round(lastValue + diffValue, 3))
                self.diffPosition = (self.diffPosition + 1) % len(self.openChannels['C'])
                logger.debug('Got differential data for channel number ' + str(channel) + '.')

            if self.lastByte == '0x81' and self.category == 'C' and self.expectedByte == 'phase':  # Reading phase.
                if thisByte == '0x10':
                    self.phase = 'insp'
                    nextByte = 'data'
                    logger.debug('Inspiration phase.')
                elif thisByte == '0x20':
                    self.phase = 'paus'
                    nextByte = 'data'
                    logger.debug('Pause phase.')
                elif thisByte == '0x30':
                    self.phase = 'exp'
                    nextByte = 'data'
                    logger.debug('Expiration phase.')

            if self.expectedByte == 'data' and thisByte == '0x80':  # Reading whole values.
                if self.diffPosition != 0:
                    self.diffPosition = 0
                nextByte = 'curveVal1'
            elif self.expectedByte == 'curveVal1':  # Got first byte of value data.
                nextByte = 'curveVal2'
                self.value = thisByte[2:]
            elif self.expectedByte == 'curveVal2':  # Got second byte of value data.
                nextByte = 'data'
                channel = self.openChannels[self.category][self.curvePosition][0]
                self.value = int(self.value + thisByte[2:], 16)
                gain = self.openChannels[self.category][self.curvePosition][1]
                offset = self.openChannels[self.category][self.curvePosition][2]
                self.channelData[self.category][channel].append(round(self.value * gain - offset, 3))
                self.value = 0
                self.curvePosition = (self.curvePosition + 1) % len(self.openChannels['C'])
                logger.debug('Got data for channel number ' + str(channel) + '.')

            if self.category == 'B' and thisByte == '0x7f':  # Got all diff data, got end flag.
                self.category = ''
                nextByte = 'checksum'
                logger.debug('Got breath data end flag. Clearing category for new data.')
            elif self.category == 'B' and self.expectedByte == 'breathVal1':  # Reading breath data.
                nextByte = 'breathVal2'
                self.value = thisByte[2:]
            elif self.expectedByte == 'breathVal2':
                nextByte = 'breathVal1'
                channel = self.openChannels[self.category][self.breathPosition][0]
                self.value = int(self.value + thisByte[2:], 16)
                gain = self.openChannels[self.category][self.breathPosition][1]
                offset = self.openChannels[self.category][self.breathPosition][2]
                self.channelData[self.category][channel].append(round(self.value * gain - offset, 3))
                self.breathPosition = (self.breathPosition + 1) % len(self.openChannels['B'])

            if self.expectedByte == 'checksum':
                nextByte = ''
                self.breathPosition = 0
                self.curvePosition = 0
                self.diffPosition = 0

            self.expectedByte = nextByte
            self.lastByte = thisByte

    def parseData(self, category, data):
        """
        EXTENDED MODE CMD. This method parses channel data streamed from the Servo and breaks it out into the data
        structure created by readDataStream() based on data category.

        :param category:
        :param data:
        """
        logger.info('Parsing data.')
        # TODO: parse each category of data.
        category = category.upper()
        if category not in self.dataCategories:
            logger.warning('Incorrect data category given.')
            return self.Error.INVALID

        hexData = []
        for _ in data:
            hexData.append(hex(_)[2:].zfill(2))

        values = []
        i = 0

        if category == 'C':
            for index, byte in enumerate(hexData):
                if byte == '81':
                    hexData.pop(index + 1)
                elif byte == '80':
                    values[i] = int(hexData.pop(index + 1) + hexData.pop(index + 2))
                    i += 1
                else:
                    # TODO: Find a way to convert a string like '7e' to a byte like b'\x7e'. Pass as first argument to from_bytes().
                    values[i] = values[i - 1] + int.from_bytes("""b'\x7e'""", signed=True, byteorder='big')
                    values += 1
        elif category == 'B':
            # TODO: Add parsing for breath data.
            pass
        else:
            pass

    def readChannelConfig(self, channel):
        """
        EXTENDED MODE CMD. This command reads channel configuration data from the Servo, e.g. gain, offset, either for
        a specific channel or for all available channels.

        :param channel:
        :return status:
        """
        logger.info('Reading defined channel configurations.')

        validChannel = False
        for key in self.openChannels:
            for openedChannel in self.openChannels[key]:
                if channel == openedChannel:
                    validChannel = True
                    category = key

        if not validChannel:
            logger.warning('Cannot read configuration status for channel, channel in not open.')
            return self.Error.INVALID

        position = self.openChannels[category].index(channel)  # Record position of channel.

        message = b'RCCO' + b'%i' % channel
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endFlag)
        logger.debug('Servo response: ' + str(response))

        configuration = list(str(response[4:-9], 'utf-8').split(','))

        ch_num = int(configuration[0])
        configuration[0] = ch_num
        gain = int(configuration[1][:5]) * 10 ** int(configuration[1][-4:])
        configuration[1] = gain
        offset = int(configuration[2][:5]) * 10 ** int(configuration[2][-4:])
        configuration[2] = offset
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
        message = message + self._calculateChecksum(message) + self._endOfTransmission

        logger.debug('Message to Servo: ' + str(message))
        self._port.write(message)

        response = self._port.read_until(self._endFlag)
        logger.debug('Servo response: ' + str(response))

        status = self._checkErrors(response)
        if status == self.Error.NO_ERROR:
            # TODO: clear self.channelData tables.
            logger.info('Successfully ended defined data stream.')
        else:
            logger.warning('Failed to end defined data stream. ' + str(status))
        return status

    def getServoTime(self):
        """
        """
