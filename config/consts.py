class _Names(object):
    ENV_VARIABLE_PREFIX = 'DEPLOYER_'
    ANS_FILE_SUFFIX = '.ini'


class _Paths(object):
    INSTALLER_CONFIG_FILE_DEFAULT_PATH = '/root'
    INSTALLER_CONFIG_FILE_DIRCTORY = 'hurricane/installer/packstack/configs'
    #INSTALLER_CONFIG_FILE_DIRCTORY = 'installer/packstack/configs'
    ENV_VARIABLE_PREFIX = 'DEPLOYER_'
    CONFIG_FILE_DIRECTORY = 'hurricane_config/config'
    #CONFIG_FILE_DIRECTORY = 'config'
    ANS_FILE_SUFFIX = '.ini'


class _SshIntervals(object):
    RECONNECTION_ATTEMPTS = 1200
    RECONNECTION_INTERVAL = 30
    SSH_TIMEOUT = 3
    REBOOT_SLEEP = 10


class _PackstackFile(object):
    GENERAL = 'general'


Names = _Names()
Paths = _Paths()
SshIntervals = _SshIntervals()
PackstackFile = _PackstackFile()