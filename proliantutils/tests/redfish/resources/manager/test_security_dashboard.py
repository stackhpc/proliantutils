# Copyright 2020 Hewlett Packard Enterprise Development LP.
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
"""Test Class for SecurityDashboard."""

import json

import mock
import testtools

from proliantutils.redfish.resources.manager import security_dashboard


class SecurityDashboardTestCase(testtools.TestCase):

    def setUp(self):
        super(SecurityDashboardTestCase, self).setUp()
        self.conn = mock.Mock()
        security_param_file = ('proliantutils/tests/redfish/json_samples/'
                               'security_dashboard.json')
        with open(security_param_file) as f:
            self.json_doc = json.load(f)
            self.conn.get.return_value.json.return_value = (
                self.json_doc)

        path = ("/redfish/v1/Mangers/1/SecurityService/"
                "SecurityDashboard")
        self.sec_dash = security_dashboard.SecurityDashboard(
            self.conn, path, '1.0.2', None)

    def test__parse_attributes(self):
        self.sec_dash._parse_attributes(self.json_doc)
        self.assertEqual('1.0.2', self.sec_dash.redfish_version)
        self.assertEqual("Risk", self.sec_dash.overall_status)
