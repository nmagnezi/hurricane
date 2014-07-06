import logging
import datetime
import os

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

JOB_CONFIG_FILE_SECTION = 'job_params'
REPO_CONFIG_FILE_SECTION = 'repositories'
CI_CONFIG_FILE_SECTION = 'ci'
CREDENTIALS_CONFIG_FILE_SECTION = 'credentials'
ENVIRONMENT_CONFIG_FILE_SECTION = 'environment'


class Configs(object):
# Pre and Post installation configurations

    def __init__(self, job_dict):
        self.job_dict = job_dict

    def create_yum_repo(self, host, repo_name, build):
        LOG.info('{time} {fqdn}: Creating yum repo {repo_name}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, repo_name=repo_name))

        repo_url = self.job_dict[REPO_CONFIG_FILE_SECTION][repo_name]
        if '{build}' in repo_url:  # check if there is a build number to inject
            repo_url = str(repo_url).format(build=build)

        cmd1 = 'echo [{name}] > /etc/yum.repos.d/{name}.repo'\
               .format(name=repo_name)
        cmd2 = 'echo name={name} >> /etc/yum.repos.d/{name}.repo'\
               .format(name=repo_name)
        cmd3 = 'echo baseurl={base_url} >> /etc/yum.repos.d/{name}.repo'\
               .format(base_url=repo_url, name=repo_name)
        cmd4 = 'echo enabled=1 >> /etc/yum.repos.d/{name}.repo'\
               .format(name=repo_name)
        cmd5 = 'echo gpgcheck=0 >> /etc/yum.repos.d/{name}.repo'\
               .format(name=repo_name)

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)
        host.run_bash_command(cmd3)
        host.run_bash_command(cmd4)
        host.run_bash_command(cmd5)

    def clean_yum_cache(self, host):
        LOG.info('{time} {fqdn}: Cleaning yum cache'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        cmd = 'yum clean all'
        host.run_bash_command(cmd)

    def remove_all_yum_repos(self, host):
        LOG.info('{time} {fqdn}: Removing all yum repos'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        cmd = 'mv /etc/yum.repos.d/*.repo /tmp'
        host.run_bash_command(cmd)

    def yum_update(self, host):
        LOG.info('{time} {fqdn}: updating all packages'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        cmd = 'yum update -y --nogpgcheck'
        host.run_bash_command(cmd)

    def install_rpm(self, host, rpm_name):
        LOG.info('{time} {fqdn}: installing {rpm}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, rpm=rpm_name))
        cmd = 'yum install -y {rpm}'.format(rpm=rpm_name)
        host.run_bash_command(cmd)

    def uninstall_rpm(self, host, rpm_name):
        LOG.info('{time} {fqdn}: removing {rpm}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, rpm=rpm_name))
        cmd = 'yum remove -y {rpm}'.format(rpm=rpm_name)
        host.run_bash_command(cmd)

    def yum_disable_repo(self, host, repo_name):
        LOG.info('{time} {fqdn}: disabling {repo}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, repo=repo_name))
        cmd = 'yum-config-manager --disable {repo}'.format(repo=repo_name)
        host.run_bash_command(cmd)

    def disable_epel(self, host):
        self.yum_disable_repo(host, 'epel')


    def disable_and_persist_selinux(self, host):
        LOG.info('{time} {fqdn}: disabling SELinux on host {host}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))

        cmd1 = 'setenforce 0'
        cmd2 = 'sed -i "s/^SELINUX=.*/SELINUX=permissive/g" /etc/selinux/config'
        cmd3 = 'sed -i "s/^SELINUX=.*/SELINUX=permissive/g" ' \
               '/etc/sysconfig/selinux'

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)
        host.run_bash_command(cmd3)

    def rhos_release(self, host):
        rpm_url = self.job_dict[CI_CONFIG_FILE_SECTION]['rhos-release']
        self.install_rpm(host, rpm_url)

    def rhos_release_havana(self, host):
        self.rhos_release(host)
        cmd = 'rhos-release 4'
        host.run_bash_command(cmd)

    def rhos_release_icehouse(self, host):
        self.rhos_release(host)
        cmd = 'rhos-release 5'
        host.run_bash_command(cmd)

    def restart_linux_service(self, host, service_name):
        LOG.info('{time} {fqdn}: restarting {service_name}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, service_name=service_name))
        if 'rhel6' in host.os_name:
            cmd = 'service {service} restart'\
                .format(service_name=service_name)

        else:  # rhel7 or fedora
            cmd = 'systemctl restart {service}.service'\
                .format(service_name=service_name)

        host.run_bash_command(cmd)

    def tun_int_ip_addr(self, host):
       tun_subnet = \
           self.job_dict[ENVIRONMENT_CONFIG_FILE_SECTION]['tunneling_subnet']


        LOG.info('{time} {fqdn}: configuring tunnel interface {int} ip '
                 'address {ip}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, int=host.tenant_interface, ip=ip))


    def ovs_add_port_to_br(self, host, br_name, port_name):
        LOG.info('{time} {fqdn}: adding {port_name} to {br_name}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, port_name=port_name,
                         br_name=br_name))
        cmd = 'ovs-vsctl add-port {br_name} {port_name}'\
              .format(br_name=br_name, port_name=port_name)

        host.run_bash_command(cmd)

    def add_ext_net_port_to_ovs_br(self, host):
        self.ovs_add_port_to_br(host, 'br-ex', host.tenant_interface)

    def create_sub_interface(self, host, vlan):
        # TODO: internally read vlan id instead of retrieving it from the user.
        interface = host.tenant_interface
        LOG.info('{time} {fqdn}: Creating sub interface: {interface}.{vlan}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, interface=interface, vlan=vlan))

        file_path = '/etc/sysconfig/network-scripts/ifcfg-{interface}.{vlan}'\
                    .format(interface=interface, vlan=vlan)

        cmd1 = 'echo > DEVICE={interface}.{vlan} {file_path}'\
               .format(vlan=vlan, file_path=file_path)
        cmd2 = 'echo > BOOTPROTO=static {file_path}'\
               .format(file_path=file_path)
        cmd3 = 'echo > ONBOOT=yes {file_path}'\
               .format(file_path=file_path)
        cmd4 = 'echo > USERCTL=no {file_path}'\
               .format(file_path=file_path)
        cmd5 = 'echo > VLAN=yes {file_path}'\
               .format(file_path=file_path)
        cmd6 = 'ifup {interface}.{vlan}'.format(interface=interface, vlan=vlan)

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)
        host.run_bash_command(cmd3)
        host.run_bash_command(cmd4)
        host.run_bash_command(cmd5)
        host.run_bash_command(cmd6)

    def register_to_rhn(self, host):
        LOG.info('{time} {fqdn}: registering to rhn'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        rhn_user = self.job_dict[CREDENTIALS_CONFIG_FILE_SECTION]['rhn_user']
        rhn_pass = self.job_dict[CREDENTIALS_CONFIG_FILE_SECTION]['rhn_pass']
        cmd = 'rhnreg_ks --serverUrl=https://xmlrpc.rhn.redhat.com/XMLRPC ' \
              '--username={rhn_user} --password={rhn_pass} ' \
              '--profilename={fqdn} --nohardware --novirtinfo' \
              ' --nopackages --use-eus-channel --force'\
              .format(fqdn=host.fqdn, rhn_user=rhn_user, rhn_pass=rhn_pass)
        host.run_bash_command(cmd)

    def create_tunnel_interface(self, host):
        interface_file_location = '/etc/sysconfig/network-scripts'
        interface_file_name = 'ifcfg-{name}'.format(name=host.tenant_interface)
        interface_file_path = os.path.join(interface_file_location,
                                           interface_file_name)
        tun_subnet = \
            self.job_dict[ENVIRONMENT_CONFIG_FILE_SECTION]['tunneling_subnet']

        cmd1 = "ifconfig {i} | grep -v inet6 | awk \'/inet/ {print $2}\' | " \
               "cut -d\"\.\" -f 4".format(i=host.mgmt_interface)

        octate, stderr = host.run_bash_command(cmd1)

        cmd2 = 'sed -i s/^{option}=.*/{option}="{value}"/g {file_path}'\
               .format(option='BOOTPROTO', value='STATIC',
                       file_path=interface_file_path)
        cmd3 = 'sed -i s/^{option}=.*/{option}="{value}"/g {file_path}'\
               .format(option='ONBOOT', value='yes',
                       file_path=interface_file_path)
        cmd4 = 'echo >> IPADDR={tun_subnet}.{octate}'\
               .format(tun_subnet=tun_subnet, octate=octate)
        cmd5 = 'echo >> NETMASK=255.255.255.0'
        if host.os_name == 'rhel6':
            cmd6 = 'ifdown {i}'.format(i=host.tenant_interface)
            cmd7 = 'ifup {i}'.format(i=host.tenant_interface)
        else:  # rhel7 or fedora
            cmd6 = 'nmcli connection reload'
            cmd7 = 'nmcli connection up {i}'.format(i=host.tenant_interface)

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)
        host.run_bash_command(cmd3)
        host.run_bash_command(cmd4)
        host.run_bash_command(cmd5)
        host.run_bash_command(cmd6)
        host.run_bash_command(cmd7)
