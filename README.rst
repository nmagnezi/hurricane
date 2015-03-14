=========
Hurricane
=========

What is Hurricane
=================

Hurricane provisions and deploys OpenStack cloud on given servers.

This project is meant for setting up OpenStack cloud in various topologies and configurations.


Components
----------

1. **Provisioner** - done via theforeman. both baremetal and virtual machines are supported, as long as they are registered to theforeman.
2. **Installer** - done via packstack on servers that are presented by **Provisioner**
3. **Tests** - This is still a work in progress.
