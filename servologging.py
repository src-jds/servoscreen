from datetime import datetime
import logging


def getLogger(name):
    logFileHandler = logging.FileHandler(filename='logs\{:%y%b%d_%H%M}.log'.format(datetime.now()), mode='w')
    logFileHandler.setLevel(logging.DEBUG)

    logFormat = logging.Formatter('%(asctime)s :: [%(levelname)s] :: %(name)s :: %(message)s', datefmt='%H:%M')
    logFileHandler.setFormatter(logFormat)

    logger = logging.getLogger(name)
    logger.addHandler(logFileHandler)
    logger.setLevel(logging.DEBUG)

    return logger
