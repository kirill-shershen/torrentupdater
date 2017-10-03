# -*- coding: utf-8 -*-
import logging
import sys
import settings
config = settings.config()

def logger():
    if config['debug'] == True:
        lvl = logging.DEBUG
    else:
        lvl = logging.INFO
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        # set up logging to console
        console1 = logging.StreamHandler(sys.stdout)
        # set a format which is simpler for console use
        formatter = logging.Formatter('%(asctime)-15s %(levelname)s:%(filename)s:%(lineno)d -- %(message)s')
        console1.setFormatter(formatter)

        logger.addHandler(console1)
        logger.setLevel(lvl)
    return logger
