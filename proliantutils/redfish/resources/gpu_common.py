# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

__author__ = 'HPE'

import os

import sushy

from proliantutils import exception
from proliantutils import log

LOG = log.get_logger(__name__)


def _get_attribute_value_of(resource, attribute_name, default=None):
    """Gets the value of attribute_name from the resource

    It catches the exception, if any, while retrieving the
    value of attribute_name from resource and returns default.

    :param resource: The resource object
    :attribute_name: Property of the resource
    :returns the property value if no error encountered
        else return 0.
    """
    try:
        return getattr(resource, attribute_name)
    except (sushy.exceptions.SushyError,
            exception.MissingAttributeError) as e:
        msg = (('The Redfish controller failed to get the '
                'attribute %(attribute)s from resource %(resource)s. '
                'Error %(error)s') % {'error': str(e),
                                      'attribute': attribute_name,
                                      'resource':
                                      resource.__class__.__name__})
        LOG.debug(msg)
        return default


def gpu_capabilities(system_obj, chassis_obj):
    """Gets the additional gpu capablities

    The PCIDevice URIs /redfish/v1/Systems/1/PCIDevices/<id>
    has the details for the device if it falls in GPU devices
    classification.
    The Devices URIs /redfish/v1/Chassis/1/Devices/<id>
    has the vendor name, vendor device names and the
    device_instances which has the list of PCIDevice URIs for the
    particular Device ID.
    The logic implemented is:
    1. Get the Chassis Devices URIs data
    2. Check if the PCIDevices given in 'device_instances' corresponds
       to GPU device classification i.e. they are there in the list
       returned by 'gpu_devices'.
    3. If the given Chassis Devices URI is for GPU device,
       then create the capability variables with following:
       gpu_<vendor_name>_count - Numeric
       gpu_<vendor_device_name>_count - Numeric
       gpu_<vendor_device_name> - True/False
    :param system_obj: An instance of sushy system
    :param chassis_obj: An instance of sushy chassis
    :returns list of additional gpu_capabilities.
    """

    gpu_cap = [{'gpu_vendor_count': {}},
               {'gpu_ven_dev_count': {}},
               {'gpu_ven_dev': {}}]

    # Get the list of PCIDevice URIs which are GPU devices
    pci_devices = _get_attribute_value_of(system_obj, 'pci_devices')
    gpu_device_list = _get_attribute_value_of(pci_devices, 'gpu_devices')

    devices = _get_attribute_value_of(chassis_obj, 'devices')

    # Get the dictionary of {<id1>: <vendor_name>, <id2>: <vendor_name>, ...}
    # from Chassis Devices URIs.
    vendor_dict = _get_attribute_value_of(devices, 'vendor_dict')

    # Get the dictionary of
    #        {<id1>: [<pci_uri1>, ...],
    #         <id2>: [<pci_uri2>, ...]}
    # from Chassis Devices URIs.
    pci_devices_uris = _get_attribute_value_of(devices,
                                               'pci_devices_uris')

    # Get the dictionary of {<id1>: <device_name>, ...} from
    # Chassis Devices URIs.
    vendor_devices_dict = _get_attribute_value_of(devices,
                                                  'vendor_devices_dict')

    # Get the dictionary of {<pci_id1>: <vendor_id>, ...} from the
    # PCI Device URIs but only for those devices which are GPU devices.
    vendor_id_dict = _get_attribute_value_of(pci_devices, 'vendor_id')

    for identity in pci_devices_uris:
        devices_list = pci_devices_uris[identity]
        for member in devices_list:
            if member in gpu_device_list:
                vendor_name = vendor_dict[identity]
                count_ven_var = 'gpu_' + vendor_name + '_count'
                # Sometimes there is no vendor name in the redfish output.
                # Hence creating the variable with the numeric vendor
                # ID for those gpu devices
                if vendor_name == 'NULL':
                    pci_uri_id = os.path.basename(member)
                    vendor_name = hex(vendor_id_dict[pci_uri_id])
                    count_ven_var = 'gpu_' + vendor_name + '_count'

                gpu_device_name = vendor_devices_dict[identity]
                # The data returned is like "Embedded Video Controller"
                # Replacing space with underscore to form the correct
                # capability name.
                gpu_dev_name = gpu_device_name.replace(" ", "_")
                count_ven_dev_var = 'gpu_' + gpu_dev_name + '_count'
                ven_dev_var = 'gpu_' + gpu_dev_name

                if count_ven_var not in gpu_cap[0]['gpu_vendor_count']:
                    gpu_cap[0]['gpu_vendor_count'].update({count_ven_var: 1})
                else:
                    gpu_ven_count = (
                        gpu_cap[0]['gpu_vendor_count'].get(count_ven_var))
                    gpu_cap[0]['gpu_vendor_count'].update(
                        {count_ven_var: gpu_ven_count + 1})

                if count_ven_dev_var not in gpu_cap[1]['gpu_ven_dev_count']:
                    gpu_cap[1]['gpu_ven_dev_count'].update(
                        {count_ven_dev_var: 1})
                    gpu_cap[2]['gpu_ven_dev'].update({ven_dev_var: True})
                else:
                    dev_count = (
                        gpu_cap[1]['gpu_ven_dev_count'].get(
                            count_ven_dev_var))
                    gpu_cap[1]['gpu_ven_dev_count'].update(
                        {count_ven_dev_var: dev_count + 1})
    return gpu_cap
