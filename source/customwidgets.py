#!/usr/bin/python3

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel)

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
        self.currentValueFont = QtGui.QFont("Arial", 50, QtGui.QFont.Bold)
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

    def setValue(self, value):
        self.currentValue.setText(str(value))
        self.currentValue.show()

    def setHigh(self, value):
        self.highValue.setText(value)

    def setLow(self, value):
        self.lowValue.setText(value)


class SmallNumeric(QWidget):
    """
    Custom widget to display values in a small tile along with a name and units.
    """

    def __init__(self, name, unit, colour):
        super(SmallNumeric, self).__init__()
        widgetLayout = QHBoxLayout()
        leftColumn = QVBoxLayout()

        widgetLayout.setContentsMargins(0, 0, 0, 0)
        leftColumn.setContentsMargins(0, 0, 0, 0)

        self.setStyleSheet('color: %s;' % colour)

        self.heading = QLabel(str(name))
        self.heading.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        self.units = QLabel(str(unit))
        self.units.setFont(QtGui.QFont("Arial", 12))

        leftColumn.addWidget(self.heading, 1)
        leftColumn.addWidget(self.units, 1)
        widgetLayout.addLayout(leftColumn, 5)

        self.currentValue = QLabel(str(0))
        self.currentValue.setFont(QtGui.QFont("Arial", 26))
        widgetLayout.addWidget(self.currentValue, 1)

        self.setLayout(widgetLayout)

    def setValue(self, value):
        self.currentValue.setText(str(value))
        self.currentValue.show()


class Waveform(pqg.PlotWidget):
    """
    Custom widget to display a waveform along with a name, units, and scale.
    """

    def __init__(self, title, color, axisPos, minVal, maxVal):
        super(Waveform, self).__init__(enableMenu=False)
        self.dataPoints = 500
        self.setMouseEnabled(False, False)
        self.hideButtons()
        #self.enableAutoRange(axis=pqg.ViewBox.YAxis)

        self.timeAxis = self.getAxis('bottom')

        self.min = minVal
        self.max = maxVal

        self.x = list(range(-self.dataPoints, 0))  # Time points
        self.y = [0] * self.dataPoints  # Data points

        #self.setYRange(maxVal, minVal)  # Defines the scale of the Y axis.

        pen = pqg.mkPen(color=QtGui.QColor(color), width=3)
        self.data_line = self.plot(self.x, self.y, pen=pen)

    def updatePlot(self, value):
        self.x = self.x[1:]
        self.x.append(self.x[-1] + 1)

        self.y = self.y[1:]
        self.y.append(value)

        self.data_line.setData(self.x, self.y)
