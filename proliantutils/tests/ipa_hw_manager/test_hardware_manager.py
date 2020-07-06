# Copyright 2015 Hewlett-Packard Development Company, L.P.
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

import mock
from oslo_utils import importutils
import testtools

from proliantutils import exception
from proliantutils.hpssa import manager as hpssa_manager
from proliantutils.ipa_hw_manager import hardware_manager
from proliantutils.sum import sum_controller

ironic_python_agent = importutils.try_import('ironic_python_agent')


class ProliantHardwareManagerTestCase(testtools.TestCase):

    def setUp(self):
        self.hardware_manager = hardware_manager.ProliantHardwareManager()
        self.info = {'ilo_address': '1.2.3.4',
                     'ilo_password': '12345678',
                     'ilo_username': 'admin'}
        clean_step = {
            'interface': 'management',
            'step': 'update_firmware_sum',
            'args': {'url': 'http://1.2.3.4/SPP.iso',
                     'checksum': '1234567890'}}
        self.node = {'driver_info': self.info,
                     'clean_step': clean_step}
        super(ProliantHardwareManagerTestCase, self).setUp()

    def test_get_clean_steps(self):
        self.assertEqual(
            [{'step': 'create_configuration',
              'interface': 'raid',
              'priority': 0,
              'reboot_requested': False},
             {'step': 'delete_configuration',
              'interface': 'raid',
              'priority': 0,
              'reboot_requested': False},
             {'step': 'erase_devices',
              'interface': 'deploy',
              'priority': 0,
              'reboot_requested': False},
             {'step': 'update_firmware_sum',
              'interface': 'management',
              'priority': 0,
              'reboot_requested': False}],
            self.hardware_manager.get_clean_steps("", ""))

    def test_get_deploy_steps(self):
        self.assertEqual(
            [{'step': 'apply_configuration',
              'interface': 'raid',
              'reboot_requested': False,
              'priority': 0,
              'argsinfo': (
                  hardware_manager._RAID_APPLY_CONFIGURATION_ARGSINFO)},
             {'step': 'flash_firmware_sum',
              'interface': 'management',
              'reboot_requested': False,
              'priority': 0,
              'argsinfo': (
                  hardware_manager._FIRMWARE_UPDATE_SUM_ARGSINFO)}],
            self.hardware_manager.get_deploy_steps("", []))

    @mock.patch.object(hpssa_manager, 'create_configuration')
    def test_create_configuration(self, create_mock):
        create_mock.return_value = 'current-config'
        manager = self.hardware_manager
        node = {'target_raid_config': {'foo': 'bar'}}
        ret = manager.create_configuration(node, [])
        create_mock.assert_called_once_with(raid_config={'foo': 'bar'})
        self.assertEqual('current-config', ret)

    @mock.patch.object(hpssa_manager, 'create_configuration')
    def test_create_configuration_no_target_config(self, create_mock):
        create_mock.return_value = 'current-config'
        manager = self.hardware_manager
        node = {'target_raid_config': {}}
        manager.create_configuration(node, [])
        create_mock.assert_not_called()

    @mock.patch.object(hardware_manager.ProliantHardwareManager,
                       'delete_configuration')
    @mock.patch.object(hpssa_manager, 'create_configuration')
    def test_apply_configuration_with_delete(self, create_mock, delete_mock):
        create_mock.return_value = 'current-config'
        manager = self.hardware_manager
        raid_config = {'foo': 'bar'}
        ret = manager.apply_configuration("", [], raid_config,
                                          delete_existing=True)
        delete_mock.assert_called_once_with("", [])
        create_mock.assert_called_once_with(raid_config={'foo': 'bar'})
        self.assertEqual('current-config', ret)

    @mock.patch.object(hardware_manager.ProliantHardwareManager,
                       'delete_configuration')
    @mock.patch.object(hpssa_manager, 'create_configuration')
    def test_apply_configuration_no_delete(self, create_mock, delete_mock):
        create_mock.return_value = 'current-config'
        manager = self.hardware_manager
        raid_config = {'foo': 'bar'}
        ret = manager.apply_configuration("", [], raid_config,
                                          delete_existing=False)
        create_mock.assert_called_once_with(raid_config={'foo': 'bar'})
        delete_mock.assert_not_called()
        self.assertEqual('current-config', ret)

    @mock.patch.object(hpssa_manager, 'delete_configuration')
    def test_delete_configuration(self, delete_mock):
        delete_mock.return_value = 'current-config'
        ret = self.hardware_manager.delete_configuration("", "")
        delete_mock.assert_called_once_with()
        self.assertEqual('current-config', ret)

    @mock.patch.object(ironic_python_agent.hardware.GenericHardwareManager,
                       'erase_devices')
    @mock.patch.object(hpssa_manager, 'erase_devices')
    def test_erase_devices(self, erase_mock, generic_erase_mock):
        node = {}
        port = {}
        erase_mock.return_value = 'erase_status'
        generic_erase_mock.return_value = {'foo': 'bar'}
        ret = self.hardware_manager.erase_devices(node, port)
        erase_mock.assert_called_once_with()
        generic_erase_mock.assert_called_once_with(node, port)
        self.assertEqual({'Disk Erase Status': 'erase_status', 'foo': 'bar'},
                         ret)

    @mock.patch.object(ironic_python_agent.hardware.GenericHardwareManager,
                       'erase_devices')
    @mock.patch.object(hpssa_manager, 'erase_devices')
    def test_erase_devices_not_supported(self, erase_mock, generic_erase_mock):
        node = {}
        port = {}
        value = ("Sanitize erase not supported in the "
                 "available controllers")
        e = exception.HPSSAOperationError(reason=value)
        erase_mock.side_effect = e

        exc = self.assertRaises(exception.HPSSAOperationError,
                                self.hardware_manager.erase_devices,
                                node, port)

        self.assertIn(value, str(exc))

    @mock.patch.object(sum_controller, 'update_firmware')
    def test_update_firmware_sum(self, update_mock):
        update_mock.return_value = "log files"
        url = self.node['clean_step']['args'].get('url')
        csum = self.node['clean_step']['args'].get('checksum')
        comp = self.node['clean_step']['args'].get('components')
        ret = self.hardware_manager.update_firmware_sum(self.node, "")
        update_mock.assert_called_once_with(self.node, url, csum,
                                            components=comp)
        self.assertEqual('log files', ret)

    @mock.patch.object(sum_controller, 'update_firmware')
    def test_flash_firmware_sum(self, update_mock):
        update_mock.return_value = "log files"
        url = self.node['clean_step']['args'].get('url')
        csum = self.node['clean_step']['args'].get('checksum')
        comp = self.node['clean_step']['args'].get('components')
        ret = self.hardware_manager.flash_firmware_sum(self.node, "", url,
                                                       csum, components=comp)
        update_mock.assert_called_once_with(self.node, url, csum,
                                            components=comp)
        self.assertEqual('log files', ret)
