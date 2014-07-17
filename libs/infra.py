import paramiko
from time import sleep
import json
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

CREDENTIALS_SECTION = 'credentials'
ENVIRONMENT_SECTION = 'environment'
JOB_SECTION = 'job_params'
FOREMAN_PARAMS_SECTION = 'foreman_params'

RECONNECTION_RETRIES = 1200
RECONNECTION_INTERVAL = 30
SSH_TIMEOUT = 3


class Provisioning(object):

    def __init__(self, job_dict):
        self.foreman_user = job_dict[CREDENTIALS_SECTION]['foreman_user']
        self.foreman_pass = job_dict[CREDENTIALS_SECTION]['foreman_pass']
        self.test_server_user = job_dict[CREDENTIALS_SECTION]['default_user']
        self.test_server_pass = job_dict[CREDENTIALS_SECTION]['default_pass']
        self.foreman_url = job_dict[ENVIRONMENT_SECTION]['foreman_url']
        self.test_server = job_dict[ENVIRONMENT_SECTION]['test_server']
        self.operating_system = job_dict[JOB_SECTION]['operating_system']
        self.host_user = job_dict[CREDENTIALS_SECTION]['default_user']
        self.host_pass = job_dict[CREDENTIALS_SECTION]['default_pass']
        self.foreman_params_list = \
            (job_dict[FOREMAN_PARAMS_SECTION][self.operating_system.lower()])\
            .split()
        self.test_server_ssh = paramiko.SSHClient()
        self.host_ssh = paramiko.SSHClient()

    def provision_hosts(self, hosts_fqdn_list):
        self.connect_to_test_server()
        self.change_os_and_medium(hosts_fqdn_list)
        self.set_build_in_foreman(hosts_fqdn_list)
        self.reboot_hosts(hosts_fqdn_list)
        sleep(10)  # allows host to gracefully reboot
        self.wait_for_reprovision_to_finish(hosts_fqdn_list)
        self.disconnect_from_test_server()

    def change_os_and_medium(self, hosts_fqdn_list):
        os_name = self.foreman_params_list[0]
        os_major = self.foreman_params_list[1]
        os_minor = self.foreman_params_list[2]
        medium = self.foreman_params_list[3]
        ptable = ' '.join(self.foreman_params_list[4:])
        for host_fqdn in hosts_fqdn_list:
            bash_cmd = 'curl -s -H "Accept:application/json" -k -u ' \
                       '{foreman_user}:{foreman_pass} ' \
                       '{foreman_url}/api/operatingsystems -X GET -o -'\
                .format(foreman_user=self.foreman_user,
                        foreman_pass=self.foreman_pass,
                        foreman_url=self.foreman_url)
            ssh_stdin, ssh_stdout, ssh_stderr = \
                self.test_server_ssh.exec_command(bash_cmd)
            os_json = ssh_stdout.read()
            os_id = self.get_foreman_os_id_by_json(os_json, os_name,
                                                   os_major, os_minor)
            medium_id = self.get_foreman_medium_id_by_json(os_json, os_name,
                                                           os_major, os_minor,
                                                           medium)
            ptables_id = self.get_foreman_ptable_id_by_json(os_json, os_name,
                                                            os_major, os_minor,
                                                            ptable)
            bash_cmd = 'curl -s -H "Accept:application/json" -k -u ' \
                       '{foreman_user}:{foreman_pass} ' \
                       '{foreman_url}/api/hosts/{host} -X PUT -d ' \
                       '"host[operatingsystem_id]={os_id}" -d ' \
                       '"host[medium_id]={medium_id}" -d ' \
                       '"host[ptable_id]={ptables_id}"'\
                .format(foreman_user=self.foreman_user,
                        foreman_pass=self.foreman_pass,
                        foreman_url=self.foreman_url,
                        host=host_fqdn, os_id=os_id,
                        medium_id=medium_id, ptables_id=ptables_id)
            self.test_server_ssh.exec_command(bash_cmd)
            LOG.info('Foreman: Changed host {host} OS to {os}'
                     .format(os=self.operating_system, host=host_fqdn))

    def get_foreman_os_id_by_json(self, os_json, os_name, os_major, os_minor):
        os_dict = json.loads(os_json)
        os_id = [os['operatingsystem']['id'] for os in os_dict
                 if os['operatingsystem']['name'] == os_name
                    and os['operatingsystem']['major'] == os_major
                    and os['operatingsystem']['minor'] == os_minor][0]
        return os_id

    def get_foreman_ptable_id_by_json(self, os_json, os_name, os_major,
                                      os_minor, ptable_name):
        os_dict = json.loads(os_json)
        ptable_id = [ptable['ptable']['id'] for ptable in
                     [os['operatingsystem']['ptables'] for os in os_dict
                      if os['operatingsystem']['name'] == os_name
                         and os['operatingsystem']['major'] == os_major
                         and os['operatingsystem']['minor'] == os_minor][0]
                         if ptable['ptable']['name'] == ptable_name][0]
        return ptable_id

    def get_foreman_medium_id_by_json(self, os_json, os_name, os_major,
                                      os_minor, medium_name):
        os_dict = json.loads(os_json)
        medium_id = [medium['medium']['id'] for medium in
                     [os['operatingsystem']['media'] for os in os_dict
                      if os['operatingsystem']['name'] == os_name
                         and os['operatingsystem']['major'] == os_major
                         and os['operatingsystem']['minor'] == os_minor][0]
                         if medium['medium']['name'] == medium_name][0]
        return medium_id

    def set_build_in_foreman(self, hosts_fqdn_list):
        for host_fqdn in hosts_fqdn_list:
            bash_cmd = 'curl -s -H "Accept:application/json" -k -u ' \
                       '{foreman_user}:{foreman_pass} ' \
                       '{foreman_url}/api/hosts/{host_fqdn} -X PUT -d ' \
                       '"host[build]=1" -o -'.\
                format(foreman_user=self.foreman_user,
                       foreman_pass=self.foreman_pass,
                       foreman_url=self.foreman_url, host_fqdn=host_fqdn)
            self.test_server_ssh.exec_command(bash_cmd)

    def connect_to_test_server(self):
        self.test_server_ssh.set_missing_host_key_policy(
            paramiko.AutoAddPolicy())
        self.test_server_ssh.connect(hostname=self.test_server,
                                     username=self.test_server_user,
                                     password=self.test_server_pass)
        LOG.info('Connected to test server: {test_server}'
                 .format(test_server=self.test_server))

    def disconnect_from_test_server(self):
        self.test_server_ssh.close()
        LOG.info('Disconnected from test server: {test_server}'
                 .format(test_server=self.test_server))

    def connect_to_host(self, host_fqdn):
            self.host_ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
            self.host_ssh.connect(hostname=host_fqdn, username=self.host_user,
                                  password=self.host_pass, timeout=SSH_TIMEOUT)
            LOG.info('Connected to host: {fqdn}'.format(fqdn=host_fqdn))

    def reboot_hosts(self, hosts_fqdn_list):
        for host_fqdn in hosts_fqdn_list:
            self.connect_to_host(host_fqdn)
            self.host_ssh.exec_command('reboot')
            LOG.info('Rebooting host: {fqdn}'.format(fqdn=host_fqdn))

    def wait_for_reprovision_to_finish(self, hosts_fqdn_list):
        # TODO: a thread to monitor each host provisioning till timeout/success.
        for host_fqdn in hosts_fqdn_list:
            LOG.info('Waiting for reprovision of: {fqdn}'
                     .format(fqdn=host_fqdn))
            for i in xrange(RECONNECTION_RETRIES):

                LOG.info('Attempting to open SSH connection to {fqdn}, '
                         'Attempt {i} out of {num_of_retries}'
                         .format(fqdn=host_fqdn, i=i,
                                 num_of_retries=RECONNECTION_RETRIES))
                try:
                    self.connect_to_host(host_fqdn)

                except Exception as e:
                    LOG.info('Failed to connect to {fqdn} with exception: '
                             '{exception}'.format(fqdn=host_fqdn, exception=e))
                    LOG.info('')
                    LOG.info('Sleeping for {x} Seconds'
                             .format(x=RECONNECTION_INTERVAL))
                    sleep(RECONNECTION_INTERVAL)

                else:
                    LOG.info('Restored connection to {fqdn}'
                             .format(fqdn=host_fqdn))
                    break