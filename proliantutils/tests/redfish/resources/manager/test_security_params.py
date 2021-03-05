# Copyright 2020 Hewlett Packard Enterprise Development LP
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
"""Test Class for SecurityParamsTestCase"""

import json

import mock
import testtools

from proliantutils.redfish.resources.manager import security_params


class SecurityParamsTestCase(testtools.TestCase):

    def setUp(self):
        super(SecurityParamsTestCase, self).setUp()
        self.conn = mock.Mock()
        security_param_file = ('proliantutils/tests/redfish/json_samples/'
                               'security_param.json')
        with open(security_param_file) as f:
            self.json_doc = json.load(f)
            self.conn.get.return_value.json.return_value = (
                self.json_doc)

        path = ("/redfish/v1/Mangers/1/SecurityService/"
                "SecurityDashboard/SecurityParams")
        self.sec_param = security_params.SecurityParams(
            self.conn, path, '1.0.2', None)

    def test__parse_attributes(self):
        self.sec_param._parse_attributes(self.json_doc)
        self.assertEqual('1.0.2', self.sec_param.redfish_version)
        self.assertEqual("Security Override Switch", self.sec_param.name)
        self.assertEqual("Ok", self.sec_param.status)
        self.assertEqual("Off", self.sec_param.state)

    def test_update_security_param_ignore_status(self):
        self.sec_param.update_security_param_ignore_status(ignore=False)
        data = {"Ignore": False}
        target_uri = ('/redfish/v1/Mangers/1/SecurityService/'
                      'SecurityDashboard/SecurityParams')
        self.sec_param._conn.patch.assert_called_once_with(
            target_uri, data=data)


class SecurityParamsCollectionTestCase(testtools.TestCase):

    def setUp(self):
        super(SecurityParamsCollectionTestCase, self).setUp()
        self.conn = mock.Mock()
        with open('proliantutils/tests/redfish/json_samples/'
                  'security_params_collection.json', 'r') as f:
            self.json_doc = json.load(f)
            self.conn.get.return_value.json.return_value = self.json_doc
        self.sec_params_col = security_params.SecurityParamsCollection(
            self.conn,
            ('/redfish/v1/Managers/1/SecurityService/'
             'SecurityDashboard/SecurityParams'),
            redfish_version='1.0.2')

    def test__parse_attributes(self):
        self.sec_params_col._parse_attributes(self.json_doc)
        self.assertEqual('1.0.2', self.sec_params_col.redfish_version)
        self.assertEqual('Security Parameter Collection',
                         self.sec_params_col.name)
        path = ('/redfish/v1/Managers/1/SecurityService/'
                'SecurityDashboard/SecurityParams/0',
                '/redfish/v1/Managers/1/SecurityService/'
                'SecurityDashboard/SecurityParams/1')
        self.assertEqual(path, self.sec_params_col.members_identities)

    @mock.patch.object(security_params, 'SecurityParams', autospec=True)
    def test_get_member(self, mock_eth):
        self.sec_params_col.get_member(
            '/redfish/v1/Managers/1/SecurityService/SecurityDashboard/'
            'SecurityParams/1')
        mock_eth.assert_called_once_with(
            self.sec_params_col._conn,
            ('/redfish/v1/Managers/1/SecurityService/SecurityDashboard/'
             'SecurityParams/1'),
            self.sec_params_col.redfish_version, None)

    @mock.patch.object(security_params, 'SecurityParams', autospec=True)
    def test_get_members(self, mock_eth):
        members = self.sec_params_col.get_members()
        path = ('/redfish/v1/Managers/1/SecurityService/SecurityDashboard/'
                'SecurityParams/0')
        path2 = ('/redfish/v1/Managers/1/SecurityService/SecurityDashboard/'
                 'SecurityParams/1')
        calls = [mock.call(self.sec_params_col._conn, path,
                           self.sec_params_col.redfish_version, None),
                 mock.call(self.sec_params_col._conn, path2,
                           self.sec_params_col.redfish_version, None)]
        mock_eth.assert_has_calls(calls)
        self.assertIsInstance(members, list)
        self.assertEqual(2, len(members))
