import paramiko
import logging
import datetime
import config.constants as c

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Host(object):

    def __init__(self, fqdn, role, job_dict):
        self.fqdn = fqdn
        self.role = role
        self.hostname = fqdn.split('.')[0]
        self.username = job_dict[c.CREDENTIALS]['default_user']
        self.password = job_dict[c.CREDENTIALS]['default_pass']
        self.ssh = paramiko.SSHClient()
        self.host_type, self.ip_address, self.os_name, self.mgmt_interface, \
            self.tenant_interface = self.get_host_info(job_dict)
        self.print_host()

    def get_host_info(self, job_dict):
        self.open_connection()
        host_type = self.get_host_type()
        ip_address = self.get_host_ip_address()
        os_name = self.get_os_name(job_dict)
        mgmt_interface = self.get_mgmt_interface()
        tenant_interface = self.get_tenant_interface(job_dict, os_name)
        self.close_connection()
        return host_type, ip_address, os_name, mgmt_interface, tenant_interface

    def get_host_type(self):
        cmd = \
            'grep hypervisor /proc/cpuinfo /dev/null && echo true || echo false'
        is_virtual, _ = self.run_bash_command(cmd)
        return 'baremetal' if is_virtual == 'false' else 'vm'

    def get_host_ip_address(self):
        cmd = 'dig {hostname} +short'.format(hostname=self.fqdn)
        ip_address, _ = self.run_bash_command(cmd)
        return ip_address.rstrip()

    def get_os_name(self, job_dict):
        os_str, _ = self.run_bash_command('cat /etc/system-release')
        for os_name in job_dict[c.OS_NAMES].keys():
            if job_dict[c.OS_NAMES][os_name] == os_str.strip():
                return os_name

    def get_mgmt_interface(self):
        cmd = "ip route | awk '/default/ {print $5}'"
        mgmt_interface, _ = self.run_bash_command(cmd)
        return mgmt_interface.strip()

    def get_tenant_interface(self, job_dict, os_name):
        """
        assumption: on baremetal machines, the tenant nic
        a. has no ip address
        b. link state is UP
        """
        host_type = self.get_host_type()
        if host_type == 'vm':
            return self.get_mgmt_interface()
        elif host_type == 'baremetal':
            if os_name == 'rhel6.5':
                cmd = "ifconfig | awk '/HWaddr/ {print $1}' | sed -e s/\:\//g"
            else:  # rhel7.0
                cmd = "ifconfig | awk '/mtu/ {print $1}' | sed -e s/\:\//g"
            nics_string, _ = self.run_bash_command(cmd)
            nics_list = nics_string.split('\n')
            tenant_nic_speed = job_dict[c.ENVIRONMENT]['tenant_nic_speed']
            for nic in nics_list:
                cmd = "ethtool {nic} ".format(nic=nic) + \
                      "| awk '/Speed/ {print $2}'"
                nic_speed, _ = self.run_bash_command(cmd)

                cmd = "ifconfig {nic} | grep inet | grep -v inet6"\
                    .format(nic=nic)
                nic_has_ip, _ = self.run_bash_command(cmd)

                if nic_speed == tenant_nic_speed and nic_has_ip == '':
                    return nic

    def open_connection(self):
        self.ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.ssh.connect(hostname=self.fqdn, username=self.username,
                         password=self.password, timeout=c.SSH_TIMEOUT)

    def close_connection(self):
        self.ssh.close()

    def run_bash_command(self, bash_command):
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(bash_command)

        stdout = (ssh_stdout.read()).strip()
        stderr = ssh_stdout.channel.recv_exit_status()

        LOG.info('{time} {fqdn}: cmd:    {bash_command}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=self.fqdn, bash_command=bash_command))
        LOG.info('{time} {fqdn}: stdout: {ssh_stdout}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=self.fqdn,
                         ssh_stdout=stdout))

        LOG.info('{time} {fqdn}: stderr: {ssh_stderr}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=self.fqdn,
                         ssh_stderr=stderr))

        return stdout, stderr

    def reboot(self):
        self.open_connection()
        self.run_bash_command('reboot')
        LOG.info('Rebooting {fqdn}'.format(fqdn=self.fqdn))
        self.close_connection()

    def print_host(self):
        LOG.info(self.__dict__)
