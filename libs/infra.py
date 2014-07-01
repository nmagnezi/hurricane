import paramiko
from socket import timeout
from paramiko.ssh_exception import SSHException
from time import sleep
from socket import timeout
import json
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

CREDENTIALS_SECTION = 'credentials'
ENVIRONMENT_SECTION = 'environment'
JOB_CONFIG_FILE_SECTION = 'job_params'
FOREMAN_PARAMS_SECTION = 'foreman_params'

class Provisioning(object):

    def __init__(self, job_dict):
        self.foreman_user = job_dict[CREDENTIALS_SECTION]['foreman_user']
        self.foreman_pass = job_dict[CREDENTIALS_SECTION]['foreman_pass']
        self.test_server_user = job_dict[CREDENTIALS_SECTION]['default_user']
        self.test_server_pass = job_dict[CREDENTIALS_SECTION]['default_pass']
        self.foreman_url = job_dict[ENVIRONMENT_SECTION]['foreman_url']
        self.test_server = job_dict[ENVIRONMENT_SECTION]['test_server']
        self.operating_system = \
            job_dict[JOB_CONFIG_FILE_SECTION]['operating_system']
        self.foreman_params_list = \
            (job_dict[FOREMAN_PARAMS_SECTION][self.operating_system.lower()])\
            .split()
        self.ssh = paramiko.SSHClient()

    def connect_to_test_server(self):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=self.test_server,
                         username=self.test_server_user,
                         password=self.test_server_pass)

        LOG.info('Connected to {test_server}'
                 .format(test_server=self.test_server))


    def disconnect_from_test_server(self):
        self.ssh.close()

    def provision_hosts(self, hosts_list):
        self.connect_to_test_server()
        self.change_os_and_medium(hosts_list)
        self.set_build_in_foreman(hosts_list)
        # self.reboot_hosts(hosts_list)
        # self.wait_for_reprovision_to_finish(hosts_list)
        self.disconnect_from_test_server()

    def set_build_in_foreman(self, hosts_list):
        for host in hosts_list:
            bash_cmd = 'curl -s -H "Accept:application/json" -k -u ' \
                       '{foreman_user}:{foreman_pass} ' \
                       '{foreman_url}/api/hosts/{machine_fqdn} -X PUT -d ' \
                       '"host[build]=1" -o -'.\
                format(foreman_user=self.foreman_user,
                       foreman_pass=self.foreman_pass,
                       foreman_url=self.foreman_url, machine_fqdn=host.fqdn)
            self.ssh.exec_command(bash_cmd)
        self.disconnect_from_test_server()

    def change_os_and_medium(self, hosts_list):
        os_name = self.foreman_params_list[0]
        os_major = self.foreman_params_list[1]
        os_minor = self.foreman_params_list[2]
        medium = self.foreman_params_list[3]
        ptable = ' '.join(self.foreman_params_list[4:])
        for host in hosts_list:
            bash_cmd = 'curl -s -H "Accept:application/json" -k -u ' \
                       '{foreman_user}:{foreman_pass} ' \
                       '{foreman_url}/api/operatingsystems -X GET -o -'\
                .format(foreman_user=self.foreman_user,
                        foreman_pass=self.foreman_pass,
                        foreman_url=self.foreman_url)
            ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(bash_cmd)
            os_json = ssh_stdout.read()
            os_id = self.get_foreman_os_id_by_json(os_json, os_name, os_major,
                                                   os_minor)
            medium_id = self.get_foreman_medium_id_by_json(os_json, os_name,
            os_major, os_minor, medium)
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
                        host=host.fqdn,
                        os_id=os_id,
                        medium_id=medium_id,
                        ptables_id=ptables_id)
            self.ssh.exec_command(bash_cmd)
            LOG.info('Foreman: Changed host {host} OS to {os}'
                     .format(os=self.operating_system, host=host))

    def reboot_hosts(self, hosts_list):
        for host in hosts_list:
            host.reboot()

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

    def wait_for_reprovision_to_finish(self, hosts_list):
        # TODO: a thread to monitor each host provisioning till timeout/success.
        num_of_retries = 1200
        interval = 2
        for host in hosts_list:
            LOG.info('Waiting for reprovision of: {fqdn}'
                     .format(fqdn=host.fqdn))
            for i in xrange(num_of_retries):

                LOG.info('Attempting to open SSH connection to {fqdn}, '
                         'Attempt {i} out of {num_of_retries}'
                         .format(fqdn=host.fqdn, i=i,
                                 num_of_retries=num_of_retries))
                try:
                    host.open_connection()

                except Exception as e:
                    LOG.info('Failed to connect to {fqdn} with exeption: '
                             '{exception}'.format(fqdn=host.fqdn, exception=e))
                    LOG.info('')
                    LOG.info('Sleeping for {x} Seconds'.format(x=interval))
                    sleep(interval)

                else:
                    LOG.info('Restored connection to {fqdn}'
                             .format(fqdn=host.fqdn))
                    break