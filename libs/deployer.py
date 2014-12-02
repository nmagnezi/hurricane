import logging
import paramiko
import config.constants as c
from libs.host import Host
from libs.configs import Configs
from installer.packstack.packstack import Packstack
from installer.foreman.foreman import Foreman

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Deployer(object):

    def __init__(self, job_dict):
        self.job_dict = job_dict
        self.check_hosts_connectivity()
        self.installer = self.init_installer()
        self.openstack_hosts = self.build_hosts_list()
        self.configurations = Configs(self.job_dict)

    def check_hosts_connectivity(self):
        username = self.job_dict[c.CREDENTIALS]['default_user']
        password = self.job_dict[c.CREDENTIALS]['default_pass']
        hosts_and_roles = self.job_dict[c.JOB]['hosts_and_roles']
        hosts_fqdn = [i.split('/')[0] for i in hosts_and_roles.split(", ")]
        for host_fqdn in hosts_fqdn:
            LOG.info('Checking {fqdn} availability via SSH'
                     .format(fqdn=host_fqdn))
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(hostname=host_fqdn, username=username,
                            password=password, timeout=c.SSH_TIMEOUT)
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
        installer_name = self.job_dict[c.JOB]['openstack_installer']
        if installer_name == 'packstack':
            return Packstack(self.job_dict)
        elif installer_name == 'foreman':
            return Foreman(self.job_dict)

    def build_hosts_list(self):
        hosts_and_roles = self.job_dict[c.JOB]['hosts_and_roles']
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
        installer_name = self.job_dict[c.JOB]['openstack_installer']
        networker_option = installer_name + '_networker'
        networker_option_name = \
            self.job_dict[c.CONSTANTS][networker_option]
        networker_role_name = \
            self.installer.get_tagged_value(networker_option_name)
        for tmp_host in self.openstack_hosts:
            if tmp_host.role == networker_role_name:
                self.configurations.create_sub_interface(tmp_host)

    def determine_controller_host(self):
        installer_name = self.job_dict[c.JOB]['openstack_installer']
        controller_option = installer_name + '_controller'
        controller_option_name = \
            self.job_dict[c.CONSTANTS][controller_option]
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
        username = self.job_dict[c.CREDENTIALS]['default_user']
        password = self.job_dict[c.CREDENTIALS]['default_pass']
        hosts_and_roles = self.job_dict[c.JOB]['hosts_and_roles']
        hosts_fqdn = [i.split('/')[0] for i in hosts_and_roles.split(", ")]

        cmd1 = 'echo "StrictHostKeyChecking no" > /root/.ssh/config'
        host.run_bash_command(cmd1)

        for host_fqdn in hosts_fqdn:
            cmd2 = 'sshpass -p {password} ssh-copy-id -i ~/.ssh/id_rsa.pub ' \
                   'root@{fqdn}'.format(username=username,
                                        password=password,
                                        fqdn=host_fqdn)
            host.run_bash_command(cmd2)