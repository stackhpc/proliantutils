# Copyright 2019 Hewlett Packard Enterprise Development LP
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


import builtins
import collections
import io
import json

import ddt
import mock
import sushy
from sushy.resources.system import system
import testtools

from proliantutils import exception
from proliantutils.ilo import constants as ilo_cons
from proliantutils.redfish import main
from proliantutils.redfish import redfish
from proliantutils.redfish.resources.account_service import account
from proliantutils.redfish.resources.account_service import account_service
from proliantutils.redfish.resources import gpu_common as common_gpu
from proliantutils.redfish.resources.manager import manager
from proliantutils.redfish.resources.manager import virtual_media
from proliantutils.redfish.resources.system import bios
from proliantutils.redfish.resources.system import constants as sys_cons
from proliantutils.redfish.resources.system import iscsi
from proliantutils.redfish.resources.system import memory
from proliantutils.redfish.resources.system import pci_device
from proliantutils.redfish.resources.system.storage import array_controller
from proliantutils.redfish.resources.system.storage \
    import common as common_storage
from proliantutils.redfish.resources.system import system as pro_sys
from proliantutils.redfish.resources.system import tls_config


@ddt.ddt
class RedfishOperationsTestCase(testtools.TestCase):

    @mock.patch.object(main, 'HPESushy', autospec=True)
    def setUp(self, sushy_mock):
        super(RedfishOperationsTestCase, self).setUp()
        self.sushy = mock.MagicMock()
        self.sushy.get_system_collection_path.return_value = (
            '/redfish/v1/Systems')
        self.sushy.get_manager_collection_path.return_value = (
            '/redfish/v1/Managers')
        sushy_mock.return_value = self.sushy
        with open('proliantutils/tests/redfish/'
                  'json_samples/root.json', 'r') as f:
            self.sushy.json = json.loads(f.read())

        self.rf_client = redfish.RedfishOperations(
            '1.2.3.4', username='foo', password='bar')
        args, kwargs = sushy_mock.call_args
        self.assertEqual(('https://1.2.3.4',), args)
        self.assertFalse(kwargs.get('verify'))
        self.assertEqual('/redfish/v1/', kwargs.get('root_prefix'))
        self.assertEqual('foo', kwargs.get('username'))
        self.assertEqual('bar', kwargs.get('password'))

    @mock.patch.object(main, 'HPESushy', autospec=True)
    def test_sushy_init_fail(self, sushy_mock):
        sushy_mock.side_effect = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloConnectionError,
            'The Redfish controller at "https://1.2.3.4" has thrown error',
            redfish.RedfishOperations,
            '1.2.3.4', username='foo', password='bar')

    def test__get_sushy_system_fail(self):
        self.rf_client._sushy.get_system.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish System "apple" was not found.',
            self.rf_client._get_sushy_system, 'apple')

    def test__get_sushy_manager_fail(self):
        self.rf_client._sushy.get_manager.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish Manager "banana" was not found.',
            self.rf_client._get_sushy_manager, 'banana')

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_product_name(self, get_system_mock):
        product_mock = mock.PropertyMock(return_value='ProLiant DL180 Gen10')
        type(get_system_mock.return_value).model = product_mock
        product_name = self.rf_client.get_product_name()
        self.assertEqual('ProLiant DL180 Gen10', product_name)

    def test_get_host_power_status(self):
        self.sushy.get_system().power_state = sushy.SYSTEM_POWER_STATE_ON
        power_state = self.rf_client.get_host_power_status()
        self.assertEqual('ON', power_state)

    def test_reset_server(self):
        self.rf_client.reset_server()
        self.sushy.get_system().reset_system.assert_called_once_with(
            sushy.RESET_FORCE_RESTART)

    def test_reset_server_invalid_value(self):
        self.sushy.get_system().reset_system.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to reset server.',
            self.rf_client.reset_server)

    @mock.patch.object(redfish.RedfishOperations, 'get_host_power_status')
    def test_set_host_power_no_change(self, get_host_power_status_mock):
        get_host_power_status_mock.return_value = 'ON'
        self.rf_client.set_host_power('ON')
        self.assertTrue(get_host_power_status_mock.called)
        self.assertFalse(self.sushy.get_system().reset_system.called)

    @mock.patch.object(redfish.RedfishOperations, 'get_host_power_status')
    def test_set_host_power_failure(self, get_host_power_status_mock):
        get_host_power_status_mock.return_value = 'OFF'
        self.sushy.get_system().reset_system.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to set power state of server to ON',
            self.rf_client.set_host_power, 'ON')

    def test_set_host_power_invalid_input(self):
        self.assertRaisesRegex(
            exception.InvalidInputError,
            'The parameter "target_value" value "Off" is invalid.',
            self.rf_client.set_host_power, 'Off')

    @mock.patch.object(redfish.RedfishOperations, 'get_host_power_status')
    def test_set_host_power_change(self, get_host_power_status_mock):
        get_host_power_status_mock.return_value = 'OFF'
        self.rf_client.set_host_power('ON')
        self.sushy.get_system().reset_system.assert_called_once_with(
            sushy.RESET_ON)

    def test_press_pwr_btn(self):
        self.rf_client.press_pwr_btn()
        self.sushy.get_system().push_power_button.assert_called_once_with(
            sys_cons.PUSH_POWER_BUTTON_PRESS)

    def test_press_pwr_btn_fail(self):
        self.sushy.get_system().push_power_button.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to press power button',
            self.rf_client.press_pwr_btn)

    def test_hold_pwr_btn(self):
        self.rf_client.hold_pwr_btn()
        self.sushy.get_system().push_power_button.assert_called_once_with(
            sys_cons.PUSH_POWER_BUTTON_PRESS_AND_HOLD)

    def test_hold_pwr_btn_fail(self):
        self.sushy.get_system().push_power_button.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to press and hold power button',
            self.rf_client.hold_pwr_btn)

    def test_get_one_time_boot_not_set(self):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        self.sushy.get_system().json = system_json['default']
        boot = self.rf_client.get_one_time_boot()
        self.assertEqual('Normal', boot)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_one_time_boot_set_cdrom(self, get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        self.conn = mock.Mock()
        self.conn.get.return_value.json.return_value = system_json[
            'System_op_for_one_time_boot_cdrom']
        self.sys_inst = system.System(self.conn,
                                      '/redfish/v1/Systems/437XR1138R2',
                                      redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        ret = self.rf_client.get_one_time_boot()
        self.assertEqual(ret, 'CDROM')

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_pending_boot_mode(self, get_system_mock):
        for cons_val in redfish.BOOT_MODE_MAP.keys():
            (get_system_mock.return_value.bios_settings.
             pending_settings.boot_mode) = cons_val
            result = self.rf_client.get_pending_boot_mode()
            self.assertEqual(redfish.BOOT_MODE_MAP[cons_val], result)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_pending_boot_mode_fail(self, get_system_mock):
        bios_settings_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value.bios_settings).pending_settings = (
            bios_settings_mock)
        self.assertRaisesRegex(
            exception.IloError,
            'The pending BIOS Settings was not found.',
            self.rf_client.get_pending_boot_mode)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_current_boot_mode(self, get_system_mock):
        for cons_val in redfish.BOOT_MODE_MAP.keys():
            get_system_mock.return_value.bios_settings.boot_mode = cons_val
            result = self.rf_client.get_current_boot_mode()
            self.assertEqual(redfish.BOOT_MODE_MAP[cons_val], result)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_current_boot_mode_fail(self, get_system_mock):
        bios_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value).bios_settings = bios_mock
        self.assertRaisesRegex(
            exception.IloError,
            'The current BIOS Settings was not found.',
            self.rf_client.get_current_boot_mode)

    def test_activate_license(self):
        self.rf_client.activate_license('testkey')
        (self.sushy.get_manager.return_value.set_license.
         assert_called_once_with('testkey'))

    def test_activate_license_fail(self):
        self.sushy.get_manager.return_value.set_license.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to update the license',
            self.rf_client.activate_license, 'key')

    def _setup_virtual_media(self):
        self.conn = mock.Mock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/manager.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())

        manager_mock = manager.HPEManager(
            self.conn, '/redfish/v1/Managers/1',
            redfish_version='1.0.2')

        with open('proliantutils/tests/redfish/'
                  'json_samples/vmedia_collection.json', 'r') as f:
            vmedia_collection_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/vmedia.json', 'r') as f:
            vmedia_json = json.loads(f.read())
        return manager_mock, vmedia_collection_json, vmedia_json

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    def test_eject_virtual_media(self, eject_mock, manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['vmedia_inserted']]

        self.rf_client.eject_virtual_media('CDROM')

        eject_mock.assert_called_once_with()

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    def test_eject_virtual_media_invalid_device(self, eject_mock,
                                                manager_mock):
        self.assertRaisesRegex(
            exception.IloError,
            "Invalid device 'XXXXX'. Valid devices: FLOPPY or CDROM.",
            self.rf_client.eject_virtual_media,
            'XXXXX')

        self.assertFalse(eject_mock.called)
        self.assertFalse(manager_mock.called)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    def test_eject_virtual_media_not_inserted(self, eject_mock, manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['default']]

        self.rf_client.eject_virtual_media('CDROM')

        self.assertFalse(eject_mock.called)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    def test_eject_virtual_media_floppy(self, eject_mock, manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['vmedia_floppy']]

        self.rf_client.eject_virtual_media('FLOPPY')

        self.assertFalse(eject_mock.called)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    def test_eject_virtual_media_fail(self, eject_mock, manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        eject_mock.side_effect = sushy.exceptions.SushyError
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['vmedia_inserted']]

        msg = ("The Redfish controller failed to eject the virtual"
               " media device 'CDROM'.")
        self.assertRaisesRegex(exception.IloError, msg,
                               self.rf_client.eject_virtual_media,
                               'CDROM')

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    @mock.patch.object(virtual_media.VirtualMedia, 'insert_media')
    def test_insert_virtual_media(self, insert_mock, eject_mock, manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['default']]
        url = 'http://1.2.3.4:5678/xyz.iso'

        self.rf_client.insert_virtual_media(url, 'CDROM')

        self.assertFalse(eject_mock.called)
        insert_mock.assert_called_once_with(url)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    @mock.patch.object(virtual_media.VirtualMedia, 'insert_media')
    def test_insert_virtual_media_floppy(self, insert_mock, eject_mock,
                                         manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['vmedia_floppy']]
        url = 'http://1.2.3.4:5678/xyz.iso'

        self.rf_client.insert_virtual_media(url, 'FLOPPY')

        self.assertFalse(eject_mock.called)
        insert_mock.assert_called_once_with(url)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    @mock.patch.object(virtual_media.VirtualMedia, 'insert_media')
    def test_insert_virtual_media_inserted(self, insert_mock, eject_mock,
                                           manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['vmedia_inserted']]
        url = 'http://1.2.3.4:5678/xyz.iso'

        self.rf_client.insert_virtual_media(url, 'CDROM')

        eject_mock.assert_called_once_with()
        insert_mock.assert_called_once_with(url)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    @mock.patch.object(virtual_media.VirtualMedia, 'eject_media')
    @mock.patch.object(virtual_media.VirtualMedia, 'insert_media')
    def test_insert_virtual_media_fail(self, insert_mock, eject_mock,
                                       manager_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        insert_mock.side_effect = sushy.exceptions.SushyError
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['vmedia_inserted']]
        url = 'http://1.2.3.4:5678/xyz.iso'
        msg = ("The Redfish controller failed to insert the media url "
               "%s in the virtual media device 'CDROM'.") % url

        self.assertRaisesRegex(exception.IloError, msg,
                               self.rf_client.insert_virtual_media,
                               url, 'CDROM')

    @mock.patch.object(virtual_media.VirtualMedia, 'set_vm_status')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_set_vm_status(self, manager_mock, set_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['default']]

        self.rf_client.set_vm_status(device='CDROM')

        set_mock.assert_called_once_with(True)

    @mock.patch.object(virtual_media.VirtualMedia, 'set_vm_status')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_set_vm_status_fail(self, manager_mock, set_mock):
        manager_mock.return_value, vmedia_collection_json, vmedia_json = (
            self._setup_virtual_media())
        set_mock.side_effect = sushy.exceptions.SushyError
        self.conn.get.return_value.json.side_effect = [
            vmedia_collection_json, vmedia_json['default']]
        msg = ("The Redfish controller failed to set the virtual "
               "media status.")

        self.assertRaisesRegex(exception.IloError, msg,
                               self.rf_client.set_vm_status,
                               'CDROM')

    @mock.patch.object(virtual_media.VirtualMedia, 'set_vm_status')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_set_vm_status_not_supported_boot_option(self, manager_mock,
                                                     set_mock):
        msg = ("Virtual media boot option 'XXXX' is invalid.")
        self.assertRaisesRegex(exception.IloInvalidInputError, msg,
                               self.rf_client.set_vm_status,
                               device='CDROM', boot_option='XXXX')
        self.assertFalse(manager_mock.called)
        self.assertFalse(set_mock.called)

    @mock.patch.object(virtual_media.VirtualMedia, 'set_vm_status')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_set_vm_status_boot_option_connect(self, manager_mock, set_mock):
        self.rf_client.set_vm_status(device='CDROM', boot_option='CONNECT')
        self.assertFalse(manager_mock.called)
        self.assertFalse(set_mock.called)

    def test_update_firmware(self):
        self.rf_client.update_firmware('fw_file_url', 'ilo')
        (self.sushy.get_update_service.return_value.flash_firmware.
         assert_called_once_with(self.rf_client, 'fw_file_url'))

    def test_update_firmware_flash_firmware_fail(self):
        (self.sushy.get_update_service.return_value.
         flash_firmware.side_effect) = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to update firmware',
            self.rf_client.update_firmware, 'fw_file_url', 'cpld')

    def test_update_firmware_get_update_service_fail(self):
        self.sushy.get_update_service.side_effect = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to update firmware',
            self.rf_client.update_firmware, 'fw_file_url', 'cpld')

    @mock.patch.object(redfish.RedfishOperations, 'get_current_boot_mode')
    def test__is_boot_mode_uefi_uefi(self, get_current_boot_mode_mock):
        get_current_boot_mode_mock.return_value = (
            redfish.BOOT_MODE_MAP.get(sys_cons.BIOS_BOOT_MODE_UEFI))
        result = self.rf_client._is_boot_mode_uefi()
        self.assertTrue(result)

    @mock.patch.object(redfish.RedfishOperations, 'get_current_boot_mode')
    def test__is_boot_mode_uefi_bios(self, get_current_boot_mode_mock):
        get_current_boot_mode_mock.return_value = (
            redfish.BOOT_MODE_MAP.get(sys_cons.BIOS_BOOT_MODE_LEGACY_BIOS))
        result = self.rf_client._is_boot_mode_uefi()
        self.assertFalse(result)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_persistent_boot_device_uefi_cdrom(self, get_sushy_system_mock,
                                                   _uefi_boot_mode_mock):
        (get_sushy_system_mock.return_value.
         bios_settings.boot_settings.
         get_persistent_boot_device.return_value) = (sushy.
                                                     BOOT_SOURCE_TARGET_CD)
        _uefi_boot_mode_mock.return_value = True
        result = self.rf_client.get_persistent_boot_device()
        self.assertEqual(
            result,
            redfish.DEVICE_REDFISH_TO_COMMON.get(sushy.BOOT_SOURCE_TARGET_CD))

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_persistent_boot_device_bios(self, get_sushy_system_mock,
                                             _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = False
        result = self.rf_client.get_persistent_boot_device()
        self.assertIsNone(result)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_persistent_boot_device_cdrom_continuous(self,
                                                         get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        self.conn = mock.Mock()
        self.conn.get.return_value.json.return_value = system_json[
            'System_op_for_cdrom_persistent_boot']
        self.sys_inst = system.System(self.conn,
                                      '/redfish/v1/Systems/437XR1138R2',
                                      redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        ret = self.rf_client.get_persistent_boot_device()
        self.assertEqual(ret, 'CDROM')

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_persistent_boot_device_exp(self, get_system_mock,
                                            _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = True
        boot_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value.bios_settings).boot_settings = (
            boot_mock)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller is unable to get persistent boot device.',
            self.rf_client.get_persistent_boot_device)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_pending_boot_mode(self, get_system_mock):
        self.rf_client.set_pending_boot_mode('uefi')
        (get_system_mock.return_value.
         bios_settings.pending_settings.set_pending_boot_mode.
         assert_called_once_with('uefi'))

    def test_set_pending_boot_mode_invalid_input(self):
        self.assertRaisesRegex(
            exception.IloInvalidInputError,
            'Invalid Boot mode: "test" specified',
            self.rf_client.set_pending_boot_mode, 'test')

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_pending_boot_mode_fail(self, get_system_mock):
        (get_system_mock.return_value.bios_settings.
         pending_settings.set_pending_boot_mode.side_effect) = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to set pending boot mode.',
            self.rf_client.set_pending_boot_mode, 'uefi')

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_update_persistent_boot(self, get_system_mock):
        self.rf_client.update_persistent_boot(['NETWORK'])
        (get_system_mock.return_value.update_persistent_boot.
         assert_called_once_with(['NETWORK'], persistent=True))

    def test_update_persistent_boot_invalid_input(self):
        self.assertRaisesRegex(
            exception.IloInvalidInputError,
            ('Invalid input "test". Valid devices: NETWORK, '
             'HDD, ISCSI, UEFIHTTP or CDROM.'),
            self.rf_client.update_persistent_boot, ['test'])

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_update_persistent_boot_fail(self, get_system_mock):
        get_system_mock.return_value.update_persistent_boot.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to update persistent boot.',
            self.rf_client.update_persistent_boot,
            ['NETWORK'])

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_one_time_boot(self, get_system_mock):
        self.rf_client.set_one_time_boot('CDROM')
        (get_system_mock.return_value.update_persistent_boot.
         assert_called_once_with(['CDROM'], persistent=False))

    def test_set_one_time_boot_invalid_input(self):
        self.assertRaisesRegex(
            exception.IloInvalidInputError,
            ('Invalid input "test". Valid devices: NETWORK, '
             'HDD, ISCSI, UEFIHTTP or CDROM.'),
            self.rf_client.set_one_time_boot, 'test')

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_one_time_boot_fail(self, get_system_mock):
        get_system_mock.return_value.update_persistent_boot.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to set one time boot.',
            self.rf_client.set_one_time_boot,
            'CDROM')

    def _setup_reset_ilo_credential(self):
        self.conn = mock.Mock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/account_service.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())

        account_mock = account_service.HPEAccountService(
            self.conn, '/redfish/v1/AccountService',
            redfish_version='1.0.2')

        with open('proliantutils/tests/redfish/'
                  'json_samples/account_collection.json', 'r') as f:
            account_collection_json = json.loads(f.read())

        with open('proliantutils/tests/redfish/'
                  'json_samples/account.json', 'r') as f:
            account_json = json.loads(f.read())

        return account_mock, account_collection_json, account_json

    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_reset_ilo_credential(self, account_mock):
        account_mock.return_value, account_collection_json, account_json = (
            self._setup_reset_ilo_credential())
        self.conn.get.return_value.json.side_effect = [
            account_collection_json, account_json]

        self.rf_client.reset_ilo_credential('fake-password')
        (self.sushy.get_account_service.return_value.
         accounts.get_member_details.return_value.
         update_credentials.assert_called_once_with('fake-password'))

    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_reset_ilo_credential_fail(self, account_mock):
        account_mock.return_value, account_collection_json, account_json = (
            self._setup_reset_ilo_credential())
        self.conn.get.return_value.json.side_effect = [
            account_collection_json, account_json]

        (self.sushy.get_account_service.return_value.accounts.
         get_member_details.return_value.
         update_credentials.side_effect) = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to update credentials',
            self.rf_client.reset_ilo_credential, 'fake-password')

    @mock.patch.object(account.HPEAccount, 'update_credentials')
    def test_reset_ilo_credential_get_account_service_fail(self, update_mock):
        account_service_not_found_error = sushy.exceptions.SushyError
        account_service_not_found_error.message = (
            'HPEAccountService not found!!')
        self.sushy.get_account_service.side_effect = (
            account_service_not_found_error)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to update credentials for foo. '
            'Error HPEAccountService not found!!',
            self.rf_client.reset_ilo_credential, 'fake-password')
        self.assertFalse(update_mock.called)

    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_reset_ilo_credential_no_member(self, account_mock):
        (self.sushy.get_account_service.return_value.accounts.
         get_member_details.return_value) = None
        self.assertRaisesRegex(
            exception.IloError,
            'No account found with username: foo',
            self.rf_client.reset_ilo_credential, 'fake-password')

    @ddt.data((sys_cons.SUPPORTED_LEGACY_BIOS_ONLY,
               ilo_cons.SUPPORTED_BOOT_MODE_LEGACY_BIOS_ONLY),
              (sys_cons.SUPPORTED_UEFI_ONLY,
               ilo_cons.SUPPORTED_BOOT_MODE_UEFI_ONLY),
              (sys_cons.SUPPORTED_LEGACY_BIOS_AND_UEFI,
               ilo_cons.SUPPORTED_BOOT_MODE_LEGACY_BIOS_AND_UEFI))
    @ddt.unpack
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_supported_boot_mode(self, supported_boot,
                                     expected_boot_val,
                                     get_system_mock):
        type(get_system_mock.return_value).supported_boot_mode = (
            supported_boot)
        actual_val = self.rf_client.get_supported_boot_mode()
        self.assertEqual(expected_boot_val, actual_val)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_supported_boot_mode_error(self, get_system_mock):
        supported_boot_mode_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value).supported_boot_mode = (
            supported_boot_mode_mock)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to get the supported boot modes.',
            self.rf_client.get_supported_boot_mode)

    @mock.patch.object(common_gpu, 'gpu_capabilities')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_chassis')
    @mock.patch.object(redfish.RedfishOperations,
                       '_parse_security_dashboard_values_for_capabilities')
    @mock.patch.object(common_storage, 'get_drive_rotational_speed_rpm')
    @mock.patch.object(common_storage, 'has_nvme_ssd')
    @mock.patch.object(common_storage, 'has_rotational')
    @mock.patch.object(common_storage, 'has_ssd')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_get_server_capabilities(self, get_manager_mock, get_system_mock,
                                     ssd_mock, rotational_mock,
                                     nvme_mock, speed_mock, sec_mock,
                                     get_chassis_mock, gpu_cap_mock):
        type(get_system_mock.return_value.pci_devices).gpu_devices = (
            [mock.MagicMock(spec=pci_device.PCIDevice)])
        type(get_system_mock.return_value.bios_settings).sriov = (
            sys_cons.SRIOV_ENABLED)
        type(get_system_mock.return_value.bios_settings).cpu_vt = (
            sys_cons.CPUVT_ENABLED)
        type(get_system_mock.return_value).secure_boot = (
            mock.MagicMock(spec='Hey I am secure_boot'))
        type(get_system_mock.return_value).rom_version = (
            'U31 v1.00 (03/11/2017)')
        type(get_manager_mock.return_value).firmware_version = 'iLO 5 v1.15'
        type(get_system_mock.return_value).model = 'ProLiant DL180 Gen10'
        nic_mock = mock.PropertyMock(return_value='1Gb')
        type(get_system_mock.return_value.pci_devices).max_nic_capacity = (
            nic_mock)
        tpm_mock = mock.PropertyMock(return_value=sys_cons.TPM_PRESENT_ENABLED)
        type(get_system_mock.return_value.bios_settings).tpm_state = (
            tpm_mock)
        type(get_system_mock.return_value).supported_boot_mode = (
            sys_cons.SUPPORTED_LEGACY_BIOS_AND_UEFI)
        iscsi_mock = mock.MagicMock(spec=iscsi.ISCSIResource)
        iscsi_mock.is_iscsi_boot_supported = mock.MagicMock(return_value=True)
        type(get_system_mock.return_value.bios_settings).iscsi_resource = (
            iscsi_mock)
        type(get_system_mock.return_value.smart_storage.
             array_controllers).members_identities = [
            mock.MagicMock(array_controller.HPEArrayController)]
        MemoryData = collections.namedtuple(
            'MemoryData', ['has_persistent_memory', 'has_nvdimm_n',
                           'has_logical_nvdimm_n'])
        mem = MemoryData(has_persistent_memory=True,
                         has_nvdimm_n=True,
                         has_logical_nvdimm_n=False)
        memory_mock = mock.MagicMock(spec=memory.MemoryCollection)
        memory_mock.details = mock.MagicMock(return_value=mem)
        get_system_mock.return_value.memory = memory_mock
        ssd_mock.return_value = True
        rotational_mock.return_value = True
        nvme_mock.return_value = True
        raid_mock = mock.PropertyMock(return_value=set(['0', '1']))
        type(get_system_mock.return_value.
             smart_storage).logical_raid_levels = (raid_mock)
        speed_mock.return_value = set(['10000', '15000'])
        sec_mock.return_value = {'overall_security_status': 'Risk',
                                 'security_override_switch': 'Ok',
                                 'last_firmware_scan_result': 'Ok'}
        gpu_cap_mock.return_value = (
            [{'gpu_vendor_count': {'gpu_0x102b_count': 1}},
             {'gpu_ven_dev_count': {'gpu_Embedded_Video_Controller_count': 1}},
             {'gpu_ven_dev': {'gpu_Embedded_Video_Controller': 'true'}}])
        actual = self.rf_client.get_server_capabilities()
        expected = {'pci_gpu_devices': 1, 'sriov_enabled': 'true',
                    'secure_boot': 'true', 'cpu_vt': 'true',
                    'rom_firmware_version': 'U31 v1.00 (03/11/2017)',
                    'ilo_firmware_version': 'iLO 5 v1.15',
                    'nic_capacity': '1Gb',
                    'trusted_boot': 'true',
                    'server_model': 'ProLiant DL180 Gen10',
                    'boot_mode_bios': 'true',
                    'boot_mode_uefi': 'true', 'iscsi_boot': 'true',
                    'hardware_supports_raid': 'true',
                    'persistent_memory': 'true',
                    'nvdimm_n': 'true',
                    'logical_nvdimm_n': 'false',
                    'has_ssd': 'true',
                    'has_rotational': 'true',
                    'has_nvme_ssd': 'true',
                    'logical_raid_level_0': 'true',
                    'logical_raid_level_1': 'true',
                    'drive_rotational_10000_rpm': 'true',
                    'drive_rotational_15000_rpm': 'true',
                    'overall_security_status': 'Risk',
                    'security_override_switch': 'Ok',
                    'last_firmware_scan_result': 'Ok',
                    'gpu_0x102b_count': 1,
                    'gpu_Embedded_Video_Controller_count': 1,
                    'gpu_Embedded_Video_Controller': 'true'}
        self.assertEqual(expected, actual)

    @mock.patch.object(common_gpu, 'gpu_capabilities')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_chassis')
    @mock.patch.object(redfish.RedfishOperations,
                       '_parse_security_dashboard_values_for_capabilities')
    @mock.patch.object(common_storage, 'get_drive_rotational_speed_rpm')
    @mock.patch.object(common_storage, 'has_nvme_ssd')
    @mock.patch.object(common_storage, 'has_rotational')
    @mock.patch.object(common_storage, 'has_ssd')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_get_server_capabilities_optional_capabilities_absent(
            self, get_manager_mock, get_system_mock, ssd_mock,
            rotational_mock, nvme_mock, speed_mock, sec_mock,
            get_chassis_mock, gpu_cap_mock):
        type(get_system_mock.return_value.pci_devices).gpu_devices = (
            [mock.MagicMock(spec=pci_device.PCIDevice)])
        type(get_system_mock.return_value.bios_settings).sriov = (
            sys_cons.SRIOV_DISABLED)
        type(get_system_mock.return_value.bios_settings).cpu_vt = (
            sys_cons.CPUVT_DISABLED)
        type(get_system_mock.return_value).secure_boot = (
            mock.PropertyMock(side_effect=exception.MissingAttributeError))
        type(get_system_mock.return_value).rom_version = (
            'U31 v1.00 (03/11/2017)')
        type(get_manager_mock.return_value).firmware_version = 'iLO 5 v1.15'
        type(get_system_mock.return_value).model = 'ProLiant DL180 Gen10'
        nic_mock = mock.PropertyMock(return_value='1Gb')
        type(get_system_mock.return_value.pci_devices).max_nic_capacity = (
            nic_mock)
        type(get_system_mock.return_value.pci_devices).nic_capacity = (
            nic_mock)
        tpm_mock = mock.PropertyMock(return_value=sys_cons.TPM_NOT_PRESENT)
        type(get_system_mock.return_value.bios_settings).tpm_state = (
            tpm_mock)
        type(get_system_mock.return_value).supported_boot_mode = (
            sys_cons.SUPPORTED_UEFI_ONLY)
        iscsi_mock = mock.MagicMock(spec=iscsi.ISCSIResource)
        iscsi_mock.is_iscsi_boot_supported = mock.MagicMock(return_value=False)
        type(get_system_mock.return_value.bios_settings).iscsi_resource = (
            iscsi_mock)
        type(get_system_mock.return_value.smart_storage.
             array_controllers).members_identities = []
        MemoryData = collections.namedtuple(
            'MemoryData', ['has_persistent_memory', 'has_nvdimm_n',
                           'has_logical_nvdimm_n'])
        mem = MemoryData(has_persistent_memory=False,
                         has_nvdimm_n=False,
                         has_logical_nvdimm_n=False)
        memory_mock = mock.MagicMock(spec=memory.MemoryCollection)
        get_system_mock.return_value.memory = memory_mock
        memory_mock.details = mock.MagicMock(return_value=mem)
        ssd_mock.return_value = False
        rotational_mock.return_value = False
        nvme_mock.return_value = False
        raid_mock = mock.PropertyMock(return_value=set())
        type(get_system_mock.return_value.
             smart_storage).logical_raid_levels = (raid_mock)
        speed_mock.return_value = set()
        sec_mock.return_value = {'overall_security_status': 'Risk',
                                 'security_override_switch': 'Ok',
                                 'last_firmware_scan_result': 'Ok'}
        gpu_cap_mock.return_value = (
            [{'gpu_vendor_count': {'gpu_0x102b_count': 1}},
             {'gpu_ven_dev_count': {'gpu_Embedded_Video_Controller_count': 1}},
             {'gpu_ven_dev': {'gpu_Embedded_Video_Controller': 'true'}}])
        actual = self.rf_client.get_server_capabilities()
        expected = {'pci_gpu_devices': 1,
                    'rom_firmware_version': 'U31 v1.00 (03/11/2017)',
                    'ilo_firmware_version': 'iLO 5 v1.15',
                    'nic_capacity': '1Gb',
                    'server_model': 'ProLiant DL180 Gen10',
                    'boot_mode_bios': 'false', 'boot_mode_uefi': 'true',
                    'overall_security_status': 'Risk',
                    'security_override_switch': 'Ok',
                    'last_firmware_scan_result': 'Ok',
                    'gpu_0x102b_count': 1,
                    'gpu_Embedded_Video_Controller_count': 1,
                    'gpu_Embedded_Video_Controller': 'true'}
        self.assertEqual(expected, actual)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_chassis')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_server_capabilities_gpu_fail(self, get_system_mock,
                                              get_chassis_mock):
        gpu_mock = mock.PropertyMock(side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value.pci_devices).gpu_devices = (
            gpu_mock)
        type(get_chassis_mock.return_value.devices).vendor_dict = (
            gpu_mock)
        self.assertRaises(exception.IloError,
                          self.rf_client.get_server_capabilities)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    @mock.patch.object(bios.BIOSPendingSettings, 'update_bios_data_by_post')
    def test_reset_bios_to_default(self, update_bios_mock, get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios_base_configs.json', 'r') as f:
            bios_default_json = json.loads(f.read())
        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            bios_json['BIOS_pending_settings_default'], bios_default_json]
        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        data = bios_default_json['BaseConfigs'][0]['default']
        self.rf_client.reset_bios_to_default()
        update_bios_mock.assert_called_once_with(data)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_reset_bios_to_default_fail(self, get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios_base_configs.json', 'r') as f:
            bios_default_json = json.loads(f.read())
        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            bios_json['BIOS_pending_settings_default'], bios_default_json]
        (get_system_mock.return_value.bios_settings.
         update_bios_to_default.side_effect) = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller is unable to update bios settings"
            " to default", self.rf_client.reset_bios_to_default)

    @mock.patch.object(redfish.LOG, 'debug', autospec=True)
    def test_get_secure_boot_mode(self, log_debug_mock):
        sushy_system_mock = self.sushy.get_system.return_value
        type(sushy_system_mock.secure_boot).current_boot = mock.PropertyMock(
            return_value=sys_cons.SECUREBOOT_CURRENT_BOOT_ENABLED)
        self.rf_client.get_secure_boot_mode()
        log_debug_mock.assert_called_once_with(
            '[iLO 1.2.3.4] Secure boot is Enabled')

        log_debug_mock.reset_mock()
        type(sushy_system_mock.secure_boot).current_boot = mock.PropertyMock(
            return_value=sys_cons.SECUREBOOT_CURRENT_BOOT_DISABLED)
        self.rf_client.get_secure_boot_mode()
        log_debug_mock.assert_called_once_with(
            '[iLO 1.2.3.4] Secure boot is Disabled')

    def test_get_secure_boot_mode_on_fail(self):
        sushy_system_mock = self.sushy.get_system.return_value
        type(sushy_system_mock).secure_boot = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloCommandNotSupportedError,
            'The Redfish controller failed to provide '
            'information about secure boot on the server.',
            self.rf_client.get_secure_boot_mode)

    def test__has_secure_boot(self):
        sushy_system_mock = self.sushy.get_system.return_value
        type(sushy_system_mock).secure_boot = mock.PropertyMock(
            return_value='Hey I am secure_boot')
        self.assertTrue(self.rf_client._has_secure_boot())

    def test__has_secure_boot_on_fail(self):
        sushy_system_mock = self.sushy.get_system.return_value
        type(sushy_system_mock).secure_boot = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        self.assertFalse(self.rf_client._has_secure_boot())
        type(sushy_system_mock).secure_boot = mock.PropertyMock(
            side_effect=exception.MissingAttributeError)
        self.assertFalse(self.rf_client._has_secure_boot())

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_secure_boot_mode(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = True
        self.rf_client.set_secure_boot_mode(True)
        secure_boot_mock = self.sushy.get_system.return_value.secure_boot
        secure_boot_mock.enable_secure_boot.assert_called_once_with(True)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_secure_boot_mode_in_bios(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = False
        self.assertRaisesRegex(
            exception.IloCommandNotSupportedInBiosError,
            'System is not in UEFI boot mode. "SecureBoot" related resources '
            'cannot be changed.',
            self.rf_client.set_secure_boot_mode, True)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_secure_boot_mode_on_fail(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = True
        secure_boot_mock = self.sushy.get_system.return_value.secure_boot
        secure_boot_mock.enable_secure_boot.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to set secure boot settings '
            'on the server.',
            self.rf_client.set_secure_boot_mode, True)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_secure_boot_mode_for_invalid_value(
            self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = True
        secure_boot_mock = self.sushy.get_system.return_value.secure_boot
        secure_boot_mock.enable_secure_boot.side_effect = (
            exception.InvalidInputError('Invalid input'))
        self.assertRaises(
            exception.IloError,
            self.rf_client.set_secure_boot_mode, 'some-non-boolean')

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_reset_secure_boot_keys(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = True
        self.rf_client.reset_secure_boot_keys()
        sushy_system_mock = self.sushy.get_system.return_value
        sushy_system_mock.secure_boot.reset_keys.assert_called_once_with(
            sys_cons.SECUREBOOT_RESET_KEYS_DEFAULT)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_reset_secure_boot_keys_in_bios(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = False
        self.assertRaisesRegex(
            exception.IloCommandNotSupportedInBiosError,
            'System is not in UEFI boot mode. "SecureBoot" related resources '
            'cannot be changed.',
            self.rf_client.reset_secure_boot_keys)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_reset_secure_boot_keys_on_fail(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = True
        sushy_system_mock = self.sushy.get_system.return_value
        sushy_system_mock.secure_boot.reset_keys.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to reset secure boot keys '
            'on the server.',
            self.rf_client.reset_secure_boot_keys)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_clear_secure_boot_keys(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = True
        self.rf_client.clear_secure_boot_keys()
        sushy_system_mock = self.sushy.get_system.return_value
        sushy_system_mock.secure_boot.reset_keys.assert_called_once_with(
            sys_cons.SECUREBOOT_RESET_KEYS_DELETE_ALL)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_clear_secure_boot_keys_in_bios(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = False
        self.assertRaisesRegex(
            exception.IloCommandNotSupportedInBiosError,
            'System is not in UEFI boot mode. "SecureBoot" related resources '
            'cannot be changed.',
            self.rf_client.clear_secure_boot_keys)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_clear_secure_boot_keys_on_fail(self, _is_boot_mode_uefi_mock):
        _is_boot_mode_uefi_mock.return_value = True
        sushy_system_mock = self.sushy.get_system.return_value
        sushy_system_mock.secure_boot.reset_keys.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to clear secure boot keys '
            'on the server.',
            self.rf_client.clear_secure_boot_keys)

    @mock.patch.object(common_storage, 'get_local_gb')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_essential_properties(self, get_system_mock, local_gb_mock):
        memory_mock = mock.PropertyMock(return_value=20)
        type(get_system_mock.return_value.memory_summary).size_gib = (
            memory_mock)
        count_mock = mock.PropertyMock(return_value=40)
        type(get_system_mock.return_value.processors.summary).count = (
            count_mock)
        arch_mock = mock.PropertyMock(return_value='x86 or x86-64')
        type(get_system_mock.return_value.processors.summary).architecture = (
            arch_mock)
        type(get_system_mock.return_value.ethernet_interfaces).summary = (
            {'1': '12:44:6A:3B:04:11'})

        local_gb_mock.return_value = 600
        actual = self.rf_client.get_essential_properties()
        expected = {'properties': {'cpus': 40,
                                   'cpu_arch': 'x86',
                                   'memory_mb': 20480,
                                   'local_gb': 600},
                    'macs': {'1': '12:44:6A:3B:04:11'}}
        self.assertEqual(expected, actual)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_essential_properties_fail(self, get_system_mock):
        memory_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value.memory_summary).size_gib = (
            memory_mock)
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to get the "
            "resource data. Error None",
            self.rf_client.get_essential_properties)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_iscsi_info_bios(self, _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = False
        self.assertRaisesRegex(exception.IloCommandNotSupportedInBiosError,
                               'iSCSI boot is not supported '
                               'in the BIOS boot mode',
                               self.rf_client.set_iscsi_info,
                               'iqn.2011-07.com.example.server:test1',
                               '1', '10.10.1.30')

    @mock.patch.object(redfish.RedfishOperations,
                       '_change_iscsi_target_settings', autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_iscsi_info_uefi(self, _uefi_boot_mode_mock,
                                 change_iscsi_target_settings_mock):
        _uefi_boot_mode_mock.return_value = True
        iscsi_variables = {
            'iSCSITargetName': 'iqn.2011-07.com.example.server:test1',
            'iSCSITargetInfoViaDHCP': False,
            'iSCSILUN': '1',
            'iSCSIConnection': 'Enabled',
            'iSCSITargetIpAddress': '10.10.1.30',
            'iSCSITargetTcpPort': 3260}
        self.rf_client.set_iscsi_info(
            'iqn.2011-07.com.example.server:test1',
            '1', '10.10.1.30')
        change_iscsi_target_settings_mock.assert_called_once_with(
            self.rf_client, iscsi_variables, [])

    @mock.patch.object(redfish.RedfishOperations,
                       '_change_iscsi_target_settings', autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_iscsi_info_uefi_with_mac(self, _uefi_boot_mode_mock,
                                          change_iscsi_target_settings_mock):
        _uefi_boot_mode_mock.return_value = True
        iscsi_variables = {
            'iSCSITargetName': 'iqn.2011-07.com.example.server:test1',
            'iSCSITargetInfoViaDHCP': False,
            'iSCSILUN': '1',
            'iSCSIConnection': 'Enabled',
            'iSCSITargetIpAddress': '10.10.1.30',
            'iSCSITargetTcpPort': 3260}
        self.rf_client.set_iscsi_info(
            'iqn.2011-07.com.example.server:test1',
            '1', '10.10.1.30', macs=['98:f2:b3:ee:f4:00'])
        change_iscsi_target_settings_mock.assert_called_once_with(
            self.rf_client, iscsi_variables, ['98:f2:b3:ee:f4:00'])

    @mock.patch.object(redfish.RedfishOperations,
                       '_change_iscsi_target_settings', autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_iscsi_info_uefi_with_chap(
            self, _uefi_boot_mode_mock, change_iscsi_target_settings_mock):
        _uefi_boot_mode_mock.return_value = True
        iscsi_variables = {
            'iSCSITargetName': 'iqn.2011-07.com.example.server:test1',
            'iSCSITargetInfoViaDHCP': False,
            'iSCSILUN': '1',
            'iSCSIConnection': 'Enabled',
            'iSCSITargetIpAddress': '10.10.1.30',
            'iSCSITargetTcpPort': 3260,
            'iSCSIAuthenticationMethod': 'Chap',
            'iSCSIChapUsername': 'admin',
            'iSCSIChapSecret': 'password'}
        self.rf_client.set_iscsi_info(
            'iqn.2011-07.com.example.server:test1',
            '1', '10.10.1.30', 3260, 'CHAP', 'admin', 'password')
        change_iscsi_target_settings_mock.assert_called_once_with(
            self.rf_client, iscsi_variables, [])

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_unset_iscsi_info_bios(self, _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = False
        self.assertRaisesRegex(exception.IloCommandNotSupportedInBiosError,
                               "iSCSI boot is not supported "
                               "in the BIOS boot mode",
                               self.rf_client.unset_iscsi_info)

    @mock.patch.object(redfish.RedfishOperations,
                       '_change_iscsi_target_settings', autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_unset_iscsi_info_uefi(self, _uefi_boot_mode_mock,
                                   change_iscsi_target_settings_mock):
        _uefi_boot_mode_mock.return_value = True
        iscsi_variables = {
            'iSCSIConnection': 'Disabled'}
        self.rf_client.unset_iscsi_info()
        change_iscsi_target_settings_mock.assert_called_once_with(
            self.rf_client, iscsi_variables, [])

    @mock.patch.object(redfish.RedfishOperations,
                       '_change_iscsi_target_settings', autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_unset_iscsi_info_uefi_with_mac(self, _uefi_boot_mode_mock,
                                            change_iscsi_target_settings_mock):
        _uefi_boot_mode_mock.return_value = True
        iscsi_variables = {
            'iSCSIConnection': 'Disabled'}
        self.rf_client.unset_iscsi_info(['98:f2:b3:ee:f4:00'])
        change_iscsi_target_settings_mock.assert_called_once_with(
            self.rf_client, iscsi_variables, ['98:f2:b3:ee:f4:00'])

    @mock.patch.object(iscsi.ISCSISettings, 'update_iscsi_settings')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test__change_iscsi_target_settings(
            self, get_system_mock, update_iscsi_settings_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios_mappings.json', 'r') as f:
            bios_mappings_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi.json', 'r') as f:
            iscsi_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi_settings.json', 'r') as f:
            iscsi_settings_json = json.loads(f.read())

        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            bios_mappings_json['Default'], iscsi_json,
            iscsi_settings_json['Default']]
        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        iscsi_variable = {'iSCSITargetName':
                          'iqn.2011-07.com.example.server:test1',
                          'iSCSILUN': '1',
                          'iSCSITargetIpAddress': '10.10.1.30',
                          'iSCSITargetTcpPort': 3260,
                          'iSCSITargetInfoViaDHCP': False,
                          'iSCSIConnection': 'Enabled'}
        iscsi_data1 = {'iSCSITargetName':
                       'iqn.2011-07.com.example.server:test1',
                       'iSCSILUN': '1',
                       'iSCSITargetIpAddress': '10.10.1.30',
                       'iSCSITargetTcpPort': 3260,
                       'iSCSITargetInfoViaDHCP': False,
                       'iSCSIConnection': 'Enabled',
                       'iSCSIAttemptName': 'NicBoot1',
                       'iSCSINicSource': 'NicBoot1',
                       'iSCSIAttemptInstance': 1}
        iscsi_data2 = {'iSCSITargetName':
                       'iqn.2011-07.com.example.server:test1',
                       'iSCSILUN': '1',
                       'iSCSITargetIpAddress': '10.10.1.30',
                       'iSCSITargetTcpPort': 3260,
                       'iSCSITargetInfoViaDHCP': False,
                       'iSCSIConnection': 'Enabled',
                       'iSCSIAttemptName': 'NicBoot2',
                       'iSCSINicSource': 'NicBoot2',
                       'iSCSIAttemptInstance': 2}

        data = {
            'iSCSISources': [iscsi_data1, iscsi_data2]
        }
        self.rf_client._change_iscsi_target_settings(iscsi_variable, [])
        update_iscsi_settings_mock.assert_called_once_with(
            data)

    @mock.patch.object(pro_sys.HPESystem, 'validate_macs')
    @mock.patch.object(pro_sys.HPESystem, 'get_nic_association_name_by_mac')
    @mock.patch.object(iscsi.ISCSISettings, 'update_iscsi_settings')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test__change_iscsi_target_settings_with_mac(
            self, get_system_mock, update_iscsi_settings_mock,
            get_nic_association_mock, validate_macs_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi.json', 'r') as f:
            iscsi_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi_settings.json', 'r') as f:
            iscsi_settings_json = json.loads(f.read())

        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            iscsi_json,
            iscsi_settings_json['Default']]
        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        get_nic_association_mock.return_value = 'NicBoot1'
        iscsi_variable = {'iSCSITargetName':
                          'iqn.2011-07.com.example.server:test1',
                          'iSCSILUN': '1',
                          'iSCSITargetIpAddress': '10.10.1.30',
                          'iSCSITargetTcpPort': 3260,
                          'iSCSITargetInfoViaDHCP': False,
                          'iSCSIConnection': 'Enabled'}
        iscsi_data = {'iSCSITargetName':
                      'iqn.2011-07.com.example.server:test1',
                      'iSCSILUN': '1',
                      'iSCSITargetIpAddress': '10.10.1.30',
                      'iSCSITargetTcpPort': 3260,
                      'iSCSITargetInfoViaDHCP': False,
                      'iSCSIConnection': 'Enabled',
                      'iSCSIAttemptName': 'NicBoot1',
                      'iSCSINicSource': 'NicBoot1',
                      'iSCSIAttemptInstance': 1}
        data = {
            'iSCSISources': [iscsi_data]
        }
        self.rf_client._change_iscsi_target_settings(
            iscsi_variable, ['98:f2:b3:ee:f4:00'])
        update_iscsi_settings_mock.assert_called_once_with(
            data)
        validate_macs_mock.assert_called_once_with(['98:f2:b3:ee:f4:00'])

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test__change_iscsi_target_settings_failed_getting_mappings(
            self, get_system_mock):
        mapping_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value.bios_settings).bios_mappings = (
            mapping_mock)
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to get the "
            "bios mappings. Error",
            self.rf_client._change_iscsi_target_settings, {}, [])

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test__change_iscsi_target_settings_no_macs(
            self, get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios_mappings.json', 'r') as f:
            bios_mappings_json = json.loads(f.read())
        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            bios_mappings_json['Mappings_without_nic']]
        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        self.assertRaisesRegex(
            exception.IloError,
            "No macs were found on the system",
            self.rf_client._change_iscsi_target_settings, {}, [])

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test__change_iscsi_target_settings_mac_invalid(
            self, get_system_mock):
        msg = ("Given macs: %(macs)s not found in the system"
               % {'macs': str(['12:44:6A:3B:04:15'])})
        get_system_mock.return_value.validate_macs.side_effect = (
            exception.InvalidInputError(msg))
        self.assertRaisesRegex(
            exception.InvalidInputError,
            r"Given macs: \['12:44:6A:3B:04:15'\] not found in the system",
            self.rf_client._change_iscsi_target_settings, {},
            ['12:44:6A:3B:04:15'])

    @mock.patch.object(iscsi.ISCSISettings, 'update_iscsi_settings')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test__change_iscsi_target_settings_update_failed(
            self, get_system_mock, update_iscsi_settings_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios_mappings.json', 'r') as f:
            bios_mappings_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi.json', 'r') as f:
            iscsi_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi_settings.json', 'r') as f:
            iscsi_settings_json = json.loads(f.read())

        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            bios_mappings_json['Default'], iscsi_json,
            iscsi_settings_json['Default']]

        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        iscsi_variable = {'iSCSITargetName':
                          'iqn.2011-07.com.example.server:test1',
                          'iSCSILUN': '1',
                          'iSCSITargetIpAddress': '10.10.1.30',
                          'iSCSITargetTcpPort': 3260,
                          'iSCSITargetInfoViaDHCP': False,
                          'iSCSIConnection': 'Enabled'}
        update_iscsi_settings_mock.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller is failed to update iSCSI '
            'settings.',
            self.rf_client._change_iscsi_target_settings, iscsi_variable, [])

    @mock.patch.object(iscsi.ISCSISettings, 'update_iscsi_settings')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_iscsi_initiator_info(
            self, get_system_mock, _uefi_boot_mode_mock,
            update_iscsi_settings_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi.json', 'r') as f:
            iscsi_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi_settings.json', 'r') as f:
            iscsi_settings_json = json.loads(f.read())

        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            iscsi_json, iscsi_settings_json['Default']]
        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        _uefi_boot_mode_mock.return_value = True
        initiator = 'iqn.2015-02.com.hpe:uefi-U31'
        data = {'iSCSIInitiatorName': initiator}
        self.rf_client.set_iscsi_initiator_info(initiator)
        update_iscsi_settings_mock.assert_called_once_with(
            data)

    @mock.patch.object(iscsi.ISCSISettings, 'update_iscsi_settings')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_iscsi_initiator_info_update_failed(
            self, get_system_mock, _uefi_boot_mode_mock,
            update_iscsi_settings_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi.json', 'r') as f:
            iscsi_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi_settings.json', 'r') as f:
            iscsi_settings_json = json.loads(f.read())

        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            iscsi_json, iscsi_settings_json['Default']]
        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        _uefi_boot_mode_mock.return_value = True
        initiator = 'iqn.2015-02.com.hpe:uefi-U31'
        update_iscsi_settings_mock.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller has failed to update iSCSI '
            'settings.',
            self.rf_client.set_iscsi_initiator_info,
            initiator)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_set_iscsi_initiator_info_bios(self, _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = False
        self.assertRaisesRegex(exception.IloCommandNotSupportedInBiosError,
                               'iSCSI initiator cannot be updated in '
                               'BIOS boot mode',
                               self.rf_client.set_iscsi_initiator_info,
                               'iqn.2015-02.com.hpe:uefi-U31')

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_iscsi_initiator_info(
            self, get_system_mock, _uefi_boot_mode_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/iscsi.json', 'r') as f:
            iscsi_json = json.loads(f.read())
        self.conn = mock.Mock()
        self.conn.get.return_value.json.side_effect = [
            system_json['default'], bios_json['Default'],
            iscsi_json]
        self.sys_inst = pro_sys.HPESystem(self.conn,
                                          '/redfish/v1/Systems/437XR1138R2',
                                          redfish_version='1.0.2')
        get_system_mock.return_value = self.sys_inst
        _uefi_boot_mode_mock.return_value = True
        ret = self.rf_client.get_iscsi_initiator_info()
        self.assertEqual('iqn.2015-02.com.hpe:uefi-U31', ret)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_iscsi_initiator_info_failed(
            self, get_system_mock, _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = True
        iscsi_resource_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value.bios_settings).iscsi_resource = (
            iscsi_resource_mock)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller has failed to get the '
            'iSCSI initiator.',
            self.rf_client.get_iscsi_initiator_info)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi',
                       autospec=True)
    def test_get_iscsi_initiator_info_bios(self, _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = False
        self.assertRaisesRegex(exception.IloCommandNotSupportedInBiosError,
                               'iSCSI initiator cannot be retrieved in '
                               'BIOS boot mode',
                               self.rf_client.get_iscsi_initiator_info)

    def test_inject_nmi(self):
        self.sushy.get_system().power_state = sushy.SYSTEM_POWER_STATE_ON
        self.rf_client.inject_nmi()
        self.sushy.get_system().reset_system.assert_called_once_with(
            sushy.RESET_NMI)

    def test_inject_nmi_power_off(self):
        self.sushy.get_system().power_state = sushy.SYSTEM_POWER_STATE_OFF
        self.assertRaisesRegex(
            exception.IloError,
            'Server is not in powered on state.',
            self.rf_client.inject_nmi)
        self.assertFalse(self.sushy.get_system().reset_system.called)

    def test_inject_nmi_sushy_exc(self):
        self.sushy.get_system().power_state = sushy.SYSTEM_POWER_STATE_ON
        self.sushy.get_system().reset_system.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to inject nmi',
            self.rf_client.inject_nmi)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_current_bios_settings_filter_true(self, get_system_mock):

        only_allowed_settings = True
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("Default")
        type(
            get_system_mock.return_value.bios_settings).json = (
                mock.PropertyMock(return_value=jsonval))
        settings = jsonval.get('Attributes')
        expected_value = {k: settings[k] for k in (
            ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES) if k in settings}
        actual_value = self.rf_client.get_current_bios_settings(
            only_allowed_settings)
        self.assertEqual(expected_value, actual_value)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_current_bios_settings_filter_false(self, get_system_mock):

        only_allowed_settings = False
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("Default")
        type(
            get_system_mock.return_value.bios_settings).json = (
                mock.PropertyMock(return_value=jsonval))
        settings = jsonval.get('Attributes')
        expected_value = settings
        actual_value = self.rf_client.get_current_bios_settings(
            only_allowed_settings)
        self.assertEqual(expected_value, actual_value)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_current_bios_settings_raises_exception(self, get_system_mock):

        only_allowed_settings = True
        bios_mock = mock.PropertyMock()
        bios_mock.side_effect = sushy.exceptions.SushyError
        type(get_system_mock.return_value.bios_settings).json = bios_mock
        self.assertRaisesRegex(
            exception.IloError,
            'The current BIOS Settings were not found',
            self.rf_client.get_current_bios_settings,
            only_allowed_settings)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_pending_bios_settings_filter_true(self, system_mock):

        only_allowed_settings = True
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("BIOS_pending_settings_default")
        type(system_mock.return_value.bios_settings.pending_settings).json = (
            mock.PropertyMock(return_value=jsonval))
        settings = jsonval.get('Attributes')
        expected_value = {k: settings[k] for k in (
            ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES) if k in settings}
        actual_value = self.rf_client.get_pending_bios_settings(
            only_allowed_settings)
        self.assertEqual(expected_value, actual_value)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_pending_bios_settings_filter_false(self, system_mock):

        only_allowed_settings = False
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("BIOS_pending_settings_default")
        type(system_mock.return_value.bios_settings.pending_settings).json = (
            mock.PropertyMock(return_value=jsonval))
        expected = jsonval.get('Attributes')
        actual = self.rf_client.get_pending_bios_settings(
            only_allowed_settings)
        self.assertEqual(expected, actual)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_pending_bios_settings_raises_exception(self, system_mock):

        only_allowed_settings = True
        bios_mock = mock.PropertyMock()
        bios_mock.side_effect = sushy.exceptions.SushyError
        type(system_mock.return_value.bios_settings.pending_settings).json = (
            bios_mock)
        self.assertRaisesRegex(
            exception.IloError,
            'The pending BIOS Settings were not found',
            self.rf_client.get_pending_bios_settings,
            only_allowed_settings)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_default_bios_settings_filter_true(self, get_system_mock):

        only_allowed_settings = True
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("Default")
        settings = jsonval.get("Attributes")
        type(get_system_mock.return_value.bios_settings).default_settings = (
            mock.PropertyMock(return_value=settings))
        expected = {k: settings[k] for k in (
            ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES) if k in settings}
        actual = self.rf_client.get_default_bios_settings(
            only_allowed_settings)
        self.assertEqual(expected, actual)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_default_bios_settings_filter_false(self, get_system_mock):

        only_allowed_settings = False
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("Default")
        settings = jsonval.get("Attributes")
        type(get_system_mock.return_value.bios_settings).default_settings = (
            mock.PropertyMock(return_value=settings))
        expected = settings
        actual = self.rf_client.get_default_bios_settings(
            only_allowed_settings)
        self.assertEqual(expected, actual)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_default_bios_settings_raises_exception(self, get_system_mock):

        only_allowed_settings = True
        bios_mock = mock.PropertyMock(side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value.bios_settings).default_settings = (
            bios_mock)
        self.assertRaisesRegex(
            exception.IloError,
            'The default BIOS Settings were not found',
            self.rf_client.get_default_bios_settings,
            only_allowed_settings)

    @mock.patch.object(bios.BIOSPendingSettings, 'update_bios_data_by_patch')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_bios_settings_no_data(self, system_mock, update_data_mock):
        data = None
        apply_filter = True
        self.assertRaisesRegex(
            exception.IloError,
            "Could not apply settings with empty data",
            self.rf_client.set_bios_settings,
            data, apply_filter)
        update_data_mock.assert_not_called()
        system_mock.assert_not_called()

    @mock.patch.object(bios.BIOSPendingSettings, 'update_bios_data_by_patch')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_bios_settings_no_data_no_filter(self, system_mock,
                                                 update_data_mock):

        data = None
        apply_filter = False
        self.assertRaisesRegex(
            exception.IloError,
            "Could not apply settings with empty data",
            self.rf_client.set_bios_settings,
            data, apply_filter)
        update_data_mock.assert_not_called()
        system_mock.assert_not_called()

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_bios_settings_filter_true_valid_data(self, system_mock):
        apply_filter = True
        data = {
            "BootOrderPolicy": "AttemptOnce",
            "IntelPerfMonitoring": "Enabled",
            "IntelProcVtd": "Disabled",
            "UefiOptimizedBoot": "Disabled",
            "PowerProfile": "MaxPerf",
        }
        bios_ps_mock = mock.MagicMock(spec=bios.BIOSPendingSettings)
        pending_settings_mock = mock.PropertyMock(return_value=bios_ps_mock)
        type(system_mock.return_value.bios_settings).pending_settings = (
            pending_settings_mock)

        self.rf_client.set_bios_settings(data, apply_filter)
        bios_ps_mock.update_bios_data_by_patch.assert_called_once_with(data)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_bios_settings_filter_true_invalid_data(self, system_mock):
        apply_filter = True
        data = {
            "AdminName": "Administrator",
            "BootOrderPolicy": "AttemptOnce",
            "IntelPerfMonitoring": "Enabled",
            "IntelProcVtd": "Disabled",
            "UefiOptimizedBoot": "Disabled",
            "PowerProfile": "MaxPerf",
            "TimeZone": "Utc1"
        }

        self.assertRaisesRegex(
            exception.IloError,
            "Could not apply settings as one or more settings"
            " are not supported",
            self.rf_client.set_bios_settings,
            data, apply_filter)
        system_mock.assert_called_once_with(redfish.PROLIANT_SYSTEM_ID)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_bios_settings_filter_false(self, system_mock):
        apply_filter = False
        data = {
            "BootMode": "LEGACY",
            "ServerName": "Gen9 server",
            "TimeFormat": "Ist",
            "BootOrderPolicy": "RetryIndefinitely",
            "ChannelInterleaving": "Enabled",
            "CollabPowerControl": "Enabled",
            "ConsistentDevNaming": "LomsOnly",
            "CustomPostMessage": ""
        }

        bios_ps_mock = mock.MagicMock(spec=bios.BIOSPendingSettings)
        pending_settings_mock = mock.PropertyMock(return_value=bios_ps_mock)
        type(system_mock.return_value.bios_settings).pending_settings = (
            pending_settings_mock)

        self.rf_client.set_bios_settings(data, apply_filter)
        bios_ps_mock.update_bios_data_by_patch.assert_called_once_with(data)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_bios_settings_raises_exception(self, system_mock):
        apply_filter = True
        data = {
            "BootOrderPolicy": "AttemptOnce",
            "IntelPerfMonitoring": "Enabled",
            "IntelProcVtd": "Disabled",
            "UefiOptimizedBoot": "Disabled",
            "PowerProfile": "MaxPerf"
        }

        pending_settings_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(system_mock.return_value.bios_settings).pending_settings = (
            pending_settings_mock)
        self.assertRaisesRegex(
            exception.IloError,
            'The pending BIOS Settings resource not found',
            self.rf_client.set_bios_settings,
            data,
            apply_filter)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_host_post_state(self, get_system_mock):
        post_state = mock.PropertyMock(return_value='poweroff')
        type(get_system_mock.return_value).post_state = post_state
        result = self.rf_client.get_host_post_state()
        self.assertEqual('PowerOff', result)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_do_one_button_secure_erase(self, get_system_mock):
        self.rf_client.do_one_button_secure_erase()
        (get_system_mock.return_value.
         do_one_button_secure_erase.assert_called_once())

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_do_disk_erase_hdd(self, get_system_mock):
        self.rf_client.do_disk_erase('HDD')
        get_system_mock.return_value.do_disk_erase.assert_called_once_with(
            'HDD', None)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_do_disk_erase_ssd(self, get_system_mock):
        self.rf_client.do_disk_erase('SSD')
        get_system_mock.return_value.do_disk_erase.assert_called_once_with(
            'SSD', None)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_do_disk_erase_ssd_pattern_zero(self, get_system_mock):
        self.rf_client.do_disk_erase('SSD', 'zero')
        get_system_mock.return_value.do_disk_erase.assert_called_once_with(
            'SSD', 'zero')

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_has_disk_erase_completed(self, get_system_mock):
        (get_system_mock.return_value.
         has_disk_erase_completed.return_value) = True
        self.assertEqual(True, self.rf_client.has_disk_erase_completed())

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_delete_raid_configuration(self, get_system_mock):
        self.rf_client.delete_raid_configuration()
        get_system_mock.return_value.delete_raid.assert_called_once_with()

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_create_raid_configuration(self, get_system_mock):
        ld1 = {"size_gb": 150, "raid_level": '0', "is_root_volume": True}
        raid_config = {"logical_disks": [ld1]}
        self.rf_client.create_raid_configuration(raid_config)
        get_system_mock.return_value.create_raid.assert_called_once_with(
            raid_config)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_read_raid_configuration(self, get_system_mock):
        result_ld1 = [{'size_gb': 149,
                       'physical_disks': [u'2I:1:1'],
                       'raid_level': u'0',
                       'root_device_hint': {'wwn': u'0x600508B'},
                       'controller': u'Smart Storage Controller in Slot 1',
                       'volume_name': u'01E6E63APFJHD'}]
        config = {'logical_disks': result_ld1}
        expected = [('HPE Smart Array P408i-p SR Gen10', config)]
        get_system_mock.return_value.read_raid.return_value = expected
        self.assertEqual(expected, self.rf_client.read_raid_configuration())

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_bios_settings_result_failed(self, get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios_failed.json', 'r') as f:
            jsonval = json.loads(f.read()).get("Default")

        type(get_system_mock.return_value.bios_settings).messages = (
            jsonval['@Redfish.Settings']['Messages'])

        expected_settings = [
            {
                "MessageArgs": [
                    "MinProcIdlePkgState"
                ],
                "MessageID": "Base.1.0:PropertyNotWritable"
            },
            {
                "MessageArgs": [
                    "MinProcIdlePower"
                ],
                "MessageID": "Base.1.0:PropertyNotWritable"
            },
            {
                "MessageArgs": [
                    "EnergyPerfBias"
                ],
                "MessageID": "Base.1.0:PropertyNotWritable"
            },
            {
                "MessageArgs": [
                    "PowerRegulator"
                ],
                "MessageID": "Base.1.0:PropertyNotWritable"
            },
            {
                "MessageArgs": [],
                "MessageID": "Base.1.0:Success"
            }
        ]
        expected = {"status": "failed", "results": expected_settings}
        actual = self.rf_client.get_bios_settings_result()
        self.assertEqual(expected, actual)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_bios_settings_result_success(self, get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("Default")
        actual_settings = [
            {
                "MessageId": "Base.1.0.Success"
            }
        ]
        type(get_system_mock.return_value.bios_settings).messages = (
            jsonval['@Redfish.Settings']['Messages'])
        actual = self.rf_client.get_bios_settings_result()
        expected = {"status": "success", "results": actual_settings}
        self.assertEqual(expected, actual)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_available_disk_types(self, get_system_mock):
        get_system_mock.return_value.get_disk_types.return_value = ['HDD',
                                                                    'SSD']
        self.assertEqual(
            ['HDD', 'SSD'], self.rf_client.get_available_disk_types())

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_http_boot_url(self, get_system_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            jsonval = json.loads(f.read()).get("Default")
        type(
            get_system_mock.return_value.bios_settings).json = (
                mock.PropertyMock(return_value=jsonval))
        settings = jsonval.get('Attributes')
        expected_url_boot_file = settings.get('UrlBootFile')

        actual_url_boot_file = self.rf_client.get_http_boot_url()
        self.assertEqual(expected_url_boot_file, actual_url_boot_file)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_get_http_boot_url_fail(self, get_system_mock):
        bios_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(get_system_mock.return_value).bios_settings = bios_mock
        self.assertRaisesRegex(
            exception.IloError,
            'The attribute "UrlBootFile" not found.',
            self.rf_client.get_http_boot_url)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_http_boot_url_dhcp_default(self, system_mock):
        bios_ps_mock = mock.MagicMock(spec=bios.BIOSPendingSettings)
        pending_settings_mock = mock.PropertyMock(return_value=bios_ps_mock)
        type(system_mock.return_value.bios_settings).pending_settings = (
            pending_settings_mock)

        url = 'a.b.c'
        expected_parameter = {
            'PreBootNetwork': 'Auto',
            'UrlBootFile': 'a.b.c',
            'Dhcpv4': 'Enabled'
        }
        self.rf_client.set_http_boot_url(url)

        bios_ps_mock.update_bios_data_by_post.assert_called_once_with(
            expected_parameter)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_http_boot_url_dhcp_enabled(self, system_mock):
        bios_ps_mock = mock.MagicMock(spec=bios.BIOSPendingSettings)
        pending_settings_mock = mock.PropertyMock(return_value=bios_ps_mock)
        type(system_mock.return_value.bios_settings).pending_settings = (
            pending_settings_mock)

        dhcp_enabled = True
        url = 'a.b.c'
        expected_parameter = {
            'PreBootNetwork': 'Auto',
            'UrlBootFile': 'a.b.c',
            'Dhcpv4': 'Enabled'
        }
        self.rf_client.set_http_boot_url(url, dhcp_enabled)

        bios_ps_mock.update_bios_data_by_post.assert_called_once_with(
            expected_parameter)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_http_boot_url_dhcp_disabled(self, system_mock):
        bios_ps_mock = mock.MagicMock(spec=bios.BIOSPendingSettings)
        pending_settings_mock = mock.PropertyMock(return_value=bios_ps_mock)
        type(system_mock.return_value.bios_settings).pending_settings = (
            pending_settings_mock)

        dhcp_enabled = False
        url = 'a.b.c'
        expected_parameter = {
            'PreBootNetwork': 'Auto',
            'UrlBootFile': 'a.b.c',
            'Dhcpv4': 'Disabled'
        }
        self.rf_client.set_http_boot_url(url, dhcp_enabled)

        bios_ps_mock.update_bios_data_by_post.assert_called_once_with(
            expected_parameter)

    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_set_http_boot_url_raises_exception(self, system_mock):
        pending_settings_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)

        type(system_mock.return_value.bios_settings).pending_settings = (
            pending_settings_mock)

        dhcp_enabled = True
        url = 'a.b.c'
        self.assertRaisesRegex(
            exception.IloError,
            'Could not set HTTPS URL on the iLO.',
            self.rf_client.set_http_boot_url, url, dhcp_enabled)

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_add_tls_certificate_bios(self, get_sushy_system_mock,
                                      _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = False
        data = {
            "NewCertificates": [
                {
                    "X509Certificate": "Some data"
                }
            ]
        }

        self.assertRaisesRegex(
            exception.IloCommandNotSupportedInBiosError,
            'TLS certificate cannot be upload in BIOS boot mode',
            self.rf_client.add_tls_certificate,
            data)

    @mock.patch.object(builtins, 'open')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_add_tls_certificate(self, get_sushy_system_mock,
                                 _uefi_boot_mode_mock, open_mock):
        _uefi_boot_mode_mock.return_value = True
        data = (
            "-----BEGIN CERTIFICATE-----\nMIID7TC\nCF"
            "g879\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nKHY8UP\nGH"
            "f792\n-----END CERTIFICATE-----\n"
        )

        fd_mock = mock.MagicMock(spec=io.BytesIO)
        open_mock.return_value = fd_mock
        fd_mock.__enter__.return_value = fd_mock
        fd_mock.read.return_value = data
        c_l = [
            "-----BEGIN CERTIFICATE-----\r\nMIID7TC\r\nCF"
            "g879\r\n-----END CERTIFICATE-----",
            "-----BEGIN CERTIFICATE-----\r\nKHY8UP\r\nGH"
            "f792\r\n-----END CERTIFICATE-----"
        ]

        expected_data = {
            "NewCertificates": [
                {
                    "X509Certificate": c_l[0],
                },
                {
                    "X509Certificate": c_l[1],
                }
            ]
        }
        cert_file = '/path/to/certfile'

        self.rf_client.add_tls_certificate([cert_file])

        (get_sushy_system_mock.return_value.
         bios_settings.tls_config.tls_config_settings.
         add_tls_certificate.assert_called_once_with(expected_data))

    @mock.patch.object(builtins, 'open')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_add_tls_certificate_no_certificate(self, get_sushy_system_mock,
                                                _uefi_boot_mode_mock,
                                                open_mock):
        _uefi_boot_mode_mock.return_value = True
        data = (
            "-----UNFORMATED CERTIFICATE-----\nMIID7TC\nCF"
            "g879\n-----END CERTIFICATE-----\n"
            "-----UNFORMATED CERTIFICATE-----\nKHY8UP\nGH"
            "f792\n-----END CERTIFICATE-----\n"
        )

        fd_mock = mock.MagicMock(spec=io.BytesIO)
        open_mock.return_value = fd_mock
        fd_mock.__enter__.return_value = fd_mock
        fd_mock.read.return_value = data
        cert_file = "/path/to/certfile"

        self.assertRaisesRegex(
            exception.IloError,
            "No valid certificate",
            self.rf_client.add_tls_certificate, [cert_file])

        (get_sushy_system_mock.return_value.
         bios_settings.tls_config.tls_config_settings.
         add_tls_certificate.assert_not_called())

    @mock.patch.object(builtins, 'open')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_add_tls_certificate_raises_ilo_error(self, get_sushy_system_mock,
                                                  _uefi_boot_mode_mock,
                                                  open_mock):
        _uefi_boot_mode_mock.return_value = True

        data = (
            "-----BEGIN CERTIFICATE-----\nMIID7TC\nCF"
            "g879\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nKHY8UP\nGH"
            "f792\n-----END CERTIFICATE-----\n"
        )

        fd_mock = mock.MagicMock(spec=io.BytesIO)
        open_mock.return_value = fd_mock
        fd_mock.__enter__.return_value = fd_mock
        fd_mock.read.return_value = data

        cert_file = '/path/to/certfile'
        (get_sushy_system_mock.return_value.
         bios_settings.tls_config.tls_config_settings.
         add_tls_certificate.side_effect) = (
             sushy.exceptions.SushyError)

        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller has failed to upload TLS certificate.',
            self.rf_client.add_tls_certificate, [cert_file])

    @mock.patch.object(redfish, 'load_certificate')
    @mock.patch.object(redfish, 'b64decode')
    @mock.patch.object(builtins, 'open')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_remove_tls_certificate(self, get_sushy_system_mock,
                                    _uefi_boot_mode_mock, open_mock,
                                    decode_mock, load_cert_mock):
        _uefi_boot_mode_mock.return_value = True
        decode_mock.side_effect = ['first decoded data',
                                   'second decoded data']
        cert1_mock = mock.MagicMock()
        cert2_mock = mock.MagicMock()
        load_cert_mock.side_effect = [cert1_mock, cert2_mock]
        cert1_mock.digest.return_value.decode.return_value = "humptydumpty"
        cert2_mock.digest.return_value.decode.return_value = "hickerydickery"

        data = (
            "-----BEGIN CERTIFICATE-----\nMIID7TC\nCF"
            "g879\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nKHY8UP\nGH"
            "f792\n-----END CERTIFICATE-----\n"
        )

        fd_mock = mock.MagicMock(spec=io.BytesIO)
        open_mock.return_value = fd_mock
        fd_mock.__enter__.return_value = fd_mock
        fd_mock.read.return_value = data

        decode_calls = [
            mock.call('MIID7TCCFg879'),
            mock.call('KHY8UPGHf792')
        ]
        load_cert_calls = [
            mock.call(redfish.FILETYPE_ASN1, 'first decoded data'),
            mock.call(redfish.FILETYPE_ASN1, 'second decoded data')
        ]
        cert_file = '/path/to/certfile'
        self.rf_client.remove_tls_certificate([cert_file])
        decode_mock.assert_has_calls(decode_calls)
        load_cert_mock.assert_has_calls(load_cert_calls)

        expected_data = {
            "DeleteCertificates": [
                {
                    "FingerPrint": "humptydumpty",
                },
                {
                    "FingerPrint": "hickerydickery"
                }
            ]
        }

        (get_sushy_system_mock.return_value.
         bios_settings.tls_config.tls_config_settings.
         remove_tls_certificate.assert_called_once_with(expected_data))

    @mock.patch.object(redfish, 'load_certificate')
    @mock.patch.object(redfish, 'b64decode')
    @mock.patch.object(builtins, 'open')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_remove_tls_certificate_no_certificate(self,
                                                   get_sushy_system_mock,
                                                   _uefi_boot_mode_mock,
                                                   open_mock, decode_mock,
                                                   load_cert_mock):

        _uefi_boot_mode_mock.return_value = True

        data = (
            "-----UNFORMATED CERTIFICATE-----\nMIID7TC\nCF"
            "g879\n-----END CERTIFICATE-----\n"
            "-----UNFORMATED CERTIFICATE-----\nKHY8UP\nGH"
            "f792\n-----END CERTIFICATE-----\n"
        )

        fd_mock = mock.MagicMock(spec=io.BytesIO)
        open_mock.return_value = fd_mock
        fd_mock.__enter__.return_value = fd_mock
        fd_mock.read.return_value = data

        cert_file = '/path/to/certfile'

        self.assertRaisesRegex(
            exception.IloError,
            "No valid certificate",
            self.rf_client.remove_tls_certificate, [cert_file])

        decode_mock.assert_not_called()
        load_cert_mock.assert_not_called()

        (get_sushy_system_mock.return_value.
         bios_settings.tls_config.tls_config_settings.
         remove_tls_certificate.assert_not_called())

    @mock.patch.object(redfish, 'load_certificate')
    @mock.patch.object(redfish, 'b64decode')
    @mock.patch.object(builtins, 'open')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_remove_tls_certificate_raises_ilo_error(self,
                                                     get_sushy_system_mock,
                                                     _uefi_boot_mode_mock,
                                                     open_mock, decode_mock,
                                                     load_cert_mock):
        _uefi_boot_mode_mock.return_value = True
        decode_mock.side_effect = ['first decoded data',
                                   'second decoded data']
        cert1_mock = mock.MagicMock()
        cert2_mock = mock.MagicMock()
        load_cert_mock.side_effect = [cert1_mock, cert2_mock]
        cert1_mock.digest.return_value.decode.return_value = "humptydumpty"
        cert2_mock.digest.return_value.decode.return_value = "hickerydickery"

        data = (
            "-----BEGIN CERTIFICATE-----\nMIID7TC\nCF"
            "g879\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nKHY8UP\nGH"
            "f792\n-----END CERTIFICATE-----\n"
        )

        fd_mock = mock.MagicMock(spec=io.BytesIO)
        open_mock.return_value = fd_mock
        fd_mock.__enter__.return_value = fd_mock
        fd_mock.read.return_value = data

        cert_file = '/path/to/certfile'
        (get_sushy_system_mock.return_value.
         bios_settings.tls_config.tls_config_settings.
         remove_tls_certificate.side_effect) = (
             sushy.exceptions.SushyError)

        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller has failed to remove TLS certificate.',
            self.rf_client.remove_tls_certificate, [cert_file])

    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_remove_tls_certificate_bios(self, get_sushy_system_mock,
                                         _uefi_boot_mode_mock):
        _uefi_boot_mode_mock.return_value = False
        fp = ('FA:3A:68:C7:7E:ED:90:21:D2:FA:3E:54:6B:0C:14:D3:'
              '2F:8D:43:50:F7:05:A7:0F:1C:68:35:DB:5C:D2:53:28')

        self.assertRaisesRegex(
            exception.IloCommandNotSupportedInBiosError,
            'TLS certificates cannot be removed in BIOS boot mode',
            self.rf_client.remove_tls_certificate, fp)

    @mock.patch.object(redfish, 'load_certificate')
    @mock.patch.object(redfish, 'b64decode')
    @mock.patch.object(redfish.RedfishOperations, '_is_boot_mode_uefi')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_system')
    def test_remove_tls_certificate_default(self, get_sushy_system_mock,
                                            _uefi_boot_mode_mock, decode_mock,
                                            load_cert_mock):
        _uefi_boot_mode_mock.return_value = True
        with open('proliantutils/tests/redfish/'
                  'json_samples/tls_config.json', 'r') as f:
            jsonval = json.loads(f.read())
        tlsconfig_mock = mock.MagicMock(spec=tls_config.TLSConfig)

        tls_mock = mock.PropertyMock(return_value=tlsconfig_mock)

        type(get_sushy_system_mock.return_value.bios_settings).tls_config = (
            tls_mock)
        certificates = jsonval.get('Certificates')
        certs_mock = mock.PropertyMock(return_value=certificates)
        type(tlsconfig_mock).tls_certificates = certs_mock
        del_cert_list = []
        for cert in certificates:
            fp = cert.get("FingerPrint")
            cert_fp = {
                "FingerPrint": fp
            }
            del_cert_list.append(cert_fp)
        self.rf_client.remove_tls_certificate()
        (get_sushy_system_mock.return_value.
         bios_settings.tls_config.tls_config_settings.
         remove_tls_certificate.assert_called_once_with(
             {'DeleteCertificates': del_cert_list}))
        decode_mock.assert_not_called()
        load_cert_mock.assert_not_called()

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_update_password_complexity(self, account_mock, secure_mock):
        self.rf_client.update_password_complexity()
        (self.sushy.get_account_service.return_value.
         update_enforce_passwd_complexity.assert_called_once_with(True))

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_update_password_complexity_fail(self, account_mock,
                                             secure_mock):
        (self.sushy.get_account_service.return_value.
         update_enforce_passwd_complexity.
         side_effect) = sushy.exceptions.SushyError

        self.assertRaisesRegex(
            exception.IloError,
            'The Redfish controller failed to update the security dashboard '
            'parameter ``Password_Complexity``.',
            self.rf_client.update_password_complexity)

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_update_require_login_for_ilo_rbsu(self, manager_mock,
                                               secure_mock):
        self.rf_client.update_require_login_for_ilo_rbsu()
        (manager_mock.return_value.update_login_for_ilo_rbsu.
         assert_called_once_with(True))

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_update_require_login_for_ilo_rbsu_fail(self, manager_mock,
                                                    secure_mock):
        (manager_mock.return_value.update_login_for_ilo_rbsu.
         side_effect) = sushy.exceptions.SushyError

        msg = ("The Redfish controller failed to update the security dashboard"
               " parameter ``RequiredLoginForiLORBSU``.")
        self.assertRaisesRegex(
            exception.IloError, msg,
            self.rf_client.update_require_login_for_ilo_rbsu)

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_update_require_host_authentication(self, manager_mock,
                                                secure_mock):
        self.rf_client.update_require_host_authentication()
        (manager_mock.return_value.update_host_authentication.
         assert_called_once_with(True))

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_update_require_host_authentication_fail(self, manager_mock,
                                                     secure_mock):
        (manager_mock.return_value.update_host_authentication.
         side_effect) = sushy.exceptions.SushyError

        msg = ("The Redfish controller failed to update the "
               "security dashboard paramater ``RequireHostAuthentication``.")
        self.assertRaisesRegex(
            exception.IloError, msg,
            self.rf_client.update_require_host_authentication)

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_update_minimum_password_length(self, account_mock, secure_mock):
        self.rf_client.update_minimum_password_length(passwd_length=10)
        (self.sushy.get_account_service.return_value.
         update_min_passwd_length.assert_called_once_with(10))

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_update_minimum_password_length_fail(self, account_mock,
                                                 secure_mock):
        (self.sushy.get_account_service.return_value.
         update_min_passwd_length.side_effect) = sushy.exceptions.SushyError

        msg = ("The Redfish controller failed to update the "
               "security dashboard paramater ``MinPasswordLength``.")
        self.assertRaisesRegex(
            exception.IloError, msg,
            self.rf_client.update_minimum_password_length)

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_update_ipmi_over_lan(self, manager_mock, secure_mock):
        self.rf_client.update_ipmi_over_lan()
        (manager_mock.return_value.networkprotocol.return_value.
         update_ipmi_enabled(False))

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(redfish.RedfishOperations, '_get_sushy_manager')
    def test_update_ipmi_over_lan_fail(self, manager_mock, secure_mock):
        (manager_mock.return_value.networkprotocol.
         update_ipmi_enabled.side_effect) = sushy.exceptions.SushyError

        msg = ("The Redfish controller failed to update the "
               "security dashboard paramater ``IPMI/DCMI_Over_LAN``.")
        self.assertRaisesRegex(
            exception.IloError, msg, self.rf_client.update_ipmi_over_lan)

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_update_authentication_failure_logging(self, account_mock,
                                                   secure_mock):
        self.rf_client.update_authentication_failure_logging()
        (self.sushy.get_account_service.return_value.
         update_auth_failure_logging.assert_called_once_with(None))

    @mock.patch.object(redfish.RedfishOperations,
                       '_update_security_parameter')
    @mock.patch.object(main.HPESushy, 'get_account_service')
    def test_update_authentication_failure_logging_fail(self, account_mock,
                                                        secure_mock):
        (self.sushy.get_account_service.return_value.
         update_auth_failure_logging.
         side_effect) = sushy.exceptions.SushyError

        msg = ("The Redfish controller failed to update the security "
               "dashboard paramater ``Authentication_failure_Logging``.")
        self.assertRaisesRegex(
            exception.IloError, msg,
            self.rf_client.update_authentication_failure_logging)

    @mock.patch.object(redfish.RedfishOperations,
                       'get_security_dashboard_values')
    def test__parse_security_dashboard_values_for_capabilities(self, sec_mock):
        desc1 = ('The Require Login for iLO RBSU setting is disabled. '
                 'This configuration allows unauthenticated iLO access '
                 'through the UEFI System Utilities.')
        act1 = ('Enable the Require Login for iLO RBSU setting.')
        desc2 = ('The Password Complexity setting is disabled. This '
                 'configuration increases system vulnerability to attack.')
        act2 = ('Enable the "Password Complexity" setting.')
        desc3 = ('The UEFI Secure Boot setting is disabled. In this '
                 'configuration, the UEFI system firmware does not '
                 'validate the boot loader, Option ROM firmware, and '
                 'other system software executables for trusted signatures. '
                 'This configuration breaks the chain of trust established by '
                 'iLO from power-on')
        act3 = ('Enable the Secure Boot setting in the UEFI System Utilities.')
        s = {'server_configuration_lock_status': 'Disabled',
             'overall_security_status': 'Risk',
             'security_parameters':
             {'Require Host Authentication': {'ignore': False,
                                              'security_status': 'Ok',
                                              'state': 'Disabled'},
              'Last Firmware Scan Result': {'ignore': False,
                                            'security_status': 'Ok',
                                            'state': 'Ok'},
              'Require Login for iLO RBSU': {'ignore': False,
                                             'security_status': 'Risk',
                                             'description': desc1,
                                             'state': 'Disabled',
                                             'recommended_action': act1},
              'Authentication Failure Logging': {'ignore': False,
                                                 'security_status': 'Ok',
                                                 'state': 'Enabled'},
              'Password Complexity': {'ignore': False,
                                      'security_status': 'Risk',
                                      'description': desc2,
                                      'state': 'Disabled',
                                      'recommended_action': act2},
              'IPMI/DCMI Over LAN': {'ignore': False,
                                     'security_status': 'Ok',
                                     'state': 'Disabled'},
              'Security Override Switch': {'ignore': False,
                                           'security_status': 'Ok',
                                           'state': 'Off'},
              'Minimum Password Length': {'ignore': False,
                                          'security_status': 'Ok',
                                          'state': 'Ok'},
              'Secure Boot': {'ignore': False,
                              'security_status': 'Risk',
                              'description': desc3,
                              'state': 'Disabled',
                              'recommended_action': act3}}}
        sec_mock.return_value = s
        expected = {'last_firmware_scan_result': 'Ok',
                    'overall_security_status': 'Risk',
                    'security_override_switch': 'Ok'}
        actual = (
            self.rf_client._parse_security_dashboard_values_for_capabilities())
        self.assertEqual(expected, actual)
