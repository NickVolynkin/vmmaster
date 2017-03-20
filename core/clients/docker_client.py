# coding: utf-8
from functools import wraps

import logging

import docker

from core.config import config
from docker import DockerClient as DClient
from docker.models.containers import Container
from core.utils.network_utils import get_free_port

log = logging.getLogger(__name__)


def exception_handler(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except:
            log.exception("Error")
    return wrapper


class DockerContainer:
    def __init__(self, origin):
        """

        :type origin: Container
        """
        self.origin = origin

    @property
    @exception_handler
    def id(self):
        return self.origin.id

    @property
    def name(self):
        return self.origin.name

    @property
    def status(self):
        return self.origin.status

    @property
    def ip(self):
        if config.BIND_LOCALHOST_PORTS:
            return "127.0.0.1"
        else:
            networks = self.origin.attrs["NetworkSettings"]["Networks"]
            return networks.get("vmmaster", {}).get("IPAddress", None)

    @property
    def ports(self):
        _ports = {}
        if config.BIND_LOCALHOST_PORTS:
            for original_port, bind_port in self.origin.attrs["NetworkSettings"]["Ports"].items():
                original_port = int(original_port.replace("/tcp", ""))
                _ports[original_port] = int(bind_port[0]["HostPort"])
        else:
            _ports = {port: port for port in config.PORTS}
        return _ports

    @exception_handler
    def exec_run(self, cmd, *args, **kwargs):
        return self.origin.exec_run(cmd=cmd, detach=True, *args, **kwargs)

    @exception_handler
    def export(self):
        raise NotImplementedError

    @exception_handler
    def get_archive(self):
        raise NotImplementedError

    @exception_handler
    def kill(self, signal=None):
        return self.origin.kill(signal=signal)

    @exception_handler
    def logs(self, **kwargs):
        return self.origin.logs(**kwargs)

    @exception_handler
    def pause(self):
        raise NotImplementedError

    @exception_handler
    def remove(self, **kwargs):
        kwargs["force"] = True
        return self.origin.remove(**kwargs)

    @exception_handler
    def rename(self):
        raise NotImplementedError

    @exception_handler
    def restart(self, **kwargs):
        return self.origin.restart(**kwargs)

    @exception_handler
    def stop(self, **kwargs):
        return self.origin.stop(**kwargs)

    @exception_handler
    def unpause(self):
        raise NotImplementedError


class DockerClient:
    def __init__(self):
        self.client = DClient(
            base_url=config.DOCKER_BASE_URL,
            timeout=config.DOCKER_TIMEOUT,
            num_pools=config.DOCKER_NUM_POOLS
        )

    @exception_handler
    def containers(self, all=None, before=None, filters=None, limit=-1, since=None):
        return [
            DockerContainer(container) for container in self.client.containers.list(
                all=all, before=before, filters=filters, limit=limit, since=since)
        ]

    @exception_handler
    def get_container(self, container_id):
        return DockerContainer(self.client.containers.get(container_id))

    @exception_handler
    def create_container(self, image, command=None):
        cid = self.client.containers.create(image=image, command=command)
        return self.get_container(cid)

    # @exception_handler
    def run_container(self, image, ports=None, *args, **kwargs):
        """

        :type image:
        :type ports:
        :type args:
        :type kwargs:
        :rtype: DockerContainer
        """
        ports = ports if ports else config.PORTS
        if config.BIND_LOCALHOST_PORTS:
            ports = {"%s/tcp" % port: get_free_port() for port in ports}
            kwargs.update({"ports": ports})
        dns = [
            "10.54.18.110",
            "10.54.18.111",
            "10.54.18.184"
        ]
        dns_search = [
            "test",
            "2gis.local"
        ]
        env = {
            "WORKSPACE_DIR": config.BASEDIR
        }
        volumes = {
            config.BASEDIR: {'bind': config.BASEDIR, 'mode': 'rw'}
        }
        kwargs.update({
            "dns": dns,
            "dns_search": dns_search,
            "image": image,
            "privileged": True,
            "environment": env,
            "volumes": volumes,
            "working_dir": config.BASEDIR,
            "detach": True,
            "publish_all_ports": True,
        })
        return DockerContainer(self.client.containers.run(
            *args, **kwargs
        ))

    @exception_handler
    def get_image(self, name):
        from vmpool.platforms import DockerImage
        return DockerImage(self.client.images.get(name=name))

    @exception_handler
    def images(self, name=None, all=None, filters=None):
        from vmpool.platforms import DockerImage
        return [
            DockerImage(image) for image in self.client.images.list(
                name=name, all=all, filters=filters) if len(image.tags)
        ]

    def create_network(self, network_name):
        """

        :rtype: Network
        """
        ipam_pool = docker.types.IPAMPool(
            subnet='192.168.23.0/24',
            gateway='192.168.23.254'
        )
        ipam_config = docker.types.IPAMConfig(
            pool_configs=[ipam_pool]
        )
        return self.client.networks.create(
            network_name,
            check_duplicate=True,
            ipam=ipam_config
        )

    def delete_network(self, network_id):
        try:
            network = self.client.networks.get(network_id)
        except:
            network = None
        if network:
            network.remove()
