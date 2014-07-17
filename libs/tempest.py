import logging
import os
import uuid
import time

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
console = logging.StreamHandler()
LOG.addHandler(console)

TEMPEST_URL = "https://github.com/openstack/tempest.git"
TEMPEST_DIR = "/var/lib/tempest"
PYPI_URL_MIRROR = "http://pypi.gocept.com/simple/"




def provision_tempest(host, branch):
    cmd1 = 'yum -y install git'
    host.run_bash_command(cmd1)
    if "eol" in branch:
        ssh.run_cmd("git clone %s %s" %
                    (TEMPEST_URL, TEMPEST_DIR))
        ssh.run_cmd("cd %s && git checkout %s" %
                    (TEMPEST_DIR, branch))
    else:
        ssh.run_cmd("git clone %s -b %s %s" %
                    (TEMPEST_URL, branch, TEMPEST_DIR))
    ssh.run_cmd("cp %s/etc/tempest.conf.sample %s/etc/tempest.conf" %
                (TEMPEST_DIR, TEMPEST_DIR))




def prepare_tempest_venv(ssh, reqs_file):
    ssh.run_cmd("yum -y install libxslt-devel libxml2-devel gcc python-devel openssl-devel gmp-devel libffi-devel wget")
    ssh.run_cmd("easy_install --index-url %s 'pip<1.5'" % PYPI_URL_MIRROR)
    ssh.run_cmd("pip install --index-url %s virtualenv" % PYPI_URL_MIRROR)
    ssh.run_cmd("virtualenv %s/.venv" % TEMPEST_DIR)
    venv_activate = "%s/.venv/bin/activate" % TEMPEST_DIR
    reqs_file = os.path.join(TEMPEST_DIR, reqs_file)
    ssh.run_cmd("mkdir -p %s/.pip_cache" % TEMPEST_DIR)
    ssh.run_cmd("source %s && "
                "pip install --index-url %s --download-cache %s/.pip_cache nose unittest2 python-ceilometerclient " %
                (venv_activate, PYPI_URL_MIRROR, TEMPEST_DIR))

    def install_pypi_reqs(ssh, venv_activate, reqs_file, PYPI_URL_MIRROR):
        PIP_ATTEMPTS = 20
        SLEEP_BETWEEN_ATTEMPS = 10
        for attempt in range(1, PIP_ATTEMPTS + 1):
            logger.info("### Installing tempest reqs (attempt %s) ###" % attempt)
            try:
                ssh.run_cmd("source %s && "
                            "pip install --index-url %s --download-cache %s/.pip_cache -r %s" %
                            (venv_activate, PYPI_URL_MIRROR, TEMPEST_DIR, reqs_file))
                break
            except RuntimeError:
                logger.warning(
                    "### ... something went wrong when installing reqs, retrying in %s seconds  ###" % SLEEP_BETWEEN_ATTEMPS)
                time.sleep(SLEEP_BETWEEN_ATTEMPS)

        else:
            raise RuntimeError("!!! unable to install reqs after %s attempts" %
                               PIP_ATTEMPTS)

    install_pypi_reqs(ssh, venv_activate, reqs_file, PYPI_URL_MIRROR)


def install_tempest(ssh, openstack_version, branch_name=None):
    tempest_branch = None
    working_directory = os.path.dirname(os.path.realpath(__file__))
    if branch_name is None:
        if openstack_version == "3":
            tempest_branch = "grizzly-eol"
        elif openstack_version == "4":
            tempest_branch = "stable/havana"
        elif openstack_version == "5":
            tempest_branch = "master"
    elif branch_name is not None:
        #in case we set branch name from shell parameters
        tempest_branch = branch_name
    logger.info("### Running  %s  tempest branch ###" % tempest_branch)
    provision_tempest(ssh, tempest_branch)
    prepare_tempest_venv(ssh, "requirements.txt")



def prepare_tempest(ssh, debug_tempest=True):
    image_ref1 = str(uuid.uuid4())
    image_ref2 = str(uuid.uuid4())
    ssh.run_cmd("source ~/keystonerc_admin && "
                "glance image-create --id %s --name %s --disk-format qcow2 --container-format bare --is-public true --copy-from http://download.cirros-cloud.net/0.3.1/cirros-0.3.1-x86_64-disk.img" % (
        image_ref1, "cirros1"))
    ssh.run_cmd("source ~/keystonerc_admin && "
                "glance image-create --id %s --name %s --disk-format qcow2 --container-format bare --is-public true --copy-from http://download.cirros-cloud.net/0.3.1/cirros-0.3.1-x86_64-disk.img" % (
        image_ref2, "cirros2"))
    ssh.run_cmd("source ~/keystonerc_admin && "
                "sleep 60s && "
                "glance image-show %s" % image_ref1)
    ssh.run_cmd("source ~/keystonerc_admin && "
                "sleep 60s && "
                "glance image-show %s" % image_ref2)
    ssh.run_cmd("source ~/keystonerc_admin && "
                "keystone role-create --name ResellerAdmin",
                ignore_exit=True)

    config = {}
    config["file"] = os.path.join(TEMPEST_DIR,
                                  "etc/tempest.conf")
    config["section"] = "identity"
    config["key"] = "uri"
    config["value"] = "http://localhost:35357/v2.0/"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "uri_v3"
    config["value"] = "http://localhost:35357/v3/"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "admin_username"
    config["value"] = "admin"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "admin_tenant_name"
    config["value"] = "admin"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "admin_password"
    config["value"] = "redhat"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "username"
    config["value"] = "demo"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "tenant_name"
    config["value"] = "demo"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "password"
    config["value"] = "redhat"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "alt_username"
    config["value"] = "alt_demo"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "alt_password"
    config["value"] = "redhat"
    run_crudini(ssh, config)
    config["section"] = "identity"
    config["key"] = "alt_tenant_name"
    config["value"] = "alt_demo"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "image_ref"
    config["value"] = image_ref1
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "image_ref_alt"
    config["value"] = image_ref2
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "use_floatingip_for_ssh"
    config["value"] = "false"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "network_for_ssh"
    config["value"] = "novanetwork"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "run_ssh"
    config["value"] = "false"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "ssh_user"
    config["value"] = "cirros"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "image_ssh_user"
    config["value"] = "cirros"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "image_ssh_password"
    config["value"] = "cubswin:)"
    run_crudini(ssh, config)
    config["section"] = "compute-admin"
    config["key"] = "username"
    config["value"] = "admin"
    run_crudini(ssh, config)
    config["section"] = "compute-admin"
    config["key"] = "tenant_name"
    config["value"] = "admin"
    run_crudini(ssh, config)
    config["section"] = "compute-admin"
    config["key"] = "password"
    config["value"] = "redhat"
    run_crudini(ssh, config)
    config["section"] = "object-storage"
    config["key"] = "operator_role"
    config["value"] = "SwiftOperator"
    run_crudini(ssh, config)
    #set timout for compute and volume
    config["section"] = "volume"
    config["key"] = "build_timeout"
    config["value"] = "400"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "build_timeout"
    config["value"] = "400"
    run_crudini(ssh, config)
    config["section"] = "compute"
    config["key"] = "allow_tenant_isolation"
    config["value"] = "true"
    run_crudini(ssh, config)
    #enable debug support in tempest
    if debug_tempest == True:
        config["section"] = "DEFAULT"
        config["key"] = "debug"
        config["value"] = "true"
        run_crudini(ssh, config)
        config["section"] = "DEFAULT"
        config["key"] = "verbose"
        config["value"] = "true"
        run_crudini(ssh, config)


def run_tempest(ssh, test_dirs, skip_test_list=['create_test_server', 'load_tests_apply_scenarios']):
    skip_test_list = '|'.join(skip_test_list)
    skip_test_list = "\"%s\"" % skip_test_list
    xunit_file = os.path.join(TEMPEST_DIR, "nosetests.xml")
    test_dirs = [os.path.join(TEMPEST_DIR, test_dir) for test_dir in test_dirs]
    nose_dirs = ""
    for test_dir in test_dirs:
        nose_dirs = nose_dirs + " %s" % test_dir
    ssh.run_cmd("source %s/.venv/bin/activate && "
                "export TEMPEST_PY26_NOSE_COMPAT=1 && "
                "nosetests -v -e %s --nologcapture --with-id --with-xunit --xunit-file=%s %s" % (
        TEMPEST_DIR, skip_test_list, xunit_file, nose_dirs),
                ignore_exit=True)