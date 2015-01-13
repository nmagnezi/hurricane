import os

from libs import hurricane
import config.constants as c


def main():
    config_env_var = '{prefix}{suffix}'.format(prefix=c.ENV_VARIABLE_PREFIX,
                                               suffix='JOB_CONF_FILE')
    config_file = os.environ.get(config_env_var, 'config.ini')
    return hurricane.run(config_file)

if __name__ == '__main__':
    main()
