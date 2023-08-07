import logging
import os

# Global vars
DATE_FORMAT = "%d/%m/%Y"

LOG = logging.getLogger('my_logger')
LOG.setLevel(logging.WARNING)

BASE_PATH = os.path.dirname(__file__)
