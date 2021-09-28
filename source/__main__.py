#!/usr/bin/python3

import sys
from PyQt5.QtWidgets import QApplication
import logging.config
import gui

logging.config.fileConfig('logging.ini', disable_existing_loggers=False)
logger = logging.getLogger(__name__)


def main():
    logger.info('Starting ServoScreen application.')
    app = QApplication(sys.argv)
    win = gui.ServoMainWindow()
    win.showMaximized()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
