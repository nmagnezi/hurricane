import logging
import datetime
import os
import config.constants as c

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Configs(object):
# Pre and Post installation configurations

    def __init__(self, job_dict):
        self.job_dict = job_dict

    def create_yum_repo(self, host, repo_name, build):
        LOG.info('{time} {fqdn}: Creating yum repo {repo_name}'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn, repo_name=repo_name))

        repo_url = self.job_dict[c.REPO][repo_name]
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
        cmd = 'yum install -y --nogpgcheck {rpm}'.format(rpm=rpm_name)
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

    def tlv_openstack_repo(self, host):
        LOG.info('{time} {fqdn}: updating OpenStack repo path'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        cmd = "sed -i s/lab.bos/eng.tlv/g /etc/yum.repos.d/rhos-release*"
        host.run_bash_command(cmd)

    def disable_and_persist_selinux(self, host):
        LOG.info('{time} {fqdn}: disabling SELinux'
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
        rpm_url = self.job_dict[c.CI]['rhos-release']
        self.install_rpm(host, rpm_url)
        cmd1 = 'ls -1 /etc/yum.repos.d/*.repo | grep -v "rhos" | xargs rm -f'
        cmd2 = 'yum update -y rhos-release'
        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)

    def rhos_release_grizzly(self, host):
        self.rhos_release(host)
        openstack_build = \
            self.job_dict[c.JOB]['openstack_build']
        cmd1 = 'rhos-release 3'
        cmd2 = 'sed -i s/"latest\/\RHOS-3.0"/"{puddle}\/\RHOS-3.0"/g ' \
               '/etc/yum.repos.d/rhos-release*'.format(puddle=openstack_build)

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)

    def rhos_release_havana(self, host):
        self.rhos_release(host)
        openstack_build = \
            self.job_dict[c.JOB]['openstack_build']
        cmd1 = 'rhos-release 4'
        cmd2 = 'sed -i s/"latest\/\RHOS-4.0"/"{puddle}\/\RHOS-4.0"/g ' \
               '/etc/yum.repos.d/rhos-release*'.format(puddle=openstack_build)

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)

    def rhos_release_icehouse(self, host):
        self.rhos_release(host)
        openstack_build = self.job_dict[c.JOB]['openstack_build']
        operating_system = self.job_dict[c.JOB]['operating_system']

        cmd1 = 'rhos-release 5'
        if operating_system == 'rhel6.5':
            cmd2 = 'sed -i ' \
                   's/"latest\/\RH6-RHOS-5.0"/"{puddle}\/\RH6-RHOS-5.0"/g ' \
                   '/etc/yum.repos.d/rhos-release*'\
                   .format(puddle=openstack_build)
        else:  # operating_system == 'rhel7.0'
            cmd2 = 'sed -i ' \
                   's/"latest\/\RH7-RHOS-5.0"/"{puddle}\/\RH7-RHOS-5.0"/g ' \
                   '/etc/yum.repos.d/rhos-release*'\
                   .format(puddle=openstack_build)

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)

    def rhos_release_icehouse_adv(self, host):
        self.rhos_release(host)
        openstack_build = self.job_dict[c.JOB]['openstack_build']'
        cmd = 'rhos-release 5a -p {puddle}'.format(puddle=openstack_build)
        host.run_bash_command(cmd)

    def rhos_release_juno(self, host):
        self.rhos_release(host)
        openstack_build = self.job_dict[c.JOB]['openstack_build']
        cmd = 'rhos-release 6 -p {puddle}'.format(puddle=openstack_build)
        host.run_bash_command(cmd)

    def rhos_release_juno_adv(self, host):
        self.rhos_release(host)
        openstack_build = self.job_dict[c.JOB]['openstack_build']
        cmd = 'rhos-release 6a -p {puddle}'.format(puddle=openstack_build)
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

    def create_sub_interface(self, host):
        if not host.host_type == 'vm':
            ext_vlan = self.job_dict[c.JOB]['ext_vlan']
            interface_file_name = 'ifcfg-{name}.{vlan}'\
                                  .format(name=host.tenant_interface,
                                          vlan=ext_vlan)
            interface_file_location = '/etc/sysconfig/network-scripts'
            interface_file_path = os.path.join(interface_file_location,
                                               interface_file_name)

            LOG.info('{time} {fqdn}: Creating sub interface: '
                     '{interface_file_name}'
                     .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                                   '%H:%M:%S'),
                             fqdn=host.fqdn,
                             interface_file_name=interface_file_name))

            cmd1 = 'echo DEVICE="{name}.{vlan}" > {file_path}'\
                   .format(name=host.tenant_interface, vlan=ext_vlan,
                           file_path=interface_file_path)
            cmd2 = 'echo BOOTPROTO=dhcp >> {file_path}'\
                   .format(file_path=interface_file_path)
            cmd3 = 'echo ONBOOT=yes >> {file_path}'\
                   .format(file_path=interface_file_path)
            cmd4 = 'echo USERCTL=no >> {file_path}'\
                   .format(file_path=interface_file_path)
            cmd5 = 'echo VLAN=yes >> {file_path}'\
                   .format(file_path=interface_file_path)
            cmd6 = 'echo NM_CONTROLLED=no >> {file_path}'\
                   .format(file_path=interface_file_path)
            cmd7 = 'ifdown {interface_file_name}'\
                   .format(interface_file_name=interface_file_name)
            cmd8 = 'ifup {interface_file_name}'\
                   .format(interface_file_name=interface_file_name)
            host.run_bash_command(cmd1)
            host.run_bash_command(cmd2)
            host.run_bash_command(cmd3)
            host.run_bash_command(cmd4)
            host.run_bash_command(cmd5)
            host.run_bash_command(cmd6)
            host.run_bash_command(cmd7)
            host.run_bash_command(cmd8)

    def register_to_rhn(self, host):
        """
        :param host: the host that will be registered to rhn
        """
        LOG.info('{time} {fqdn}: registering to rhn'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        rhn_user = self.job_dict[c.CREDENTIALS]['rhn_user']
        rhn_pass = self.job_dict[c.CREDENTIALS]['rhn_pass']
        cmd = 'rhnreg_ks --serverUrl=https://xmlrpc.rhn.redhat.com/XMLRPC ' \
              '--username={rhn_user} --password={rhn_pass} ' \
              '--profilename={fqdn} --nohardware --novirtinfo' \
              ' --nopackages --use-eus-channel --force'\
              .format(fqdn=host.fqdn, rhn_user=rhn_user, rhn_pass=rhn_pass)
        host.run_bash_command(cmd)

    def create_tunnel_interface(self, host):
        """
        Assumption, vm type host can only be used as openstack controller
        therefor, no need for tunnel interface.
        :param host: the host in which the tunnel interface will be created in.
        """
        if not host.host_type == 'vm':
            interface_file_location = '/etc/sysconfig/network-scripts'
            interface_file_name = 'ifcfg-{name}'\
                .format(name=host.tenant_interface)
            interface_file_path = os.path.join(interface_file_location,
                                               interface_file_name)
            tun_subnet = self.job_dict[c.ENVIRONMENT]['tunneling_subnet']

            cmd1 = 'ifconfig {i}'.format(i=host.mgmt_interface) + \
                   " | grep -v inet6 | awk \'/inet/ {print $2}\'" \
                   " | cut -d\".\" -f 4"

            octate, stderr = host.run_bash_command(cmd1)

            cmd2 = 'sed -i s/^{option}=.*/{option}="{value}"/g {file_path}'\
                   .format(option='BOOTPROTO', value='static',
                           file_path=interface_file_path)
            cmd3 = 'sed -i s/^{option}=.*/{option}="{value}"/g {file_path}'\
                   .format(option='ONBOOT', value='yes',
                           file_path=interface_file_path)
            cmd4 = 'echo IPADDR={tun_subnet}.{octate} >> {file_path}'\
                   .format(tun_subnet=tun_subnet, octate=octate,
                           file_path=interface_file_path)
            cmd5 = 'echo NETMASK=255.255.255.0 >> {file_path}'\
                   .format(file_path=interface_file_path)
            cmd6 = 'ifdown {interface_file_name}'\
                   .format(interface_file_name=interface_file_name)
            cmd7 = 'ifup {interface_file_name}'\
                   .format(interface_file_name=interface_file_name)

            host.run_bash_command(cmd2)
            host.run_bash_command(cmd3)
            host.run_bash_command(cmd4)
            host.run_bash_command(cmd5)
            host.run_bash_command(cmd6)
            host.run_bash_command(cmd7)

    def disable_nm(self, host):
        """
        Disable NetworkManager due to a known issue.
        """
        LOG.info('{time} {fqdn}: Switching off NetworkManager'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        cmd1 = 'systemctl disable NetworkManager'
        cmd2 = 'systemctl stop NetworkManager'
        cmd3 = 'systemctl restart network'

        host.run_bash_command(cmd1)
        host.run_bash_command(cmd2)
        host.run_bash_command(cmd3)

    def prep_for_robot(self, host):
        """
        This function is a preparation for Robot tests.
        That test system expects to find the answer file at: /root/ANSWER_FILE
        :param host: a host which holds the packstack answer file
        """
        LOG.info('{time} {fqdn}: Changing answer file name to ANSWER_FILE'
                 .format(time=datetime.datetime.now().strftime('%Y-%m-%d '
                                                               '%H:%M:%S'),
                         fqdn=host.fqdn))
        answer_file = self.job_dict['job_params']['installer_conf_file']
        robot_file = 'ANSWER_FILE'
        cmd = 'mv {answer_file} {robot_file}'.format(answer_file=answer_file,
                                                     robot_file=robot_file)
        host.run_bash_command(cmd)