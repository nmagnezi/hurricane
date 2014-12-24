# SSH Intervals
RECONNECTION_ATTEMPTS = 1200
RECONNECTION_INTERVAL = 30
SSH_TIMEOUT = 3
REBOOT_SLEEP = 10

# Paths
INSTALLER_CONFIG_FILE_DEFAULT_PATH = '/root'
INSTALLER_CONFIG_FILE_DIRCTORY = 'hurricane/installer/packstack/configs'
#INSTALLER_CONFIG_FILE_DIRCTORY = 'installer/packstack/configs'
ENV_VARIABLE_PREFIX = 'DEPLOYER_'
CONFIG_FILE_DIRECTORY = 'hurricane_config/config'
#CONFIG_FILE_DIRECTORY = 'config'

# Hurricane Config File Section
JOB = 'job_params'
CREDENTIALS = 'credentials'
CONSTANTS = 'constants'
INSTALLER = 'general'
ENVIRONMENT = 'environment'
REPO = 'repositories'
CI = 'ci'
FOREMAN_PARAMS = 'foreman_params'

# Packstack
INSTALLER_SECTION = 'general'