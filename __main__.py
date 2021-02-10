#!/usr/bin/python3

import sys
from PyQt5.QtWidgets import QApplication
from servologging import getLogger

import gui
logger = getLogger(__name__)


def main():
    logger.info('Starting ServoScreen application.')

    app = QApplication(sys.argv)
    win = gui.ServoMainWindow()
    win.showMaximized()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
