#!/usr/bin/python3

import sys
import logging
import serial
import serial.tools.list_ports

from PyQt5 import QtGui
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenu, QAction)

import customwidgets
import ciedriver
# TODO: Add logger to gui module. Logfile will be passed in from main module.

logger = logging.getLogger(__name__)


class ServoMainWindow(QMainWindow):
    """
    Main servoMainWindow.
    """

    def __init__(self, parent=None):
        """
        Initializer.
        """
        super().__init__(parent)
        # Set some main window properties.
        logger.info('Creating main window.')
        self.setWindowTitle('ServoScreen')
        self.setContentsMargins(0, 0, 0, 0)
        #self.setStyleSheet('border: 1px solid white;')  # Used for layout debugging purposes.

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor('black'))
        self.setPalette(palette)

        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)

        logger.info('Opening serial port.')
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
        curvesWidgets = {}
        numericsWidgets = {}

        curves = [('cmH2O', 'yellow', 'bottom', 0, 30),
                  ('l/min BTPS', 'green', 'middle', -60, 60),
                  ('l/min BTPS', 'teal', 'bottom', 0, 400)]

        for curve in curves:
            title = curve[0]
            colour = curve[1]
            axis = curve[2]
            minVal = curve[3]
            maxVal = curve[4]

            curvesWidgets[colour] = customwidgets.Waveform(title, colour, axis, minVal, maxVal)
            curvesLayout.addWidget(curvesWidgets[colour])

        generalLayout.addLayout(curvesLayout, 5)

        numerics = [('Ppeak', '(cmH2O)', 'yellow', 2),
                    ('Pmean', '(cmH2O)', 'yellow', 1),
                    ('PEEP', '(cmH2O)', 'yellow', 1),
                    ('RR', '(br/min)', 'green', 2),
                    ('O2', '(%)', 'green', 2),
                    ('Ti/Ttot', '', 'green', 1),
                    ('MVe', '(l/min)', 'teal', 2),
                    ('VTi', '(ml)', 'teal', 1),
                    ('VTe', '(ml)', 'teal', 1)]

        for number in numerics:
            name = number[0]
            unit = number[1]
            colour = number[2]
            size = number[3]

            if size > 1:
                numericsWidgets[name] = customwidgets.LargeNumeric(name, unit, colour)
            else:
                numericsWidgets[name] = customwidgets.SmallNumeric(name, unit, colour)

            numericsLayout.addWidget(numericsWidgets[name], size)

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
            sys.stderr.write('\nCould not open serial port: {}\n'.format(err))
            sys.exit(1)

        print('Connected to %s' % port.name)

        self._initialiseServo()

    def _disconnectSerialPort(self):
        """
        Close serial port and exit program.
        :return:
        """
        if self.openPort.is_open:
            self.openPort.close()

        sys.exit(0)

    def _initialiseServo(self):
        if self.openPort.is_open:
            self.servo = ciedriver.ServoCIE(self.openPort)

        if b'900PCI' not in self.servo.generalCall():
            print('Could not connect to Servo-i.')
        else:
            print('Connected to Servo-i.')
            self.servo.readCIType()
            maxProtocol = self.servo.getMaxProtocol()
            self.servo.setProtocol(maxProtocol)
            # TODO: Add commands to setup data tables.

    def _checkSerialPort(self):
        # TODO: Add check serial port for new data. Called when serial data is available.
        pass