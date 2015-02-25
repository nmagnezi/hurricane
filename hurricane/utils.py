from ConfigParser import ConfigParser
import datetime
import logging
import os

import bunch

from config import consts

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

# Helper functions


def get_file_path(config_file):
    return os.path.join(consts.Paths.CONFIG_FILE_DIRECTORY, config_file)


def file2bunch(conf):
    config_file = ConfigParser()
    config_file.read(conf)
    conf_dict = {}
    for section in config_file.sections():
        conf_dict[section] = {}
        for option in config_file.options(section):
            conf_dict[section][option] = config_file.get(section, option)
    conf = bunch.bunchify(conf_dict)
    return conf


def do_exec(value):
    skip_values = ['', 'false', 'None', None]
    return True if value not in skip_values else False


def timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
