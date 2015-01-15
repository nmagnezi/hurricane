import logging
import os
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


def run(config_file):
    # TODO: check that the config file was opened successfully.
    CONF = utils.file2bunch(os.path.join(consts.Paths.CONFIG_FILE_DIRECTORY,
                                         config_file))
    LOG.info(pprint.pformat(CONF))
    hosts_fqdn = [i.split('/')[0] for i in 
                  CONF.job_params.hosts_and_roles.split(", ")]
    provisioner = Provisioning(CONF)

    # Reprovision Hosts via foreman
    if utils.do_exec(CONF.job_params.reprovision):
        if utils.do_exec(CONF.job_params.rebuild_test_client) and \
           utils.do_exec(CONF.job_params.run_tests):
            test_client_fqdn = CONF.job_params.test_client_fqdn
            hosts_fqdn.append(test_client_fqdn)
        provisioner.provision_hosts(list(set(hosts_fqdn)))
    else:
        LOG.info('Reprovisioning disabled, Skipping...')

    main = Deployer(CONF)

    # Configure repositories
    if utils.do_exec(main.CONF.job_params.repositories):
        main.config_all_openstack_hosts('remove_all_yum_repos')
        main.create_yum_repos_all_openstack_hosts(
            main.CONF.job_params.repositories, 
            main.CONF.job_params.openstack_build)
    else:
        LOG.info('Repository list is empty, Skipping...')

    # Pre installation configurations
    if utils.do_exec(main.CONF.job_params.pre_install_configs):
        main.config_all_openstack_hosts(
            main.CONF.job_params.pre_install_configs)
    else:
        LOG.info('Pre installation configurations list is empty, Skipping...')

    # OpenStack installation
    if utils.do_exec(main.CONF.job_params.install_openstack):
        if main.CONF.job_params.openstack_installer == 'packstack':
            controller_host = main.determine_controller_host()
            networker_host = main.determine_networker_host()
            controller_host.open_connection()
            main.generate_ssh_key(controller_host)
            main.distribute_public_key_to_openstack_hosts(controller_host)
            main.configurations.install_rpm(controller_host,
                                            'openstack-packstack')
            main.installer.generate_answer_file(controller_host)
            main.installer.configure_answer_file(controller_host,
                                                 networker_host,
                                                 main.openstack_hosts)
            main.installer.install_openstack(controller_host)
            LOG.info('Rebooting All nodes in due to possible kernel update')
            provisioner.reboot_hosts(list(set(hosts_fqdn)))
            # allows host to gracefully reboot
            sleep(consts.SshIntervals.REBOOT_SLEEP)
            provisioner.wait_for_reprovision_to_finish(list(set(hosts_fqdn)))

    else:
        LOG.info('OpenStack installation set to false, Skipping...')

    # Post installation configurations
    if utils.do_exec(main.CONF.job_params.post_install_configs):
        main.config_all_openstack_hosts(
            main.CONF.job_params.post_install_configs)
    else:
        LOG.info('Post installation configurations list is empty, Skipping...')

    # Run Tests (WIP)
    if utils.do_exec(main.CONF.job_params.run_tests):
        tests_repository = main.CONF.job_params.tests_repository
        tests = main.CONF.job_params.tests
        #if utils.do_exec(main.CONF.job_params.rebuild_test_client):