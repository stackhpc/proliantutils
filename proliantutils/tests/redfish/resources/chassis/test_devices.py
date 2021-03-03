# Copyright 2021 Hewlett Packard Enterprise Development LP
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

import json

import mock
import testtools

from proliantutils.redfish.resources.chassis import devices


class DevicesTestCase(testtools.TestCase):

    def setUp(self):
        super(DevicesTestCase, self).setUp()
        self.conn = mock.Mock()
        dev_file = 'proliantutils/tests/redfish/json_samples/devices.json'
        with open(dev_file, 'r') as f:
            self.json_doc = json.load(f)
        self.conn.get.return_value.json.return_value = self.json_doc

        dev_path = "/redfish/v1/Chassis/1/Devices/9"
        self.dev = devices.Devices(
            self.conn, dev_path, '1.0.2', None)

    def test__parse_attributes(self):
        self.dev._parse_attributes(self.json_doc)
        self.assertEqual('1.0.2', self.dev.redfish_version)
        self.assertEqual('1', self.dev.identity)
        self.assertEqual('Embedded Video Controller', self.dev.name)
        self.assertEqual('', self.dev.manufacturer)


class DevicesCollectionTestCase(testtools.TestCase):

    def setUp(self):
        super(DevicesCollectionTestCase, self).setUp()
        self.conn = mock.Mock()
        with open('proliantutils/tests/redfish/json_samples/'
                  'devices_collection.json') as f:
            self.json_doc = json.load(f)
        self.conn.get.return_value.json.return_value = self.json_doc
        self.dev_col = devices.DevicesCollection(
            self.conn, '/redfish/v1/Chassis/1/Devices',
            redfish_version='1.0.2')

    def test__parse_attributes(self):
        self.dev_col._parse_attributes(self.json_doc)
        self.assertEqual('1.0.2', self.dev_col.redfish_version)
        self.assertEqual('Devices', self.dev_col.name)
        path = ('/redfish/v1/Chassis/1/Devices/9')
        self.assertEqual(path, self.dev_col.members_identities)

    @mock.patch.object(devices, 'Devices', autospec=True)
    def test_get_member(self, mock_dev):
        self.dev_col.get_member(
            '/redfish/v1/Chassis/1/Devices/9')
        mock_dev.assert_called_once_with(
            self.dev_col._conn,
            ('/redfish/v1/Chassis/1/Devices/9'),
            self.dev_col.redfish_version, None)

    @mock.patch.object(devices, 'Devices', autospec=True)
    def test_get_members(self, mock_dev):
        members = self.dev_col.get_members()
        path_list = ["/redfish/v1/Chassis/1/Devices/9"]
        calls = [
            mock.call(self.dev_col._conn, path_list[0],
                      self.dev_col.redfish_version, None)
        ]
        mock_dev.assert_has_calls(calls)
        self.assertIsInstance(members, list)
        self.assertEqual(1, len(members))

    def test_vendor_dict(self):
        self.conn.get.return_value.json.reset_mock()
        val = []
        path = ('proliantutils/tests/redfish/json_samples/'
                'devices.json')
        with open(path, 'r') as f:
            val.append(json.loads(f.read()))
        self.conn.get.return_value.json.side_effect = val
        expected = {'9': 'NULL'}
        actual = self.dev_col.vendor_dict
        self.assertEqual(expected, actual)

    def test_pci_devices_uris(self):
        self.conn.get.return_value.json.reset_mock()
        val = []
        path = ('proliantutils/tests/redfish/json_samples/'
                'devices.json')
        with open(path, 'r') as f:
            val.append(json.loads(f.read()))
        self.conn.get.return_value.json.side_effect = val
        expected = {'9': ["/redfish/v1/Systems/1/PCIDevices/6"]}
        actual = self.dev_col.pci_devices_uris
        self.assertEqual(expected, actual)

    def test_vendor_devices_dict(self):
        self.conn.get.return_value.json.reset_mock()
        val = []
        path = ('proliantutils/tests/redfish/json_samples/'
                'devices.json')
        with open(path, 'r') as f:
            val.append(json.loads(f.read()))
        self.conn.get.return_value.json.side_effect = val
        expected = {'9': 'Embedded Video Controller'}
        actual = self.dev_col.vendor_devices_dict
        self.assertEqual(expected, actual)
