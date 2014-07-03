import os
import logging
from ConfigParser import ConfigParser

"""
This script will configure the given config file section
with relevant env variables.
"""

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

ENV_VARIABLE_PREFIX = 'DEPLOYER_'
CONFIG_FILE_DIRECTORY = '../hurricane_config/config'
CONFIG_FILE_SECTION = 'job_params'
CONFIG_FILE_NAME = os.environ.get(ENV_VARIABLE_PREFIX + 'JOB_CONF_FILE'
                                  , 'config.ini')
CONFIG_FILE_PATH = os.path.join(os.environ.get('WORKSPACE'),
                                CONFIG_FILE_DIRECTORY,
                                CONFIG_FILE_NAME)

config = ConfigParser()
config.read(CONFIG_FILE_PATH)

LOG.info('Configuring {configfile} configuration file with the job parameters'
         .format(configfile=CONFIG_FILE_PATH))
LOG.info('[' + CONFIG_FILE_SECTION + ']')

for env_variable in os.environ:
    if ENV_VARIABLE_PREFIX in str(env_variable):
        option = env_variable.split(ENV_VARIABLE_PREFIX)[1].lower()
        value = os.environ.get(env_variable)
        config.set(CONFIG_FILE_SECTION, option, value)
        LOG.info('{option} = {value}'.format(option=option, value=value))

with open(CONFIG_FILE_PATH, 'wb') as configfile:
    config.write(configfile)