import logging
import os

from config import consts
from hurricane import utils

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)


class Packstack(object):

    def __init__(self, conf):
        self.packstack_answer_file_name = conf.job_params.installer_conf_file
        self.installer_conf_tags = conf.job_params.installer_conf_file_tags
        self.ext_vlan = conf.job_params.ext_vlan
        self.ntp_server = conf.environment.default_ntp
        self.answer_file = utils.file2bunch(self._get_file_path())

    def _get_file_path(self):
        path = os.path.join(consts.Paths.INSTALLER_CONFIG_FILE_DIRCTORY,
                            self.packstack_answer_file_name)
        file_path = ('{path}{suffix}'
                     .format(path=path, suffix=consts.Names.ANS_FILE_SUFFIX))
        return file_path

    def generate_answer_file(self, host):
        LOG.info('Generating packstack answer file {answer_file_name} on host '
                 '{host}'
                 .format(answer_file_name=self.packstack_answer_file_name,
                         host=host.fqdn))
        host.run_bash_command(
            'packstack --gen-answer-file={answer_file_name}'
            .format(answer_file_name=self.packstack_answer_file_name))

    def get_tagged_value(self, attribute):
        a = attribute.lower()
        tagged_value = self.answer_file.general[a]
        return tagged_value[1:-1]

    def _set_tagged_value(self, host, tag_name, tag_value):
        host.run_bash_command(
            'sed -i s/"<{tag_name}>"/"{tag_value}"/g /root/{answer_file_name}'
            .format(tag_name=tag_name,
                    tag_value=tag_value,
                    answer_file_name=self.packstack_answer_file_name))

    def configure_answer_file(self, controller, networker, openstack_hosts):
        LOG.info('Configuring packstack answer file {answer_file_name} '
                 'on host {host}'
                 .format(answer_file_name=self.packstack_answer_file_name,
                         host=controller.fqdn))

        # Inject template values to answer file
        for option in self.answer_file.general.keys():
            controller.run_bash_command(
                'sed -i s/^{option}=.*/{option}="{value}"/g '
                '{packstack_answer_file_name}'
                .format(option=option.upper(),
                        value=self.answer_file.general[option],
                        packstack_answer_file_name=os.path.
                        join(consts.Paths.INSTALLER_CONFIG_FILE_DEFAULT_PATH,
                             self.packstack_answer_file_name)))

        # Build hosts ip addresses dict by role
        tags_to_inject = {}
        for host in openstack_hosts:
            if host.role not in tags_to_inject:
                tags_to_inject[host.role] = []
            tags_to_inject[host.role].append(host.ip_address)

        # Add tagged values to dict
        if self.installer_conf_tags:
            for tag in self.installer_conf_tags.split(", "):
                split_tag = tag.split('/')
                tag_name = split_tag[0]
                tag_value = split_tag[1]
                if tag_name not in tags_to_inject:
                    tags_to_inject[tag_name] = []
                tags_to_inject[tag_name].append(tag_value)

        tags_to_inject['tenant_int'] = []
        tags_to_inject['tenant_int'].append(networker.tenant_interface)

        tags_to_inject['ntp_server'] = []
        tags_to_inject['ntp_server'].append(self.ntp_server)

        if not self.ext_vlan == '':
            tags_to_inject['ext_vlan'] = []
            tags_to_inject['ext_vlan'].append(self.ext_vlan)

        LOG.info('Values to be configured in answer file: {tags}'
                 .format(tags=tags_to_inject))

        # inject tagged values to answer file
        for tag in tags_to_inject.keys():
            self._set_tagged_value(controller, tag,
                                   ", ".join(tags_to_inject[tag]))

    def install_openstack(self, host):
        host.run_bash_command(
            'grep "CONFIG_" {answer_file_name} | grep -v "#"'
            .format(answer_file_name=self.packstack_answer_file_name))
        LOG.info('running packstack on {host}. Grab yourself a cup of coffee '
                 'it will take ~20 minutes'.format(host=host.fqdn))
        host.run_bash_command(
            'time packstack --answer-file=/root/{answer_file_name} -d'
            .format(answer_file_name=self.packstack_answer_file_name))