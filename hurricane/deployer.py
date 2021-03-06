import logging

from config import consts
from hurricane.configs import Configs
from hurricane.host import Host
from plugins.installer.packstack.packstack import Packstack
from plugins.installer.staypuft.staypuft import Staypuft
import paramiko

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Deployer(object):

    def __init__(self, conf):
        self.username = conf.credentials.default_user
        self.password = conf.credentials.default_pass
        self.hosts_and_roles = conf.job_params.hosts_and_roles
        self.installer_name = conf.job_params.openstack_installer
        self.hosts_fqdn = self._init_hosts_fqdn()
        self.os_ver = conf.job_params.openstack_version
        self.constants = conf.constants
        self.check_hosts_connectivity()
        self.installer = self._init_installer_plugin(conf)
        self.openstack_hosts = self._init_hosts_list(conf)
        self.configurations = Configs(conf)

    def check_hosts_connectivity(self):
        for host_fqdn in list(set(self.hosts_fqdn)):
            LOG.info('Checking {fqdn} availability via SSH'
                     .format(fqdn=host_fqdn))
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(hostname=host_fqdn,
                            username=self.username,
                            password=self.password,
                            timeout=consts.SshIntervals.SSH_TIMEOUT)
            except Exception as e:
                LOG.info('Failed to establish SSH connection to {fqdn}'
                         .format(fqdn=host_fqdn))
                raise e

            else:
                LOG.info('SSH Connection established to {fqdn}'
                         .format(fqdn=host_fqdn))
                ssh.close()

    def _init_hosts_fqdn(self):
        return [i.split('/')[0] for i in self.hosts_and_roles.split(", ")]

    def _init_installer_plugin(self, conf):
        # TODO: this is ugly and should be refactored.
        if self.installer_name == 'packstack':
            return Packstack(conf)
        elif self.installer_name == 'staypuft':
            return Staypuft(conf)

    def _init_hosts_list(self, conf):
        openstack_hosts = []
        for host_and_role in self.hosts_and_roles.split(", "):
            host_and_role_split = host_and_role.split('/')
            host_fqdn = host_and_role_split[0]
            role_name = host_and_role_split[1]
            tmp_host = Host(host_fqdn, role_name, conf)
            openstack_hosts.append(tmp_host)
        return openstack_hosts

    def create_yum_repos_all_openstack_hosts(self, repos_list, build):
        for openstack_host in self.openstack_hosts:
            openstack_host.open_connection()
            for repo in repos_list.split(", "):
                self.configurations.create_yum_repo(openstack_host,
                                                    repo,
                                                    build)
            openstack_host.close_connection()

    def config_all_openstack_hosts(self, configs_list):
        for openstack_host in self.openstack_hosts:
            openstack_host.open_connection()
            for config in configs_list.split(", "):
                getattr(self.configurations, config)(openstack_host)

    def get_controller_host(self):
        # TODO: this is ugly and should be refactored.
        LOG.info('openstack version: {os_ver},'.format(os_ver=self.os_ver))
        LOG.info('plugin name: {installer_name},'
                 .format(installer_name=self.installer_name))
        controller_option = ('{ver}_{plugin}_controller'
                             .format(ver=self.os_ver.lower(),
                                     plugin=self.installer_name))
        LOG.info('controller option: {controller_option}'
                 .format(controller_option=controller_option))
        controller_option_name = self.constants[controller_option]
        LOG.info('controller option name: {controller_option_name}'
                 .format(controller_option_name=controller_option_name))
        controller_role_name = (self.installer
                                .get_tagged_value(controller_option_name))
        LOG.info('controller role name: {controller_role_name},'
                 .format(controller_role_name=controller_role_name))
        for tmp_host in self.openstack_hosts:
            if tmp_host.role == controller_role_name:
                LOG.info('Controller host found: {fqdn}'
                         .format(fqdn=tmp_host.fqdn))
                return tmp_host

    def get_networker_host(self):
        # TODO: this is ugly and should be refactored.
        LOG.info('openstack version: {os_ver},'.format(os_ver=self.os_ver))
        LOG.info('plugin name: {installer_name},'
                 .format(installer_name=self.installer_name))
        networker_option = ('{ver}_{plugin}_networker'
                            .format(ver=self.os_ver.lower(),
                                    plugin=self.installer_name))
        LOG.info('networker option: {networker_option}'
                 .format(networker_option=networker_option))
        networker_option_name = self.constants[networker_option]
        LOG.info('networker option name: {networker_option_name}'
                 .format(networker_option_name=networker_option_name))
        networker_role_name = (self.installer
                               .get_tagged_value(networker_option_name))
        LOG.info('networker role name: {networker_role_name},'
                 .format(networker_role_name=networker_role_name))
        for tmp_host in self.openstack_hosts:
            if tmp_host.role == networker_role_name:
                LOG.info('Networker host found: {fqdn}'
                         .format(fqdn=tmp_host.fqdn))
                return tmp_host

    def generate_ssh_key(self, host):
        host.run_bash_command('yes | ssh-keygen -t rsa -N "" -f '
                              '/root/.ssh/id_rsa')

    def distribute_public_key_to_openstack_hosts(self, host):
        host.run_bash_command('echo "StrictHostKeyChecking no" > '
                              '/root/.ssh/config')

        for host_fqdn in self.hosts_fqdn:
            host.run_bash_command(('sshpass -p {password} ssh-copy-id -i '
                                   '~/.ssh/id_rsa.pub root@{fqdn}'
                                   .format(username=self.username,
                                           password=self.password,
                                           fqdn=host_fqdn)))