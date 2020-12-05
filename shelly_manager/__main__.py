import os
import socket
import time
from dataclasses import dataclass
from typing import List, Optional, TypedDict

import click
import requests
from zeroconf import ServiceBrowser, Zeroconf
from ruamel.yaml import YAML
yaml=YAML(typ='safe')

@click.group()
def cli():
    pass


@dataclass()
class Device:
    class Auth(TypedDict):
        username: str
        password: str

    mac: str
    type: str
    auth: Optional[Auth]
    name: str
    address: str


class DeviceRegistry():
    def __init__(self, config_path: str):
        self._config_path = config_path
        if os.path.exists(self._config_path):
            config = yaml.load(open(self._config_path, 'r'))
        else:
            config = {'devices': []}

        self._devices: List[Device] = config['devices']
        self._devices_by_mac = {d.mac: d for d in self._devices}

    def register_device(self, mac, type, name, address, auth: bool):
        if mac in self._devices_by_mac:
            return

        device = Device(
            mac=mac,
            type=type,
            name=name,
            address=address,
            auth={'username': '', 'password': ''} if auth else None
        )
        self._devices.append(device)
        self._devices_by_mac[mac] = device

        self.flush()

    def flush(self):
        config_f = open(self._config_path, 'w')
        yaml.dump({
            'devices': self._devices
        }, config_f)


class ShellyDiscoveryListener:
    def __init__(self, device_registry: DeviceRegistry):
        self._device_registry = device_registry

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        address = socket.inet_ntoa(info.addresses[0])
        shelly_resp = requests.get('http://{}:{}/shelly'.format(address, info.port))
        if not shelly_resp.ok:
            return

        shelly_info = shelly_resp.json()
        settings_info = {}
        if shelly_info['auth'] is False:
            # Fetch additional info about the device
            settings_info_resp = requests.get('http://{}:{}/settings'.format(address, info.port))
            if settings_info_resp.ok:
                settings_info = settings_info_resp.json()

        name = settings_info.get('name', 'no name')
        print("Found device: {} at {}".format(name, address))

        self._device_registry.register_device(
            mac=shelly_info['mac'],
            type=shelly_info['type'],
            name=settings_info.get('name'),
            address=address,
            auth=shelly_info['auth'],
        )


@cli.command()
@click.option('--devices', type=click.Path(), default='devices.yaml')
def discover(devices):
    device_registry = DeviceRegistry(devices)
    zeroconf = Zeroconf()
    listener = ShellyDiscoveryListener(device_registry)
    ServiceBrowser(zeroconf, "_http._tcp.local.", listener)
    print("Discoverying... ^C to exit")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt as e:
        raise e


if __name__ == '__main__':
    cli()

    # with click.progressbar(all_the_users_to_process) as bar:
    #     for user in bar:
    #         modify_the_user(user)
    #
    # try:
    #     input("Press enter to exit...\n\n")
    # finally:
    #     zeroconf.close()
    #
    # print(devices)

# async def main():
#     options = aioshelly.ConnectionOptions("192.168.2.90")
#
#     async with aiohttp.ClientSession() as aiohttp_session, aioshelly.COAP() as coap_context:
#         try:
#             device = await asyncio.wait_for(
#                 aioshelly.Device.create(aiohttp_session, coap_context, options), 5
#             )
#         except asyncio.TimeoutError:
#             print("Timeout connecting to", ip)
#             return
#
#         for block in device.blocks:
#             print(block)
#             pprint(block.current_values())
#             print()
#
#
# if __name__ == "__main__":
#     asyncio.run(main())


#
# zeroconf = Zeroconf()
# listener = MyListener()
# browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)
#
# try:
#     input("Press enter to exit...\n\n")
# finally:
#     zeroconf.close()
