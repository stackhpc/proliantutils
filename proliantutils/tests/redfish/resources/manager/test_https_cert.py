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
"""Test Class for HttpsCertTestCase"""

import json
from unittest import mock

import sushy
import testtools

from proliantutils import exception
from proliantutils.redfish.resources.manager import https_cert


class HttpsCertTestCase(testtools.TestCase):

    def setUp(self):
        super(HttpsCertTestCase, self).setUp()
        self.conn = mock.Mock()
        https_cert_file = ('proliantutils/tests/redfish/json_samples/'
                           'https_cert.json')
        with open(https_cert_file) as f:
            self.json_doc = json.load(f)
            self.conn.get.return_value.json.return_value = (
                self.json_doc)

        path = ("/redfish/v1/Mangers/1/SecurityService/HttpsCert")
        self.https_cert_inst = https_cert.HttpsCert(
            self.conn, path, '1.0.2', None)

    def test__get_https_cert_uri_generate_csr(self):
        value = self.https_cert_inst._get_https_cert_uri('generate_csr')
        expected_url = ('/redfish/v1/Managers/1/SecurityService/HttpsCert/'
                        'Actions/HpeHttpsCert.GenerateCSR')
        self.assertEqual(expected_url, value.target_uri)

    def test__get_https_cert_uri_import_certificate(self):
        value = self.https_cert_inst._get_https_cert_uri('import_cert')
        expected_url = ('/redfish/v1/Managers/1/SecurityService/HttpsCert/'
                        'Actions/HpeHttpsCert.ImportCertificate')
        self.assertEqual(expected_url, value.target_uri)

    def test__get_https_cert_uri_missing_url(self):
        self.https_cert_inst._actions.generate_csr = None
        self.assertRaisesRegex(
            sushy.exceptions.MissingActionError,
            'action #HpeHttpsCert.GenerateCSR',
            self.https_cert_inst._get_https_cert_uri, 'generate_csr')

    @mock.patch.object(https_cert.HttpsCert, 'wait_for_csr_to_create',
                       autospec=True)
    def test_generate_csr(self, wait_for_csr_to_create_mock):
        target_uri = ('/redfish/v1/Managers/1/SecurityService/HttpsCert/'
                      'Actions/HpeHttpsCert.GenerateCSR')
        data = {
            "CommonName": '1.1.1.1',
            "Country": 'IN',
            "State": 'KA',
            "City": 'blr',
            "OrgName": 'HPE',
            "OrgUnit": None
        }
        self.https_cert_inst.generate_csr(data)
        self.https_cert_inst._conn.post.assert_called_once_with(
            target_uri, data=data)
        self.assertTrue(wait_for_csr_to_create_mock.called)

    def test_generate_csr_post_fails(self):
        data = {
            "CommonName": '1.1.1.1',
            "Country": 'IN',
            "State": 'KA',
            "City": 'blr',
            "OrgName": 'HPE',
            "OrgUnit": None
        }
        self.https_cert_inst._conn.post.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to generate CSR',
            self.https_cert_inst.generate_csr, data)

    def test_import_certificate(self):
        target_uri = ('/redfish/v1/Managers/1/SecurityService/HttpsCert/'
                      'Actions/HpeHttpsCert.ImportCertificate')
        data = {
            "Certificate": 'certificate'
        }
        self.https_cert_inst.import_certificate('certificate')
        self.https_cert_inst._conn.post.assert_called_once_with(
            target_uri, data=data)

    def test_import_certificate_post_fails(self):
        self.https_cert_inst._conn.post.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to import certificate. Error',
            self.https_cert_inst.import_certificate, 'certificate')

    @mock.patch('time.sleep', autospec=True)
    @mock.patch.object(https_cert.HttpsCert, 'get_generate_csr_refresh',
                       autospec=True)
    def test_wait_for_csr_to_create_ok(self, get_generate_csr_refresh_mock,
                                       sleep_mock):
        self.cert_sign_request = 'certificate'
        self.https_cert_inst.wait_for_csr_to_create()
        self.assertTrue(get_generate_csr_refresh_mock.called)

    @mock.patch('time.sleep', autospec=True)
    @mock.patch.object(https_cert.HttpsCert, 'get_generate_csr_refresh',
                       autospec=True)
    def test_wait_for_csr_to_create_fails(self, get_generate_csr_refresh_mock,
                                          sleep_mock):
        exc = exception.IloError('error')
        get_generate_csr_refresh_mock.side_effect = exc
        self.assertRaises(exception.IloError,
                          self.https_cert_inst.wait_for_csr_to_create)
        self.assertEqual(10, get_generate_csr_refresh_mock.call_count)
