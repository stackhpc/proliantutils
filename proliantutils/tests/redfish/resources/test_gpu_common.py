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

import ddt
import mock
import sushy
import testtools

from proliantutils import exception
from proliantutils.redfish.resources import gpu_common


@ddt.ddt
class GPUCommonMethodsTestCase(testtools.TestCase):

    def setUp(self):
        super(GPUCommonMethodsTestCase, self).setUp()
        self.system_obj = mock.MagicMock()
        self.chassis_obj = mock.MagicMock()

    def _mock_property(self, value):
        if value is sushy.exceptions.SushyError:
            mock_value = mock.PropertyMock(side_effect=value)
        else:
            mock_value = mock.PropertyMock(return_value=value)
        return mock_value

    @ddt.data((["/redfish/v1/Systems/1/PCIDevices/2"], {'1': 'NULL'},
               {'1': ["/redfish/v1/Systems/1/PCIDevices/2"]},
               {'1': "Embedded Video Controller"}, {'2': 4139},
               [{'gpu_vendor_count': {'gpu_0x102b_count': 1}},
                {'gpu_ven_dev_count':
                    {'gpu_Embedded_Video_Controller_count': 1}},
                {'gpu_ven_dev': {'gpu_Embedded_Video_Controller': True}}]),
              (["/redfish/v1/Systems/1/PCIDevices/2"], {'1': 'Nvidia'},
               {'1': ["/redfish/v1/Systems/1/PCIDevices/2"]},
               {'1': "Nvidia Tesla M10"}, {'2': 4139},
               [{'gpu_vendor_count': {'gpu_Nvidia_count': 1}},
                {'gpu_ven_dev_count':
                    {'gpu_Nvidia_Tesla_M10_count': 1}},
                {'gpu_ven_dev': {'gpu_Nvidia_Tesla_M10': True}}]))
    @ddt.unpack
    def test_gpu_capabilities(self, gpu_uris_list, ch_vendor_dict,
                              pci_uris, device_names, pci_vendor_id,
                              expected):
        system_obj = self.system_obj
        chassis_obj = self.chassis_obj
        type(system_obj.pci_devices).gpu_devices = (
            self._mock_property(gpu_uris_list))
        type(chassis_obj.devices).vendor_dict = (
            self._mock_property(ch_vendor_dict))
        type(chassis_obj.devices).pci_devices_uris = (
            self._mock_property(pci_uris))
        type(chassis_obj.devices).vendor_devices_dict = (
            self._mock_property(device_names))
        type(system_obj.pci_devices).vendor_id = (
            self._mock_property(pci_vendor_id))
        actual = gpu_common.gpu_capabilities(system_obj, chassis_obj)
        self.assertEqual(expected, actual)

    def test__get_attribute_value_of(self):
        system_obj = self.system_obj
        gpu_mock = mock.PropertyMock(
            return_value=['/redfish/v1/Systems/1/PCIDevices/6'])
        type(system_obj.pci_devices).gpu_devices = gpu_mock
        actual = gpu_common._get_attribute_value_of(system_obj.pci_devices,
                                                    'gpu_devices')
        self.assertEqual(['/redfish/v1/Systems/1/PCIDevices/6'], actual)

    def test__get_attribute_value_of_sushy_error(self):
        system_obj = self.system_obj
        gpu_mock = mock.PropertyMock(side_effect=sushy.exceptions.SushyError)
        type(system_obj.pci_devices).gpu_devices = gpu_mock
        actual = gpu_common._get_attribute_value_of(system_obj.pci_devices,
                                                    'gpu_devices', default=[])
        self.assertEqual([], actual)

    def test__get_attribute_value_of_fail_missing_attribute(self):
        system_obj = self.system_obj
        gpu_mock = mock.PropertyMock(
            side_effect=exception.MissingAttributeError)
        type(system_obj.pci_devices).gpu_devices = gpu_mock
        actual = gpu_common._get_attribute_value_of(system_obj.pci_devices,
                                                    'gpu_devices')
        self.assertIsNone(actual)
