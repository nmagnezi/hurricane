import logging
import os

from hurricane import utils

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Configs(object):
    # Pre and Post installation configurations

    def __init__(self, conf):
        self.repositories = conf.repositories
        self.rhos = conf.ci.rhos_release
        self.openstack_version = conf.job_params.openstack_version
        self.openstack_build = conf.job_params.openstack_build
        self.ext_vlan = conf.job_params.ext_vlan
        self.rhn_user = conf.credentials.rhn_user
        self.rhn_pass = conf.credentials.rhn_pass
        self.tun_subnet = conf.environment.tunneling_subnet
        self.answer_file = conf.job_params.installer_conf_file

    def create_yum_repo(self, host, repo_name, build):
        LOG.info('{time} {fqdn}: Creating yum repo {repo_name}'
                 .format(time=utils.timestamp(),
                         fqdn=host.fqdn,
                         repo_name=repo_name))

        repo_url = self.repositories[repo_name]
        if '{build}' in repo_url:  # check if there is a build number to inject
            repo_url = str(repo_url).format(build=build)

        host.run_bash_command('echo [{name}] > /etc/yum.repos.d/'
                              '{name}.repo'.format(name=repo_name))
        host.run_bash_command(('echo name={name} >> /etc/yum.repos.d/'
                               '{name}.repo'.format(name=repo_name)))
        host.run_bash_command(('echo baseurl={base_url} >> /etc/yum.repos.d/'
                               '{name}.repo'.format(base_url=repo_url,
                                                    name=repo_name)))
        host.run_bash_command(('echo enabled=1 >> /etc/yum.repos.d/'
                               '{name}.repo'.format(name=repo_name)))
        host.run_bash_command(('echo gpgcheck=0 >> /etc/yum.repos.d/'
                               '{name}.repo'.format(name=repo_name)))

    def clean_yum_cache(self, host):
        LOG.info('{time} {fqdn}: Cleaning yum cache'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        host.run_bash_command('yum clean all')

    def remove_all_yum_repos(self, host):
        LOG.info('{time} {fqdn}: Removing all yum repos'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        host.run_bash_command('mv /etc/yum.repos.d/*.repo /tmp')

    def yum_update(self, host):
        LOG.info('{time} {fqdn}: updating all packages'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        host.run_bash_command('yum update -y --nogpgcheck')

    def install_rpm(self, host, rpm_name):
        LOG.info('{time} {fqdn}: installing {rpm}'
                 .format(time=utils.timestamp(),
                         fqdn=host.fqdn,
                         rpm=rpm_name))
        host.run_bash_command('yum install -y --nogpgcheck {rpm}'
                              .format(rpm=rpm_name))

    def uninstall_rpm(self, host, rpm_name):
        LOG.info('{time} {fqdn}: removing {rpm}'.format(time=utils.timestamp(),
                                                        fqdn=host.fqdn,
                                                        rpm=rpm_name))
        host.run_bash_command('yum remove -y {rpm}'.format(rpm=rpm_name))

    def yum_disable_repo(self, host, repo_name):
        LOG.info('{time} {fqdn}: disabling {repo}'
                 .format(time=utils.timestamp(),
                         fqdn=host.fqdn,
                         repo=repo_name))
        host.run_bash_command('yum-config-manager --disable {repo}'
                              .format(repo=repo_name))

    def disable_epel(self, host):
        self.yum_disable_repo(host, 'epel')

    def tlv_openstack_repo(self, host):
        LOG.info('{time} {fqdn}: updating OpenStack repo path'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        host.run_bash_command("sed -i s/lab.bos/eng.tlv/g "
                              "/etc/yum.repos.d/rhos-release*")

    def disable_and_persist_selinux(self, host):
        LOG.info('{time} {fqdn}: disabling SELinux'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        host.run_bash_command('setenforce 0')
        host.run_bash_command('sed -i "s/^SELINUX=.*/SELINUX=permissive/g" '
                              '/etc/selinux/config')
        host.run_bash_command('sed -i "s/^SELINUX=.*/SELINUX=permissive/g" '
                              '/etc/sysconfig/selinux')

    def rhos_release(self, host):
        rpm_url = self.rhos
        self.install_rpm(host, rpm_url)
        vers = {'grizzly': '3', 'havana': '4', 'icehouse': '5',
                'icehouse_adv': '5a', 'juno': '6', 'juno_adv': '6a',
                'kilo': '7'}
        host.run_bash_command('ls -1 /etc/yum.repos.d/*.repo | grep -v "rhos" '
                              '| xargs rm -f')
        host.run_bash_command('yum update -y rhos-release')
        host.run_bash_command('rhos-release {ver} -p {puddle}'
                              .format(ver=vers[self.openstack_version],
                                      puddle=self.openstack_build))

    def restart_linux_service(self, host, service_name):
        LOG.info('{time} {fqdn}: restarting {service_name}'
                 .format(time=utils.timestamp(),
                         fqdn=host.fqdn,
                         service_name=service_name))
        if 'rhel6' in host.os_name:
            cmd = ('service {service} restart'
                   .format(service_name=service_name))

        else:  # rhel7 or fedora
            cmd = ('systemctl restart {service}.service'
                   .format(service_name=service_name))

        host.run_bash_command(cmd)

    def ovs_add_port_to_br(self, host, br_name, port_name):
        LOG.info('{time} {fqdn}: adding {port_name} to {br_name}'
                 .format(time=utils.timestamp(), fqdn=host.fqdn,
                         port_name=port_name, br_name=br_name))
        host.run_bash_command('ovs-vsctl add-port {br_name} {port_name}'
                              .format(br_name=br_name, port_name=port_name))

    def add_ext_net_port_to_ovs_br(self, host):
        self.ovs_add_port_to_br(host, 'br-ex', host.tenant_interface)

    def create_sub_interface(self, host):
        """This function will read the vlan range from config file

        following format: 'x:y' where the x is that start and the y is the end
        of that range.
        it will create a sub interface for each vlan in the given range.
        the function does support a single vlan as follows (example): '100:100'
        :param host: the host that will be added with sub interfaces
        :return: nothing
        """
        if not host.host_type == 'vm':
            ext_vlan_range = self.ext_vlan.split(':')
            sub_interfaces = list(xrange(int(ext_vlan_range[0]),
                                         int(ext_vlan_range[-1]) + 1))
            for sub_interface in sub_interfaces:
                iface_file_name = ('ifcfg-{name}.{vlan}'
                                   .format(name=host.tenant_interface,
                                           vlan=sub_interface))
                interface_file_location = '/etc/sysconfig/network-scripts'
                interface_file_path = os.path.join(interface_file_location,
                                                   iface_file_name)
                LOG.info('{time} {fqdn}: Creating sub interface: '
                         '{interface_file_name}'
                         .format(time=utils.timestamp(), fqdn=host.fqdn,
                                 interface_file_name=iface_file_name))
                bootproto = 'none' if 'rhel7' in host.os_name else 'dhcp'
                host.run_bash_command('echo DEVICE="{name}.{vlan}" > '
                                      '{file_path}'
                                      .format(name=host.tenant_interface,
                                              vlan=sub_interface,
                                              file_path=interface_file_path))
                host.run_bash_command('echo BOOTPROTO={bootproto} >> '
                                      '{file_path}'
                                      .format(file_path=interface_file_path,
                                              bootproto=bootproto))
                host.run_bash_command('echo ONBOOT=yes >> {file_path}'
                                      .format(file_path=interface_file_path))
                host.run_bash_command('echo USERCTL=no >> {file_path}'
                                      .format(file_path=interface_file_path))
                host.run_bash_command('echo VLAN=yes >> {file_path}'
                                      .format(file_path=interface_file_path))
                host.run_bash_command('echo NM_CONTROLLED=no >> {file_path}'
                                      .format(file_path=interface_file_path))
                host.run_bash_command('ifdown {iface_file_name}'
                                      .format(iface_file_name=iface_file_name))
                host.run_bash_command('ifup {iface_file_name}'
                                      .format(iface_file_name=iface_file_name))

    def register_to_rhn(self, host):
        """
        :param host: the host that will be registered to rhn
        """
        LOG.info('{time} {fqdn}: registering to rhn'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        host.run_bash_command('rhnreg_ks --serverUrl='
                              'https://xmlrpc.rhn.redhat.com/XMLRPC '
                              '--username={rhn_user} --password={rhn_pass} '
                              '--profilename={fqdn} --nohardware --novirtinfo '
                              '--nopackages --use-eus-channel --force'
                              .format(fqdn=host.fqdn,
                                      rhn_user=self.rhn_user,
                                      rhn_pass=self.rhn_pass))

    def create_tunnel_interface(self, host):
        """
        Assumption, vm type host can only be used as openstack controller
        therefor, no need for tunnel interface.
        :param host: the host in which the tunnel interface will be created in.
        """
        if not host.host_type == 'vm':
            interface_file_location = '/etc/sysconfig/network-scripts'
            interface_file_name = ('ifcfg-{name}'
                                   .format(name=host.tenant_interface))
            interface_file_path = os.path.join(interface_file_location,
                                               interface_file_name)
            octate, stderr = host.run_bash_command(
                ('ifconfig {i}'.format(i=host.mgmt_interface) +
                 " | grep -v inet6 | awk \'/inet/ {print $2}\'"
                 " | cut -d\".\" -f 4"))
            host.run_bash_command('sed -i s/^{option}=.*/{option}="{value}"/g '
                                  '{file_path}'
                                  .format(option='BOOTPROTO',
                                          value='static',
                                          file_path=interface_file_path))
            host.run_bash_command('sed -i s/^{option}=.*/{option}="{value}"/g '
                                  '{file_path}'
                                  .format(option='ONBOOT',
                                          value='yes',
                                          file_path=interface_file_path))
            host.run_bash_command('echo IPADDR={tun_subnet}.{octate} >> '
                                  '{file_path}'
                                  .format(tun_subnet=self.tun_subnet,
                                          octate=octate,
                                          file_path=interface_file_path))
            host.run_bash_command('echo NETMASK=255.255.255.0 >> {file_path}'
                                  .format(file_path=interface_file_path))
            host.run_bash_command('ifdown {iface_file_name}'
                                  .format(iface_file_name=interface_file_name))
            host.run_bash_command('ifup {iface_file_name}'
                                  .format(iface_file_name=interface_file_name))

    def disable_nm(self, host):
        """
        Disable NetworkManager due to a known issue.
        """
        LOG.info('{time} {fqdn}: Switching off NetworkManager'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        host.run_bash_command('systemctl disable NetworkManager')
        host.run_bash_command('systemctl stop NetworkManager')
        host.run_bash_command('systemctl restart network')

    def prep_for_robot(self, host):
        """
        This function is a preparation for Robot tests.
        That test system expects to find the answer file at: /root/ANSWER_FILE
        :param host: a host which holds the packstack answer file
        """
        LOG.info('{time} {fqdn}: Changing answer file name to ANSWER_FILE'
                 .format(time=utils.timestamp(), fqdn=host.fqdn))
        robot_file = 'ANSWER_FILE'
        host.run_bash_command('mv {answer_file} {robot_file}'
                              .format(answer_file=self.answer_file,
                                      robot_file=robot_file))