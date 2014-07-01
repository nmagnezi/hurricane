import logging
import datetime

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


JOB_CONFIG_FILE_SECTION = 'job_params'
REPO_CONFIG_FILE_SECTION = 'repositories'

# Pre and Post installation configurations


class Configs(object):

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

    def restart_linux_service(self, host, service_name):
        """work in progress"""
        pass

    def register_to_rhn(self, host):
        """work in progress"""
        pass

    def register_to_sm(self, host):
        """work in progress"""
        pass

    def create_ext_net_interface(self, host):
        """work in progress"""
        pass


    def create_tunnel_interface(self, host):
        """work in progress"""
        pass

    def add_ext_net_interface_to_ovs_bridge(self, host):
        """work in progress"""
        pass

