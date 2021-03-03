# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from sushy.resources import base
from sushy import utils as sushy_utils

LOG = logging.getLogger(__name__)


class Devices(base.ResourceBase):

    identity = base.Field('Id', required=True)

    name = base.Field('Name')

    manufacturer = base.Field('Manufacturer')

    device_instances = base.Field('DeviceInstances')


class DevicesCollection(base.ResourceCollectionBase):

    @property
    def _resource_type(self):
        return Devices

    @property
    @sushy_utils.cache_it
    def vendor_dict(self):
        """Gets the dictionary of identity and vendor names"""
        vendor_dict = {}
        for member in self.get_members():
            vendor = member.manufacturer
            if vendor == '':
                vendor = 'NULL'
            vendor_dict.update({member.identity: vendor})
        return vendor_dict

    @property
    @sushy_utils.cache_it
    def pci_devices_uris(self):
        """Gets the dictionary of pci_device_uris and identity"""
        pci_devices_uris = {}
        for member in self.get_members():
            dev_list = []
            dev_instances = member.device_instances
            if dev_instances is None:
                dev_instances = []
            for m in dev_instances:
                dev_list.append(m.get('@odata.id'))
            pci_devices_uris.update({member.identity: dev_list})
        return pci_devices_uris

    @property
    @sushy_utils.cache_it
    def vendor_devices_dict(self):
        """Gets the dictionary of identity and device names"""
        vendor_devices_dict = {}
        for member in self.get_members():
            vendor_devices_dict.update(
                {member.identity: member.name})
        return vendor_devices_dict
