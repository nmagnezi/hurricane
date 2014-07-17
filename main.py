import os
import logging
import paramiko
from ConfigParser import ConfigParser
from libs.host import Host
from libs.infra import Provisioning
from libs.configs import Configs
from installer.packstack.packstack import Packstack
from installer.foreman.foreman import Foreman

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

JOB_CONFIG_FILE_DIRECTORY = 'hurricane_config/config'
JOB_SECTION = 'job_params'
JOB_CONFIG_FILE_NAME = 'config.ini'
JOB_CONFIG_FILE_PATH = os.path.join(JOB_CONFIG_FILE_DIRECTORY,
                                    JOB_CONFIG_FILE_NAME)

CREDENTIALS_SECTION = 'credentials'
INSTALLER_SECTION = 'general'
CONSTANTS_SECTION = 'constants'

SSH_TIMEOUT = 3


class Deployer(object):

    def __init__(self, job_dict):
        self.job_dict = job_dict
        self.check_hosts_connectivity()
        self.installer = self.init_installer()
        self.openstack_hosts = self.build_hosts_list()
        self.configurations = Configs(self.job_dict)

    def check_hosts_connectivity(self):
        username = self.job_dict[CREDENTIALS_SECTION]['default_user']
        password = self.job_dict[CREDENTIALS_SECTION]['default_pass']
        hosts_and_roles = self.job_dict[JOB_SECTION]['hosts_and_roles']
        hosts_fqdn_list = [i.split('/')[0] for i in hosts_and_roles.split(", ")]
        for host_fqdn in hosts_fqdn_list:
            LOG.info('Checking {fqdn} availability via SSH'.format(
                fqdn=host_fqdn))
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(hostname=host_fqdn, username=username,
                            password=password, timeout=SSH_TIMEOUT)
            except Exception as e:
                LOG.info('Failed to establish SSH connection to {fqdn}'
                         .format(fqdn=host_fqdn))
                raise e

            else:
                LOG.info('SSH Connection established to {fqdn}'
                         .format(fqdn=host_fqdn))
                ssh.close()

    def init_installer(self):
        """WIP"""
        installer_name = self.job_dict[JOB_SECTION]['openstack_installer']
        if installer_name == 'packstack':
            return Packstack(self.job_dict)
        elif installer_name == 'foreman':
            return Foreman(self.job_dict)

    def build_hosts_list(self):
        hosts_and_roles = self.job_dict[JOB_SECTION]['hosts_and_roles']
        openstack_hosts = []

        for host_and_role in hosts_and_roles.split(", "):
            host_and_role_split = host_and_role.split('/')
            host_fqdn = host_and_role_split[0]
            role_name = host_and_role_split[1]
            tmp_host = Host(host_fqdn, role_name, self.job_dict)
            openstack_hosts.append(tmp_host)
        return openstack_hosts

    def create_yum_repos_all_openstack_hosts(self, repos_list, build):
        for openstack_host in self.openstack_hosts:
            openstack_host.open_connection()
            for repo in repos_list.split(", "):
                self.configurations.create_yum_repo(openstack_host, repo, build)
            openstack_host.close_connection()

    def config_all_openstack_hosts(self, configs_list):
        for openstack_host in self.openstack_hosts:
            openstack_host.open_connection()
            for config in configs_list.split(", "):
                getattr(self.configurations, config)(openstack_host)

    def config_networker_ext_net_interface(self):
        installer_name = self.job_dict[JOB_SECTION]['openstack_installer']
        networker_option = installer_name + '_networker'
        networker_option_name = \
            self.job_dict[CONSTANTS_SECTION][networker_option]
        networker_role_name = \
            self.installer.get_tagged_value(networker_option_name)
        for tmp_host in self.openstack_hosts:
            if tmp_host.role == networker_role_name:
                self.configurations.create_sub_interface(tmp_host)

    def determine_controller_host(self):
        installer_name = self.job_dict[JOB_SECTION]['openstack_installer']
        controller_option = installer_name + '_controller'
        controller_option_name = \
            self.job_dict[CONSTANTS_SECTION][controller_option]
        controller_role_name = \
            self.installer.get_tagged_value(controller_option_name)
        for tmp_host in self.openstack_hosts:
            if tmp_host.role == controller_role_name:
                LOG.info('Controller host found: {fqdn}'
                         .format(fqdn=tmp_host.fqdn))
                return tmp_host

    def generate_ssh_key(self, host):
        cmd = 'yes | ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa'
        host.run_bash_command(cmd)

    def distribute_public_key_to_openstack_hosts(self, host):
        username = self.job_dict[CREDENTIALS_SECTION]['default_user']
        password = self.job_dict[CREDENTIALS_SECTION]['default_pass']
        hosts_and_roles = self.job_dict[JOB_SECTION]['hosts_and_roles']
        hosts_fqdn_list = [i.split('/')[0] for i in hosts_and_roles.split(", ")]

        cmd1 = 'echo "StrictHostKeyChecking no" > /{username}/.ssh/config'
        host.run_bash_command(cmd1)

        for host_fqdn in hosts_fqdn_list:
            cmd2 = 'sshpass -p {password} ssh-copy-id -i ~/.ssh/id_rsa.pub ' \
                   'root@{fqdn}'.format(username=username,
                                        password=password,
                                        fqdn=host_fqdn)
            host.run_bash_command(cmd2)


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
    LOG.info('==============')
    LOG.info('Job Variables:')
    LOG.info('==============')
    LOG.info('[{section}]'.format(section=JOB_SECTION))
    for option in job_dict[JOB_SECTION]:
        LOG.info('{option}: {value}'
                 .format(option=option, value=job_dict[JOB_SECTION][option]))


def do_exec(value):
    skip_values = ['', 'false', 'None', None]
    if not value in skip_values:
        return True
    else:
        return False


def hurricane():
    job_dict = build_dict_from_file(JOB_CONFIG_FILE_PATH)
    print_job_dict(job_dict)

    # Reprovision Hosts via foreman
    if do_exec(job_dict[JOB_SECTION]['reprovision']):
        provisioner = Provisioning(job_dict)
        hosts_fqdn_list = [i.split('/')[0] for i in
                           job_dict[JOB_SECTION]['hosts_and_roles'].split(", ")]
        provisioner.provision_hosts(hosts_fqdn_list)
    else:
        LOG.info('Reprovisioning disabled, Skipping...')

    main = Deployer(job_dict)

    if do_exec(main.job_dict[JOB_SECTION]['repositories']):
        # Configure repositories
        main.config_all_openstack_hosts('remove_all_yum_repos')
        main.create_yum_repos_all_openstack_hosts(
            main.job_dict[JOB_SECTION]['repositories'],
            main.job_dict[JOB_SECTION]['openstack_build'])
    else:
        LOG.info('Repository list is empty, Skipping...')

    # Pre installation configurations
    if do_exec(main.job_dict[JOB_SECTION]['pre_install_configs']):
        main.config_all_openstack_hosts(
            main.job_dict[JOB_SECTION]['pre_install_configs'])
    else:
        LOG.info('Pre installation configurations list is empty, Skipping...')

    if do_exec(main.job_dict[JOB_SECTION]['install_openstack']):
        if main.job_dict[JOB_SECTION]['openstack_installer'] == 'packstack':
            if do_exec(main.job_dict[JOB_SECTION]['ext_vlan']):
                main.config_networker_ext_net_interface()
            controller_host = main.determine_controller_host()
            controller_host.open_connection()
            main.generate_ssh_key(controller_host)
            main.distribute_public_key_to_openstack_hosts(controller_host)
            main.configurations.install_rpm(controller_host,
                                            'openstack-packstack')
            main.installer.generate_answer_file(controller_host)
            main.installer.configure_answer_file(controller_host,
                                                 main.openstack_hosts)
            main.installer.install_openstack(controller_host)

    else:
        LOG.info('OpenStack installation set to false, Skipping...')

    # Pre installation configurations
    if do_exec(main.job_dict[JOB_SECTION]['post_install_configs']):
        main.config_all_openstack_hosts(
            main.job_dict[JOB_SECTION]['Post_install_configs'])
    else:
        LOG.info('Post installation configurations list is empty, Skipping...')


if __name__ == '__main__':
    hurricane()

# TODO:
# 1. exceptions handling - Started
# 2. prep for tempest (later phase)
# 3. docstrings