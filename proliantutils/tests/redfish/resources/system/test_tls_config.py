# Copyright 2017 Hewlett Packard Enterprise Development LP
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

from proliantutils.redfish.resources.system import tls_config


class TLSConfigTestCase(testtools.TestCase):

    def setUp(self):
        super(TLSConfigTestCase, self).setUp()
        self.conn = mock.MagicMock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/tls_config.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read()))

        self.tls_config_inst = tls_config.TLSConfig(
            self.conn, '/redfish/v1/Systems/1/bios/tlsconfig',
            redfish_version='1.0.2')

    def test_tls_config_settings(self):
        self.conn.get.return_value.json.reset_mock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/tls_config_settings.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read()))
        actual_settings = self.tls_config_inst.tls_config_settings
        self.assertIsInstance(actual_settings,
                              tls_config.TLSConfigSettings)
        self.conn.get.return_value.json.assert_called_once_with()
        # reset mock
        self.conn.get.return_value.json.reset_mock()
        self.assertIs(actual_settings,
                      self.tls_config_inst.tls_config_settings)
        self.conn.get.return_value.json.assert_not_called()

    def test_iscsi_settings_on_refresh(self):
        with open('proliantutils/tests/redfish/'
                  'json_samples/tls_config_settings.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read()))
        actual_settings = self.tls_config_inst.tls_config_settings
        self.assertIsInstance(actual_settings,
                              tls_config.TLSConfigSettings)

        with open('proliantutils/tests/redfish/'
                  'json_samples/tls_config.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read()))

        self.tls_config_inst.invalidate()
        self.tls_config_inst.refresh(force=False)

        self.assertTrue(actual_settings._is_stale)

        with open('proliantutils/tests/redfish/'
                  'json_samples/tls_config_settings.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read()))
        self.assertIsInstance(self.tls_config_inst.tls_config_settings,
                              tls_config.TLSConfigSettings)
        self.assertFalse(actual_settings._is_stale)


class TLSConfigSettingsTestCase(testtools.TestCase):

    def setUp(self):
        super(TLSConfigSettingsTestCase, self).setUp()
        self.conn = mock.MagicMock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/tls_config_settings.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read()))

        self.tls_config_settings_inst = tls_config.TLSConfigSettings(
            self.conn, '/redfish/v1/Systems/1/bios/tlsconfig/settings',
            redfish_version='1.0.2')

    def test_add_tls_certificate(self):
        target_uri = '/redfish/v1/Systems/1/bios/tlsconfig/settings'
        cert_data = {
            "NewCertificates": [
                {
                    "X509Certificate": "abc"
                }
            ]
        }
        self.tls_config_settings_inst.add_tls_certificate(cert_data)
        self.tls_config_settings_inst._conn.put.assert_called_once_with(
            target_uri, data=cert_data)

    def test_remove_tls_certificate(self):
        target_uri = '/redfish/v1/Systems/1/bios/tlsconfig/settings'
        fp = ('FA:3A:68:C7:7E:ED:90:21:D2:FA:3E:54:6B:0C:14:D3:'
              '2F:8D:43:50:F7:05:A7:0F:1C:68:35:DB:5C:D2:53:28')
        cert = {}
        del_cert_list = [{"FingerPrint": fp}]
        cert.update({"DeleteCertificates": del_cert_list})

        self.tls_config_settings_inst.remove_tls_certificate(cert)
        self.tls_config_settings_inst._conn.put.assert_called_once_with(
            target_uri, data=cert)
