# Copyright 2017 Hewlett Packard Enterprise Development LP
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sushy
from sushy.resources import base
from sushy.resources.system import ethernet_interface
from sushy import utils as sushy_utils


class EthernetInterface(ethernet_interface.EthernetInterface):

    uefi_device_path = base.Field('UefiDevicePath')


class EthernetInterfaceCollection(base.ResourceCollectionBase):

    @property
    def _resource_type(self):
        return EthernetInterface

    @property
    @sushy_utils.cache_it
    def summary(self):
        """property to return the summary MAC addresses and state

        This filters the MACs whose health is OK,
        and in 'Enabled' State would be returned.
        The returned format will be {<port_id>: <mac_address>}.
        This is because RIBCL returns the data in format
        {'Port 1': 'aa:bb:cc:dd:ee:ff'} and ironic ilo drivers inspection
        consumes the data in this format.
        Note: 'Id' is referred to as "Port number".
        """
        mac_dict = {}
        for eth in self.get_members():
            if eth.mac_address is not None:
                if (eth.status is not None
                        and eth.status.health == sushy.HEALTH_OK
                        and eth.status.state == sushy.STATE_ENABLED):
                    mac_dict.update(
                        {'Port ' + eth.identity: eth.mac_address})
        return mac_dict

    def get_uefi_device_path_by_mac(self, mac):
        """Return uefi device path of mac"""
        for nic in self.get_members():
            if nic.mac_address.lower() == mac.lower():
                return nic.uefi_device_path

    def get_all_macs(self):
        """Return list of macs available on system"""
        macs = [mac.mac_address.lower() for mac in self.get_members()]
        return macs
