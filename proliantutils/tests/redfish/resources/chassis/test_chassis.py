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

from proliantutils.redfish.resources.chassis import chassis
from proliantutils.redfish.resources.chassis import devices


class HPEChassisTestCase(testtools.TestCase):

    def setUp(self):
        super(HPEChassisTestCase, self).setUp()
        self.conn = mock.MagicMock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/chassis.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())

        self.chas_inst = chassis.HPEChassis(
            self.conn, '/redfish/v1/Chassis/1',
            redfish_version='1.0.2')

    def test_devices(self):
        self.conn.get.return_value.json.reset_mock()

        with open('proliantutils/tests/redfish/'
                  'json_samples/devices_collection.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        actual_devices = self.chas_inst.devices

        self.assertIsInstance(actual_devices,
                              devices.DevicesCollection)
        self.conn.get.return_value.json.assert_called_once_with()

        # reset mock
        self.conn.get.return_value.json.reset_mock()

        self.assertIs(actual_devices,
                      self.chas_inst.devices)
        self.conn.get.return_value.json.assert_not_called()
