#!/usr/bin/python3

import sys
import logging
from PyQt5.QtWidgets import QApplication

import gui
# TODO: Create logfile and pass to application.


def main():
    logger = logging.getLogger('ServoScreen')
    logger.setLevel(logging.DEBUG)
    logFileHandler = logging.FileHandler('test.log')
    logFormat = logging.Formatter('%(asctime)s:[%(levelname)s]:%(name)s: %(message)s')
    logFileHandler.setFormatter(logFormat)

    logger.addHandler(logFileHandler)

    logger.info('Starting ServoScreen application.')

    app = QApplication(sys.argv)
    win = gui.ServoMainWindow()
    win.showMaximized()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
