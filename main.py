import os

from config import consts
from libs import hurricane


def main():
    config_env_var = \
        '{prefix}{suffix}'.format(prefix=consts.Names.ENV_VARIABLE_PREFIX,
                                  suffix='JOB_CONF_FILE')
    config_file = os.environ.get(config_env_var, 'config.ini')
    return hurricane.run(config_file)

if __name__ == '__main__':
    main()