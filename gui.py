#!/usr/bin/python3

import traceback
import sys
import serial
import serial.tools.list_ports

from PyQt5 import QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenu, QAction

import customwidgets
import ciedriver
from servologging import getLogger

logger = getLogger(__name__)


class Worker(QObject):
    runtest = False
    finished = pyqtSignal()
    servoData = pyqtSignal()

    def close(self):
        pass

    def run(self, port, servo):
        """
        task
        :return:
        """
        while True:  # TODO: Add finish parameter.
            servo.readDataStream()

        #self.finished.emit()


class ServoMainWindow(QMainWindow):
    """
    Main servoMainWindow.
    """

    def __init__(self, parent=None):
        """
        Initializer.
        """
        super().__init__(parent)
        logger.info('Creating main window.')

        # Set some main window properties.
        self.setWindowTitle('ServoScreen')
        self.setContentsMargins(0, 0, 0, 0)
        #self.setStyleSheet('border: 1px solid white;')  # Used for layout debugging purposes.

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor('black'))
        self.setPalette(palette)

        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)

        self.openPort = serial.Serial()

        logger.info('Creating window layout.')
        self._createLayout()
        logger.info('Creating window menu.')
        self._createMenu()

        # TODO: Add threading for serial communication.

        # TODO: Add timers for GUI data refresh.

        # TODO: Connect Numeric widgets to values.

    def _createLayout(self):
        """
        Set the main window layout.
        """
        generalLayout = QHBoxLayout()
        curvesLayout = QVBoxLayout()
        numericsLayout = QVBoxLayout()

        # Fill the layout.
        self.curvesWidgets = {}
        self.numericsWidgets = {}
        # TODO: change the units entry here to name and get units from the Servo config values instead.
        # so that only channel num, name, colour and size are listed here.
        curves = [(100, 'cmH2O', 'yellow', 'bottom', 0, 30),
                  (101, 'l/min BTPS', 'green', 'middle', -60, 60),
                  (102, 'l/min BTPS', 'teal', 'bottom', 0, 400)]

        for curve in curves:
            channel = curve[0]
            title = curve[1]
            colour = curve[2]
            axis = curve[3]
            minVal = curve[4]
            maxVal = curve[5]

            self.curvesWidgets[channel] = customwidgets.Waveform(title, colour, axis, minVal, maxVal)
            curvesLayout.addWidget(self.curvesWidgets[channel])

        generalLayout.addLayout(curvesLayout, 5)
        # TODO: remove the unit entry here and instead get the units from the Servo config values instead.
        # so that only channel num, name, colour and size are listed here.
        numerics = [(201, 'Ppeak', '(cmH2O)', 'yellow', 2),
                    (202, 'Pmean', '(cmH2O)', 'yellow', 1),
                    (203, 'PEEP', '(cmH2O)', 'yellow', 1),
                    (204, 'RR', '(br/min)', 'green', 2),
                    (205, 'O2', '(%)', 'green', 2),
                    (206, 'Ti/Ttot', '', 'green', 1),
                    (207, 'MVe', '(l/min)', 'teal', 2),
                    (208, 'VTi', '(ml)', 'teal', 1),
                    (209, 'VTe', '(ml)', 'teal', 1)]

        for number in numerics:
            channel = number[0]
            name = number[1]
            unit = number[2]
            colour = number[3]
            size = number[4]

            if size > 1:
                self.numericsWidgets[channel] = customwidgets.LargeNumeric(name, unit, colour)
            else:
                self.numericsWidgets[channel] = customwidgets.SmallNumeric(name, unit, colour)

            numericsLayout.addWidget(self.numericsWidgets[channel], size)

        generalLayout.addLayout(numericsLayout, 1)

        self.centralWidget.setLayout(generalLayout)

    def _createMenu(self):
        menuBar = self.menuBar()
        fileMenu = QMenu('Menu', self)
        menuBar.addMenu(fileMenu)

        self.refreshSerialPortsAction = QAction('Refresh Serial Ports', self)
        self.refreshSerialPortsAction.triggered.connect(lambda: self._populateSerialPorts())
        fileMenu.addAction(self.refreshSerialPortsAction)

        self.connectMenu = fileMenu.addMenu('Connect to Serial Port')
        self._populateSerialPorts()

        fileMenu.addSeparator()

        self.exitAction = QAction('Exit', self)
        self.exitAction.triggered.connect(lambda: self._disconnectSerialPort())
        fileMenu.addAction(self.exitAction)

    def _populateSerialPorts(self):
        """
        Clear and refill the 'Available Serial Ports' menu.
        :return:
        """
        self.connectMenu.clear()

        self.availableSerialPorts = serial.tools.list_ports.comports()

        connectActions = []
        for port in self.availableSerialPorts:
            action = QAction(port.name, self)
            action.triggered.connect(lambda *args, portToOpen=port: self._connectToSerialPort(portToOpen))
            connectActions.append(action)

        self.connectMenu.addActions(connectActions)

    def _connectToSerialPort(self, port):
        """
        Connect to specified serial port.
        :return:
        """
        logger.info('Connecting to serial port.')
        try:
            self.openPort = serial.Serial(
                port=port.name,
                baudrate=9600,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )
        except serial.SerialException as err:
            logger.info('Could not connect to %s' % self.openPort.name)
            sys.stderr.write('\nCould not open serial port: {}\n'.format(err))
            sys.exit(1)

        logger.info('Connected to %s' % self.openPort.name)

        self._initialiseServo()

    def _disconnectSerialPort(self):
        """
        Close serial port and exit program.
        :return:
        """
        if self.openPort.is_open:
            self.timer.stop()
            self.servo.endDataStream()
            logger.info('Disconnected from %s' % self.openPort.name)
            self.openPort.close()

        sys.exit(0)

    def _initialiseServo(self):
        if self.openPort.is_open:
            self.servo = ciedriver.ServoCIE(self.openPort)

        if b'900PCI' not in self.servo.generalCall():
            logger.warn('Could not connect to Servo-i.')
        else:
            logger.info('Connected to Servo-i. Setting protocol version.')
            self.servo.readCIType()
            maxProtocol = self.servo.getMaxProtocol()
            self.servo.setProtocol(maxProtocol)

            logger.info('Setting up data tables.')
            breathChannels = []
            curveChannels = []
            for channel in self.curvesWidgets:
                curveChannels.append(channel)

            for channel in self.numericsWidgets:
                breathChannels.append(channel)

            self.servo.defineAcquiredData('B', breathChannels)
            self.servo.defineAcquiredData('C', curveChannels)

            logger.info('Reading open channel configurations.')
            for key in self.servo.openChannels:
                for channel in self.servo.openChannels[key]:
                    logger.debug('%s : %s' % (key, channel))
                    self.servo.readChannelConfig(channel)

            logger.info('Starting Servo data stream.')
            self.timer = QTimer()
            self.timer.timeout.connect(self.checkSerialPort())
            self.servo.startDataStream()
            self.timer.start(50)

        #self.thread = QThread()
        #self.worker = Worker()
        #self.worker.moveToThread(self.thread)

        #self.thread.started.connect(self.worker.run(self.openPort, self.servo))
        #self.worker.finished.connect(self.thread.quit)
        #self.worker.finished.connect(self.worker.deleteLater)
        #self.thread.finished.connect(self.thread.deleteLater)

        #self.thread.start()

    def checkSerialPort(self):
        if self.openPort.in_waiting:
            self.servo.readDataStream()
            for category in self.servo.channelData:
                if category == 'C':  # Leave last data in array.
                    for channel in self.servo.channelData[category]:
                        while len(self.servo.channelData[category][channel]) > 1:
                            data = self.servo.channelData[category][channel].pop()
                            self.curvesWidgets[channel].updatePlot(data)

                else:  # For breath and other data, remove all data from array.
                    for channel in self.servo.channelData[category]:
                        if len(self.servo.channelData[category][channel]) > 0:
                            data = self.servo.channelData[category][channel].pop()
                            self.numericsWidgets[channel].setValue(data)
