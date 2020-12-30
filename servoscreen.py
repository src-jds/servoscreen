#!/usr/bin/python3

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel)


# from pyqtgraph import PlotWidget, plot


class Color(QWidget):
    """
    Custom widget to display a coloured box for testing purposes.
    """

    def __init__(self, color):
        super(Color, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)


class LargeNumeric(QWidget):
    """
    Custom widget to display values in a large tile along with a name and units.
    """
    def __init__(self, name, unit, colour):
        super(LargeNumeric, self).__init__()
        _widgetLayout = QHBoxLayout()
        _leftColumn = QVBoxLayout()
        _rightColumn = QVBoxLayout()
        self.setStyleSheet('color: %s;' % colour)

        self.heading = QLabel('%s %s' % (name, unit))
        self.heading.setFont(QFont("Arial", 14))
        self.currentValue = QLabel(str(0))
        self.currentValue.setFont(QFont("Arial", 50, QFont.Bold))
        self.currentValue.setAlignment(Qt.AlignHCenter)

        _leftColumn.addWidget(self.heading)
        _leftColumn.addWidget(self.currentValue)
        _widgetLayout.addLayout(_leftColumn, 5)

        self.highValue = QLabel('HI')
        self.lowValue = QLabel('LO')

        _rightColumn.addWidget(self.highValue)
        _rightColumn.addWidget(self.lowValue)
        _widgetLayout.addLayout(_rightColumn, 1)

        self.setLayout(_widgetLayout)

    def setValue(self, value):
        self.currentValue.setText(value)

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
        _widgetLayout = QHBoxLayout()
        _leftColumn = QVBoxLayout()
        self.setStyleSheet('color: %s;' % colour)

        self.heading = QLabel(str(name))
        self.heading.setFont(QFont("Arial", 14, QFont.Bold))
        self.units = QLabel(str(unit))
        self.units.setFont(QFont("Arial", 12))

        _leftColumn.addWidget(self.heading)
        _leftColumn.addWidget(self.units)
        _widgetLayout.addLayout(_leftColumn, 5)

        self.currentValue = QLabel(str(0))
        self.currentValue.setFont(QFont("Arial", 26))
        _widgetLayout.addWidget(self.currentValue, 1)

        self.setLayout(_widgetLayout)

    def setValue(self, value):
        self.currentValue.setText(value)


class Waveform(QWidget):
    """
    Custom widget to display a waveform along with a name, units, and scale.
    """
    def __init__(self, name, value):
        super(Waveform, self).__init__()


class Window(QMainWindow):
    """
    Main Window.
    """

    def __init__(self, parent=None):
        """
        Initializer.
        """
        super().__init__(parent)
        # Set some main window properties.
        self.setWindowTitle('Servo Display')

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('black'))
        self.setPalette(palette)

        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)

        self._createLayout()

        self._createMenu()

    def _createLayout(self):
        """
        Set the main window layout.
        """
        _generalLayout = QHBoxLayout()
        _curvesLayout = QVBoxLayout()
        _numericsLayout = QVBoxLayout()

        # Fill the layout.
        _curvesWidgets = {}
        _numericsWidgets = {}

        _curves = ('yellow', 'green', 'teal')

        for text in _curves:
            _curvesWidgets[text] = Color(text)
            _curvesLayout.addWidget(_curvesWidgets[text])

        _generalLayout.addLayout(_curvesLayout, 5)

        _numerics = [('Ppeak', '(cmH2O)', 'yellow', 3),
                     ('Pmean', '(cmH2O)', 'yellow', 1),
                     ('PEEP', '(cmH2O)', 'yellow', 1),
                     ('RR', '(br/min)', 'green', 3),
                     ('O2', '(%)', 'green', 3),
                     ('Ti/Ttot', '', 'green', 1),
                     ('MVe', '(l/min)', 'teal', 3),
                     ('VTi', '(ml)', 'teal', 1),
                     ('VTe', '(ml)', 'teal', 1)]

        for channel in _numerics:
            name = channel[0]
            unit = channel[1]
            colour = channel[2]
            size = channel[3]

            if size == 3:
                _numericsWidgets[name] = LargeNumeric(name, unit, colour)
            else:
                _numericsWidgets[name] = SmallNumeric(name, unit, colour)

            _numericsLayout.addWidget(_numericsWidgets[name], size)

        _generalLayout.addLayout(_numericsLayout, 1)

        self._centralWidget.setLayout(_generalLayout)

    def _createMenu(self):
        self.menu = self.menuBar().addMenu("&Menu")
        self.menu.addAction('&Exit', self.close)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Window()
    win.showMaximized()
    sys.exit(app.exec_())
