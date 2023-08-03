import logging
import os

# Global vars
DATE_FORMAT = "%d/%m/%Y"

LOG = logging.getLogger('my_logger')
LOG.setLevel(logging.INFO)

BASE_PATH = os.path.dirname(__file__)
