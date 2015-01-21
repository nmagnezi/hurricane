import logging
import pprint
from time import sleep

from config import consts
from libs.deployer import Deployer
from libs.infra import Provisioning
from libs import utils


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Hurricane(object):

    def __init__(self, conf):
        self.CONF = conf
        self.hosts_fqdn = self.get_hosts_list()
        self.provisioner = Provisioning(self.CONF)
        self.deployer = None  # must provision before spawning Deployer instance

    def get_hosts_list(self):
        return [i.split('/')[0] for i in
                self.CONF.job_params.hosts_and_roles.split(", ")]

    def provision(self):
        if utils.do_exec(self.CONF.job_params.reprovision):
            if utils.do_exec(self.CONF.job_params.rebuild_test_client) and \
               utils.do_exec(self.CONF.job_params.run_tests):
                test_client_fqdn = self.CONF.job_params.test_client_fqdn
                self.hosts_fqdn.append(test_client_fqdn)
            self.provisioner.provision_hosts(list(set(self.hosts_fqdn)))
        else:
            LOG.info('Reprovisioning disabled, Skipping...')

    def configure_repositories(self):
        if utils.do_exec(self.CONF.job_params.repositories):
            self.deployer.config_all_openstack_hosts('remove_all_yum_repos')
            self.deployer.create_yum_repos_all_openstack_hosts(
                self.CONF.job_params.repositories,
                self.CONF.job_params.openstack_build)
        else:
            LOG.info('Repository list is empty, Skipping...')

    def preinstall_configs(self):
        if utils.do_exec(self.CONF.job_params.pre_install_configs):
            pre_confs = self.CONF.job_params.pre_install_configs
            self.deployer.config_all_openstack_hosts(pre_confs)
        else:
            LOG.info('Pre installation configs list is empty, Skipping...')

    def install_openstack(self):
        if utils.do_exec(self.CONF.job_params.install_openstack):
            if self.CONF.job_params.openstack_installer == 'packstack':
                controller_host = self.deployer.determine_controller_host()
                networker_host = self.deployer.determine_networker_host()
                controller_host.open_connection()
                self.deployer.generate_ssh_key(controller_host)
                self.deployer.distribute_public_key_to_openstack_hosts(
                    controller_host)
                self.deployer.configurations.install_rpm(controller_host,
                                                         'openstack-packstack')
                self.deployer.installer.generate_answer_file(controller_host)
                self.deployer.installer\
                    .configure_answer_file(controller_host,
                                           networker_host,
                                           self.deployer.openstack_hosts)
                self.deployer.installer.install_openstack(controller_host)
                LOG.info('Rebooting All nodes in due to possible kernel update')
                self.provisioner.reboot_hosts(list(set(self.hosts_fqdn)))
                # allows host to gracefully reboot
                sleep(consts.SshIntervals.REBOOT_SLEEP)
                self.provisioner\
                    .wait_for_reprovision_to_finish(list(set(self.hosts_fqdn)))
        else:
            LOG.info('OpenStack installation set to false, Skipping...')

    def postinstall_configs(self):
        if utils.do_exec(self.CONF.job_params.post_install_configs):
            post_confs = self.CONF.job_params.post_install_configs
            self.deployer.config_all_openstack_hosts(post_confs)
        else:
            LOG.info('Post installation configs list is empty, Skipping...')

    def run_tests(self):
        """
        WIP
        """
        if utils.do_exec(self.CONF.job_params.run_tests):
            tests_repository = self.CONF.job_params.tests_repository
            tests = self.CONF.job_params.tests
            #if utils.do_exec(main.CONF.job_params.rebuild_test_client):

    def run(self):
        LOG.info(pprint.pformat(self.CONF))
        self.provision()
        self.deployer = Deployer(self.CONF)
        self.preinstall_configs()
        self.install_openstack()
        self.postinstall_configs()
        # self.run_tests() #WIP