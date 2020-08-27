# Copyright 2017 Hewlett Packard Enterprise Development LP
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

from proliantutils.redfish.resources.manager import security_service


class SecurityServiceTestCase(testtools.TestCase):

    def setUp(self):
        super(SecurityServiceTestCase, self).setUp()
        self.conn = mock.Mock()
        security_file = ('proliantutils/tests/redfish/json_samples/'
                         'security_service.json')
        with open(security_file) as f:
            self.json_doc = json.load(f)
            self.conn.get.return_value.json.return_value = (
                self.json_doc)

        path = ("/redfish/v1/Mangers/1/SecurityService/")
        self.sec_serv = security_service.SecurityService(
            self.conn, path, '1.0.2', None)

    def test__parse_attributes(self):
        self.sec_serv._parse_attributes(self.json_doc)
        self.assertEqual('1.0.2', self.sec_serv.redfish_version)
