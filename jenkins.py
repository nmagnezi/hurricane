import ConfigParser
import logging
import os

from config import consts
"""
This script will configure the given config file section
with relevant env variables.
"""

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

# Constants
CONFIG_FILE_NAME = (os.environ.
                    get(consts.Names.ENV_VARIABLE_PREFIX + 'JOB_CONF_FILE',
                        'config.ini'))
CONFIG_FILE_PATH = os.path.join(os.environ.get('WORKSPACE'),
                                consts.Paths.CONFIG_FILE_DIRECTORY,
                                CONFIG_FILE_NAME)

config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE_PATH)

LOG.info('Configuring {configfile} configuration file with the job parameters'
         .format(configfile=CONFIG_FILE_PATH))
LOG.info('[' + consts.Names.CONFIG_FILE_SECTION + ']')

for env_variable in os.environ:
    if consts.Names.ENV_VARIABLE_PREFIX in str(env_variable):
        option = (env_variable.
                  split(consts.Names.ENV_VARIABLE_PREFIX)[1].lower())
        value = os.environ.get(env_variable)
        LOG.info('found {env} env variable with value: {val}'
                 .format(env=env_variable, val=value))
        config.set(consts.Names.CONFIG_FILE_SECTION, option, value)
        LOG.info('{option} = {value}'.format(option=option, value=value))

with open(CONFIG_FILE_PATH, 'wb') as configfile:
    config.write(configfile)