# coding: utf-8

import logging
import libvirt
from uuid import uuid4
from docker.models.networks import Network as DNetwork

from core.network.network_xml import NetworkXml
from core.network.mac_ip_table import MacIpTable
from core.connection import Virsh
from core.clients.docker_client import DockerClient, exception_handler

log = logging.getLogger(__name__)


class Network(MacIpTable):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Network, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            super(Network, self).__init__()

            self.name = "session_network"
            self.uuid = uuid4()
            self.bridge_name = "virbr2"
            self.dumpxml_file = NetworkXml(
                self.name, self.uuid, self.bridge_name, self.free_table
            ).xml.toprettyxml()
            self.conn = Virsh()
            try:
                self.conn.networkDefineXML(self.dumpxml_file)
            except libvirt.libvirtError:
                self.clear_previous_network_session()
                self.conn.networkDefineXML(self.dumpxml_file)

            net = self.conn.networkLookupByName(self.name)
            net.create()
            self.initialized = True
        else:
            pass

    def clear_previous_network_session(self):
        net = self.conn.networkLookupByName(self.name)
        try:
            net.destroy()
        except libvirt.libvirtError:
            pass
        try:
            net.undefine()
        except libvirt.libvirtError:
            pass

    def delete(self):
        log.info("deleting network: {}".format(self.name))
        net = self.conn.networkLookupByName(self.name)
        net.destroy()
        net.undefine()
        del self


class DockerNetwork:
    def __init__(self):
        self.name = "vmmaster"
        self.network = None
        self.client = DockerClient()
        self.network = self.create()

    def create(self):
        """

        :rtype: DNetwork
        """
        self.delete(self.name)
        return self.client.create_network(self.name)

    def delete(self, name=None):
        nid = name if name else self.network.id
        self.client.delete_network(nid)

    def connect_container(self, container_id):
        self.network.connect(container_id)

    def disconnect_container(self, container_id):
        self.network.disconnect(container_id)
