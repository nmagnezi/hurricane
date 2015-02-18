import datetime
import pprint
import logging

import paramiko
import yaml

from config import consts
from hurricane import utils

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Host(object):

    def __init__(self, fqdn, role, conf):
        self.fqdn = fqdn
        self.role = role
        self.hostname = fqdn.split('.')[0]
        self.username = conf.credentials.default_user
        self.password = conf.credentials.default_pass
        self.ssh = paramiko.SSHClient()
        self.host_facts = self.facter2yaml()
        self.host_type = self.get_host_type()
        self.ip_address = self.get_host_ip_address()
        self.os_name = self.get_os_name()
        self.mgmt_interface = self.get_mgmt_interface()
        self.tenant_interface = \
            self.get_tenant_interface(conf.environment.tenant_nic_speed)
        self.print_host()

    def facter2yaml(self):
        self.open_connection()
        self.install_prerequisites()
        host_facts = self.init_facter()
        #self.close_connection()
        return host_facts

    def init_facter(self):
        cmd = 'facter --yaml'
        facter_data, _ = self.run_bash_command(cmd)
        return yaml.safe_load(facter_data)

    def install_prerequisites(self):
        # TODO: verify prerequisites were successfully installed.
        cmd = 'yum install -y facter'
        self.run_bash_command(cmd)

    def get_host_type(self):
        return 'vm' if self.host_facts['is_virtual'] == 'true' else 'baremetal'

    def get_host_ip_address(self):
        return self.host_facts['ipaddress'].encode('ascii', 'ignore')

    def get_os_name(self):
        # For some reason the facter names 'RHEL' as 'RedHat'.
        # This is a workaround to correct it (does not happen in Fedora)
        name = 'rhel' \
            if self.host_facts['operatingsystem'] == 'RedHat' \
            else self.host_facts['operatingsystem'].lower()
        ver = self.host_facts['operatingsystemrelease']
        return ('{name}{ver}'.format(name=name, ver=ver)).lower()

    def get_mgmt_interface(self):
        cmd = "ip route | awk '/default/ {print $5}'"
        mgmt_interface, _ = self.run_bash_command(cmd)
        return mgmt_interface.strip()

    def get_tenant_interface(self, tenant_nic_speed):
        """
        assumption: on baremetal machines, the tenant nic
        a. has no ip address
        b. link state is UP
        """
        if self.host_type == 'vm':
            return self.mgmt_interface
        elif self.host_type == 'baremetal':
            nics_list = self.host_facts['interfaces'].split(',')
            nics_list.remove('lo')  # remove loopback interface
            for nic in nics_list:
                cmd = "ethtool {nic} ".format(nic=nic) + \
                      "| awk '/Speed/ {print $2}'"
                nic_speed, _ = self.run_bash_command(cmd)
                cmd = "ifconfig {nic} | grep inet | grep -v inet6"\
                      .format(nic=nic)
                nic_has_ip, _ = self.run_bash_command(cmd)
                if nic_speed == tenant_nic_speed and nic_has_ip == '':
                    self.close_connection()
                    return nic

    def open_connection(self):
        self.ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.ssh.connect(hostname=self.fqdn,
                         username=self.username,
                         password=self.password,
                         timeout=consts.SshIntervals.SSH_TIMEOUT)

    def close_connection(self):
        self.ssh.close()

    def run_bash_command(self, bash_command):
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(bash_command)

        stdout = (ssh_stdout.read()).strip()
        stderr = ssh_stdout.channel.recv_exit_status()

        LOG.info('{time} {fqdn}: cmd:    {bash_command}'
                 .format(time=utils.timestamp(),
                         fqdn=self.fqdn,
                         bash_command=bash_command))

        LOG.info('{time} {fqdn}: stdout: {ssh_stdout}'
                 .format(time=utils.timestamp(),
                         fqdn=self.fqdn,
                         ssh_stdout=stdout))

        LOG.info('{time} {fqdn}: stderr: {ssh_stderr}'
                 .format(time=utils.timestamp(),
                         fqdn=self.fqdn,
                         ssh_stderr=stderr))

        return stdout, stderr

    def reboot(self):
        self.open_connection()
        self.run_bash_command('reboot')
        LOG.info('Rebooting {fqdn}'.format(fqdn=self.fqdn))
        self.close_connection()

    def print_host(self):
        LOG.info(pprint.pformat(self.__dict__))