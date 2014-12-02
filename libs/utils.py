import logging
from ConfigParser import ConfigParser
import config.constants as c

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

# Helper functions


def build_dict_from_file(conf):
    config_file = ConfigParser()
    config_file.read(conf)
    file_dict = {}
    for section in config_file.sections():
        file_dict[section] = {}
        for option in config_file.options(section):
            file_dict[section][option] = config_file.get(section, option)
    return file_dict


def print_job_dict(job_dict):
    LOG.info('Job Variables:')
    LOG.info('[{section}]'.format(section=c.JOB))
    for option in job_dict[c.JOB]:
        LOG.info('{option}: {value}'
                 .format(option=option, value=job_dict[c.JOB][option]))


def do_exec(value):
    skip_values = ['', 'false', 'None', None]
    return True if not value in skip_values else False