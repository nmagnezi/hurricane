import os

from config import consts
from libs.hurricane import Hurricane
from libs import utils


def main():
    config_env_var = '{prefix}{suffix}'\
                     .format(prefix=consts.Names.ENV_VARIABLE_PREFIX,
                             suffix='JOB_CONF_FILE')
    config_file = os.environ.get(config_env_var, 'config.ini')
    conf = utils.file2bunch(utils.get_file_path(config_file))
    hurricane = Hurricane(conf)
    return hurricane.run()

if __name__ == '__main__':
    main()