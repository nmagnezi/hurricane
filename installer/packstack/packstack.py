import logging
import os
from ConfigParser import ConfigParser

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

INSTALLER_CONFIG_FILE_DEFAULT_PATH = '/root'
INSTALLER_CONFIG_FILE_DIRCTORY = 'hurricane/installer/packstack'
INSTALLER_CONFIG_FILE_SECTION = 'general'
JOB_CONFIG_FILE_SECTION = 'job_params'
ENVIRONMENT_CONFIG_FILE_SECTION = 'environment'


class Packstack(object):

    def __init__(self, job_dict):
        self.packstack_answer_file_name = \
            job_dict[JOB_CONFIG_FILE_SECTION]['installer_conf_file']
        self.installer_conf_file_tags = \
            job_dict[JOB_CONFIG_FILE_SECTION]['installer_conf_file_tags']
        self.ext_vlan = job_dict[JOB_CONFIG_FILE_SECTION]['ext_vlan']
        self.ntp_server = \
            job_dict[ENVIRONMENT_CONFIG_FILE_SECTION]['default_ntp']
        self.answer_file_dict = self.build_dict_from_file(
            os.path.join(INSTALLER_CONFIG_FILE_DIRCTORY,
                         self.packstack_answer_file_name) + '.ini')

    def debug_print(self):
        """to be deleted"""
        LOG.info(self.packstack_answer_file_name)
        LOG.info(self.installer_conf_file_tags)
        LOG.info(os.path.join(INSTALLER_CONFIG_FILE_DIRCTORY,
                         self.packstack_answer_file_name) + '.ini')
        LOG.info(self.answer_file_dict)

    def build_dict_from_file(self, conf):
        # TODO: add check that file exists - conf
        config_file = ConfigParser()
        config_file.read(conf)
        file_dict = {}
        for section in config_file.sections():
            file_dict[section] = {}
            for option in config_file.options(section):
                file_dict[section][option] = config_file.get(section, option)
        return file_dict

    def generate_answer_file(self, host):
        cmd = 'packstack --gen-answer-file={answer_file_name}'\
              .format(answer_file_name=self.packstack_answer_file_name)

        host.run_bash_command(cmd)

        LOG.info('Generating packstack answer file {answer_file_name} '
                 'on host {host}'
                 .format(answer_file_name=self.packstack_answer_file_name,
                         host=host.fqdn))

    def get_tagged_value(self, attribute):
        a = attribute.lower()
        tagged_value = self.answer_file_dict[INSTALLER_CONFIG_FILE_SECTION][a]
        return tagged_value[1:-1]

    def set_tagged_value(self, host, tag_name, tag_value):
        cmd = 'sed -i s/"<{tag_name}>"/"{tag_value}"/g ' \
                       '/root/{answer_file_name}'\
            .format(tag_name=tag_name,
                    tag_value=tag_value,
                    answer_file_name=self.packstack_answer_file_name)
        host.run_bash_command(cmd)

    def configure_answer_file(self, controller, openstack_hosts):
        LOG.info('Configuring packstack answer file {answer_file_name} '
                 'on host {host}'
                 .format(answer_file_name=self.packstack_answer_file_name,
                         host=controller.fqdn))

        # inject template values to answer file
        for option in \
                self.answer_file_dict[INSTALLER_CONFIG_FILE_SECTION]\
                    .keys():

            cmd = 'sed -i s/^{option}=.*/{option}="{value}"/g ' \
                  '{packstack_answer_file_name}'\
                  .format(option=option.upper(),
                          value=self.answer_file_dict
                          [INSTALLER_CONFIG_FILE_SECTION][option],
                          packstack_answer_file_name=
                          os.path.join(INSTALLER_CONFIG_FILE_DEFAULT_PATH,
                                       self.packstack_answer_file_name))

            controller.run_bash_command(cmd)

        # build hosts ip addresses dict by role
        tags_to_inject = {}
        for host in openstack_hosts:
            if not host.role in tags_to_inject:
                tags_to_inject[host.role] = []
            tags_to_inject[host.role].append(host.ip_address)

        # add tagged values to dict
        if self.installer_conf_file_tags:
            for tag in self.installer_conf_file_tags.split(", "):
                split_tag = tag.split('/')
                tag_name = split_tag[0]
                tag_value = split_tag[1]
                if not tag_name in tags_to_inject:
                    tags_to_inject[tag_name] = []
                tags_to_inject[tag_name].append(tag_value)

        tags_to_inject['tenant_int'] = []
        tags_to_inject['tenant_int'].append(controller.tenant_interface)

        tags_to_inject['ntp_server'] = []
        tags_to_inject['ntp_server'].append(self.ntp_server)

        if not self.ext_vlan == '':
            tags_to_inject['ext_vlan'] = []
            tags_to_inject['ext_vlan'].append(self.ext_vlan)

        LOG.info('Values to be configured in answer file: {tags}'
                 .format(tags=tags_to_inject))

        # inject tagged values to answer file
        for tag in tags_to_inject.keys():
            self.set_tagged_value(controller, tag,
                                  ", ".join(tags_to_inject[tag]))

    def install_openstack(self, host):
        LOG.info('running packstack on {host}. '
                 'Grab yourself a cup of coffee it will take ~20 minutes'
                 .format(host=host.fqdn))

        cmd = 'packstack --answer-file=/root/{packstack_answer_file_name}'\
              .format(packstack_answer_file_name=
                      self.packstack_answer_file_name)

        host.run_bash_command(cmd)
