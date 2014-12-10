import logging
import pprint
from libs.deployer import Deployer
from libs.infra import Provisioning
import libs.utils as utils
import config.constants as c

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


def hurricane():
    job_dict = utils.build_dict_from_file(c.CONFIG_FILE_PATH)
    LOG.info(pprint.pformat(job_dict))
    utils.print_job_dict(job_dict)

    # Reprovision Hosts via foreman
    if utils.do_exec(job_dict[c.JOB]['reprovision']):
        provisioner = Provisioning(job_dict)
        hosts_fqdn = [i.split('/')[0] for i in
                      job_dict[c.JOB]['hosts_and_roles'].split(", ")]
        if utils.do_exec(job_dict[c.JOB]['rebuild_test_client']) and \
           utils.do_exec(job_dict[c.JOB]['run_tests']):
            test_client_fqdn = job_dict[c.JOB]['test_client_fqdn']
            hosts_fqdn.append(test_client_fqdn)
        provisioner.provision_hosts(hosts_fqdn)
    else:
        LOG.info('Reprovisioning disabled, Skipping...')

    main = Deployer(job_dict)

    # Configure repositories
    if utils.do_exec(main.job_dict[c.JOB]['repositories']):
        main.config_all_openstack_hosts('remove_all_yum_repos')
        main.create_yum_repos_all_openstack_hosts(
            main.job_dict[c.JOB]['repositories'],
            main.job_dict[c.JOB]['openstack_build'])
    else:
        LOG.info('Repository list is empty, Skipping...')

    # Pre installation configurations
    if utils.do_exec(main.job_dict[c.JOB]['pre_install_configs']):
        main.config_all_openstack_hosts(
            main.job_dict[c.JOB]['pre_install_configs'])
    else:
        LOG.info('Pre installation configurations list is empty, Skipping...')

    # OpenStack installation
    if utils.do_exec(main.job_dict[c.JOB]['install_openstack']):
        if main.job_dict[c.JOB]['openstack_installer'] == 'packstack':
            if utils.do_exec(main.job_dict[c.JOB]['ext_vlan']):
                main.config_networker_ext_net_interface()
            controller_host = main.determine_controller_host()
            controller_host.open_connection()
            main.generate_ssh_key(controller_host)
            main.distribute_public_key_to_openstack_hosts(controller_host)
            main.configurations.install_rpm(controller_host,
                                            'openstack-packstack')
            main.installer.generate_answer_file(controller_host)
            main.installer.configure_answer_file(controller_host,
                                                 main.openstack_hosts)
            main.installer.install_openstack(controller_host)

    else:
        LOG.info('OpenStack installation set to false, Skipping...')

    # Post installation configurations
    if utils.do_exec(main.job_dict[c.JOB]['post_install_configs']):
        main.config_all_openstack_hosts(
            main.job_dict[c.JOB]['Post_install_configs'])
    else:
        LOG.info('Post installation configurations list is empty, Skipping...')

    # Run Tests (WIP)
    if utils.do_exec(main.job_dict[c.JOB]['run_tests']):
        tests_repository = main.job_dict[c.JOB]['tests_repository']
        tests = main.job_dict[c.JOB]['tests']
        #if utils.do_exec(main.job_dict[c.JOB]['rebuild_test_client']):


if __name__ == '__main__':
    hurricane()