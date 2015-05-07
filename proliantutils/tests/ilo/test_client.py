# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
"""Test class for Client Module."""

import mock
import testtools

from proliantutils.ilo import client
from proliantutils.ilo import ribcl
from proliantutils.ilo import ris


class IloClientTestCase(testtools.TestCase):

    @mock.patch.object(ribcl.RIBCLOperations, 'get_product_name')
    def setUp(self, product_mock):
        super(IloClientTestCase, self).setUp()
        product_mock.return_value = 'Gen8'
        self.client = client.IloClient("1.2.3.4", "admin", "Admin")

    @mock.patch.object(ribcl.RIBCLOperations, 'get_all_licenses')
    def test__call_method_ribcl(self, license_mock):
        self.client._call_method('get_all_licenses')
        license_mock.assert_called_once_with()

    @mock.patch.object(ris.RISOperations, 'get_host_power_status')
    def test__call_method_ris(self, power_mock):
        self.client.model = 'Gen9'
        self.client._call_method('get_host_power_status')
        power_mock.assert_called_once_with()

    @mock.patch.object(ribcl.RIBCLOperations, 'reset_ilo')
    def test__call_method_gen9_ribcl(self, ilo_mock):
        self.client.model = 'Gen9'
        self.client._call_method('reset_ilo')
        ilo_mock.assert_called_once_with()

    @mock.patch.object(client.IloClient, '_call_method')
    def test_set_http_boot_url(self, call_mock):
        self.client.set_http_boot_url('fake-url')
        call_mock.assert_called_once_with('set_http_boot_url', 'fake-url')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_product_name(self, call_mock):
        self.client.get_product_name()
        call_mock.assert_called_once_with('get_product_name')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_all_licenses(self, call_mock):
        self.client.get_all_licenses()
        call_mock.assert_called_once_with('get_all_licenses')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_power_status(self, call_mock):
        self.client.get_host_power_status()
        call_mock.assert_called_once_with('get_host_power_status')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_http_boot_url(self, call_mock):
        self.client.get_http_boot_url()
        call_mock.assert_called_once_with('get_http_boot_url')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_one_time_boot(self, call_mock):
        self.client.get_one_time_boot()
        call_mock.assert_called_once_with('get_one_time_boot')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_vm_status(self, call_mock):
        self.client.get_vm_status('CDROM')
        call_mock.assert_called_once_with('get_vm_status', 'CDROM')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_press_pwr_btn(self, call_mock):
        self.client.press_pwr_btn()
        call_mock.assert_called_once_with('press_pwr_btn')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_reset_server(self, call_mock):
        self.client.reset_server()
        call_mock.assert_called_once_with('reset_server')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_hold_pwr_btn(self, call_mock):
        self.client.hold_pwr_btn()
        call_mock.assert_called_once_with('hold_pwr_btn')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_set_host_power(self, call_mock):
        self.client.set_host_power('ON')
        call_mock.assert_called_once_with('set_host_power', 'ON')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_set_one_time_boot(self, call_mock):
        self.client.set_one_time_boot('CDROM')
        call_mock.assert_called_once_with('set_one_time_boot', 'CDROM')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_insert_virtual_media(self, call_mock):
        self.client.insert_virtual_media(url='fake-url', device='FLOPPY')
        call_mock.assert_called_once_with('insert_virtual_media', 'fake-url',
                                          'FLOPPY')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_eject_virtual_media(self, call_mock):
        self.client.eject_virtual_media(device='FLOPPY')
        call_mock.assert_called_once_with('eject_virtual_media', 'FLOPPY')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_set_vm_status(self, call_mock):
        self.client.set_vm_status(device='FLOPPY', boot_option='BOOT_ONCE',
                                  write_protect='YES')
        call_mock.assert_called_once_with('set_vm_status', 'FLOPPY',
                                          'BOOT_ONCE', 'YES')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_current_boot_mode(self, call_mock):
        self.client.get_current_boot_mode()
        call_mock.assert_called_once_with('get_current_boot_mode')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_pending_boot_mode(self, call_mock):
        self.client.get_pending_boot_mode()
        call_mock.assert_called_once_with('get_pending_boot_mode')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_set_pending_boot_mode(self, call_mock):
        self.client.set_pending_boot_mode('UEFI')
        call_mock.assert_called_once_with('set_pending_boot_mode', 'UEFI')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_persistent_boot(self, call_mock):
        self.client.get_persistent_boot()
        call_mock.assert_called_once_with('get_persistent_boot')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_persistent_boot_device(self, call_mock):
        self.client.get_persistent_boot_device()
        call_mock.assert_called_once_with('get_persistent_boot_device')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_update_persistent_boot(self, call_mock):
        self.client.update_persistent_boot(['HDD'])
        call_mock.assert_called_once_with('update_persistent_boot', ['HDD'])

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_secure_boot_mode(self, call_mock):
        self.client.get_secure_boot_mode()
        call_mock.assert_called_once_with('get_secure_boot_mode')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_set_secure_boot_mode(self, call_mock):
        self.client.set_secure_boot_mode(True)
        call_mock.assert_called_once_with('set_secure_boot_mode', True)

    @mock.patch.object(client.IloClient, '_call_method')
    def test_reset_secure_boot_keys(self, call_mock):
        self.client.reset_secure_boot_keys()
        call_mock.assert_called_once_with('reset_secure_boot_keys')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_clear_secure_boot_keys(self, call_mock):
        self.client.clear_secure_boot_keys()
        call_mock.assert_called_once_with('clear_secure_boot_keys')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_reset_ilo_credential(self, call_mock):
        self.client.reset_ilo_credential('password')
        call_mock.assert_called_once_with('reset_ilo_credential', 'password')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_reset_ilo(self, call_mock):
        self.client.reset_ilo()
        call_mock.assert_called_once_with('reset_ilo')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_reset_bios_to_default(self, call_mock):
        self.client.reset_bios_to_default()
        call_mock.assert_called_once_with('reset_bios_to_default')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_uuid(self, call_mock):
        self.client.get_host_uuid()
        call_mock.assert_called_once_with('get_host_uuid')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_health_data(self, call_mock):
        self.client.get_host_health_data('fake-data')
        call_mock.assert_called_once_with('get_host_health_data', 'fake-data')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_health_present_power_reading(self, call_mock):
        self.client.get_host_health_present_power_reading('fake-data')
        call_mock.assert_called_once_with(
            'get_host_health_present_power_reading', 'fake-data')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_health_power_supplies(self, call_mock):
        self.client.get_host_health_power_supplies('fake-data')
        call_mock.assert_called_once_with('get_host_health_power_supplies',
                                          'fake-data')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_health_fan_sensors(self, call_mock):
        self.client.get_host_health_fan_sensors('fake-data')
        call_mock.assert_called_once_with('get_host_health_fan_sensors',
                                          'fake-data')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_health_temperature_sensors(self, call_mock):
        self.client.get_host_health_temperature_sensors('fake-data')
        call_mock.assert_called_once_with(
            'get_host_health_temperature_sensors', 'fake-data')

    @mock.patch.object(client.IloClient, '_call_method')
    def test_get_host_health_at_a_glance(self, call_mock):
        self.client.get_host_health_at_a_glance('fake-data')
        call_mock.assert_called_once_with('get_host_health_at_a_glance',
                                          'fake-data')