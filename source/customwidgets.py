#!/usr/bin/python3

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

import pyqtgraph as pqg


class Color(QWidget):
    """
    Custom widget to display a coloured box for testing purposes.
    """

    def __init__(self, color):
        super(Color, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(color))
        self.setPalette(palette)


class LargeNumeric(QWidget):
    """
    Custom widget to display values in a large tile along with a name and units.
    """

    def __init__(self, name, unit, colour):
        super(LargeNumeric, self).__init__()
        widgetLayout = QHBoxLayout()
        leftColumn = QVBoxLayout()
        rightColumn = QVBoxLayout()

        widgetLayout.setContentsMargins(0, 0, 0, 0)
        leftColumn.setContentsMargins(0, 0, 0, 0)
        rightColumn.setContentsMargins(0, 0, 0, 0)

        self.setStyleSheet('color: %s;' % colour)

        self.heading = QLabel('%s %s' % (name, unit))
        self.headingFont = QtGui.QFont("Arial", 14)
        self.heading.setFont(self.headingFont)

        self.currentValue = QLabel(str(0))
        self.currentValueFont = QtGui.QFont("Arial", 45, QtGui.QFont.Bold)  # TODO: auto resize font based on different screen sizes - Complicated
        self.currentValue.setFont(self.currentValueFont)
        self.currentValue.setAlignment(QtCore.Qt.AlignHCenter)

        leftColumn.addWidget(self.heading, 1)
        leftColumn.addWidget(self.currentValue, 2)
        widgetLayout.addLayout(leftColumn, 5)

        self.highValue = QLabel('HI')
        self.highValueFont = QtGui.QFont("Arial", 9)
        self.highValue.setFont(self.highValueFont)

        self.lowValue = QLabel('LO')
        self.lowValue.setFont(self.highValueFont)

        rightColumn.addWidget(self.highValue, 1)
        rightColumn.addStretch(1)
        rightColumn.addWidget(self.lowValue, 1)
        widgetLayout.addLayout(rightColumn, 1)

        self.setLayout(widgetLayout)

    def changeChannel(self, name, unit):
        self.heading = QLabel('%s %s' % (name, unit))
        self.heading.show()

    def setValue(self, value):
        self.currentValue.setText(str(value))
        self.currentValue.show()

    def setHigh(self, value):
        self.highValue.setText(value)
        self.highValue.show()

    def setLow(self, value):
        self.lowValue.setText(value)
        self.lowValue.show()


class SmallNumeric(QWidget):
    """
    Custom widget to display values in a small tile along with a name and units.
    """

    def __init__(self, name, unit, colour):
        super(SmallNumeric, self).__init__()
        self.isRatio = False
        widgetLayout = QHBoxLayout()
        leftColumn = QVBoxLayout()

        widgetLayout.setContentsMargins(0, 0, 0, 0)
        leftColumn.setContentsMargins(0, 0, 0, 0)

        self.setStyleSheet('color: %s;' % colour)

        self.heading = QLabel(str(name))
        self.heading.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        if unit == 'ratio':
            self.isRatio = True
            self.units = QLabel('')
        else:
            self.units = QLabel(str(unit))
        self.units.setFont(QtGui.QFont("Arial", 12))

        leftColumn.addWidget(self.heading, 1)
        leftColumn.addWidget(self.units, 1)
        widgetLayout.addLayout(leftColumn, 5)

        self.currentValue = QLabel(str(0))
        self.currentValue.setFont(QtGui.QFont("Arial", 26))
        widgetLayout.addWidget(self.currentValue, 1)

        self.setLayout(widgetLayout)

    def changeChannel(self, name, unit):
        self.heading.setText(name)
        self.heading.show()
        if unit == 'ratio':
            self.isRatio = True
            self.units.setText('')
        else:
            self.isRatio = False
            self.units.setText(unit)
        self.units.show()

    def setValue(self, value):
        if self.isRatio:
            if value < 1:
                self.currentValue.setText('1:' + str(round(1/value, 1)))
            else:
                self.currentValue.setText(str(round(value, 1)) + ':1')
        else:
            self.currentValue.setText(str(value))
        self.currentValue.show()


class Waveform(pqg.PlotWidget):
    """
    Custom widget to display a waveform along with a name, units, and scale.
    """
    # TODO: Add filtering to remove glitches in the data.

    def __init__(self, title, color, axispos, minval, maxval):
        super(Waveform, self).__init__(enableMenu=False)
        self.dataPoints = 500
        self.setMouseEnabled(False, False)
        self.hideButtons()
        self.dataAxis = self.getAxis('left')
        #self.dataAxis.setStyle(showValues=False)
        #self.enableAutoRange(axis=pqg.ViewBox.YAxis)

        self.x = list(range(-self.dataPoints, 0))  # Time points
        self.y = [0] * self.dataPoints  # Data points
        self.y_zeros = [0] * self.dataPoints

        pen = pqg.mkPen(color=QtGui.QColor(color), width=3)
        self.data_line = self.plot(self.x, self.y, pen=pen)

        if axispos == 'bottom':
            self.timeAxis = self.getAxis('bottom')
            self.timeAxis.setStyle(showValues=False)
        else:
            self.timeAxis = self.hideAxis('bottom')
            zeroAxisPen = pqg.mkPen(color=QtGui.QColor('grey'), width=1)
            self.zeroAxis_line = self.plot(self.x, self.y, pen=zeroAxisPen)
            #self.dataAxis.setTickSpacing(major=10000, minor=0.1)
            #self.showGrid(y=True, alpha=1.0)

        self.min = minval
        self.max = maxval

        #self.setYRange(maxval, minval)  # Defines the scale of the Y axis.

    def updatePlot(self, value):
        self.x = self.x[1:]
        self.x.append(self.x[-1] + 1)

        self.y = self.y[1:]
        self.y.append(value)

        self.data_line.setData(self.x, self.y)
        self.zeroAxis_line.setData(self.x, self.y_zeros)


class Textbox(QLabel):
    """
    Custom widget to display ventilator mode.
    """
    def __init__(self):
        super(Textbox, self).__init__()
        self.setStyleSheet("QLabel { color : white; }")
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFont(QtGui.QFont('Arial', 20))
