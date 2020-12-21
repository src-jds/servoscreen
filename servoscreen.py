#!/usr/bin/python3

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPalette, QColor

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
    def __init__(self, name, value):
        super(LargeNumeric, self).__init__()


class SmallNumeric(QWidget):
    """
    Custom widget to display values in a small tile along with a name and units.
    """
    def __init__(self, name, value):
        super(LargeNumeric, self).__init__()


class Waveform(QWidget):
    """
    Custom widget to display a waveform along with a name, units, and scale.
    """
    def __init__(self, name, value):
        super(LargeNumeric, self).__init__()


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

        self._generalLayout = QHBoxLayout()
        self._curvesLayout = QVBoxLayout()
        self._numericsLayout = QVBoxLayout()

        self._centralWidget.setLayout(self._generalLayout)

        # Fill the layout.
        self.curvesWidgets = {}
        self.numericsWidgets = {}

        curves = ('red', 'green', 'blue')

        for text in curves:
            self.curvesWidgets[text] = Color(text)
            # self.curvesWidgets[text].setAlignment(Qt.AlignCenter)
            self._curvesLayout.addWidget(self.curvesWidgets[text])

        self._generalLayout.addLayout(self._curvesLayout, 5)

        numerics = {'yellow': 2, 'cyan': 1, 'red': 1,
                    'teal': 2, 'blue': 2, 'pink': 1,
                    'white': 2, 'green': 1, 'purple': 1
                    }

        for text, stretch in numerics.items():
            self.numericsWidgets[text] = Color(text)
            # self.numericsWidgets[text].setAlignment(Qt.AlignCenter)
            self._numericsLayout.addWidget(self.numericsWidgets[text], stretch)

        self._generalLayout.addLayout(self._numericsLayout, 1)

    def _createMenu(self):
        self.menu = self.menuBar().addMenu("&Menu")
        self.menu.addAction('&Exit', self.close)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Window()
    win.showMaximized()
    sys.exit(app.exec_())
