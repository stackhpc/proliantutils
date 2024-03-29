# Copyright 2018-2022 Hewlett Packard Enterprise Development LP
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
from unittest import mock

import sushy
from sushy.resources.system import system as sushy_system
import testtools

from proliantutils import exception
from proliantutils.redfish.resources.system import bios
from proliantutils.redfish.resources.system import constants as sys_cons
from proliantutils.redfish.resources.system import ethernet_interface
from proliantutils.redfish.resources.system import memory
from proliantutils.redfish.resources.system import secure_boot
from proliantutils.redfish.resources.system import smart_storage_config
from proliantutils.redfish.resources.system.storage import array_controller
from proliantutils.redfish.resources.system.storage import simple_storage
from proliantutils.redfish.resources.system.storage import smart_storage
from proliantutils.redfish.resources.system.storage import storage
from proliantutils.redfish.resources.system import system
from proliantutils.redfish import utils


class HPESystemTestCase(testtools.TestCase):

    def setUp(self):
        super(HPESystemTestCase, self).setUp()
        self.conn = mock.MagicMock()
        self.conn.get.return_value.headers = {'Allow': 'GET,HEAD'}
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        self.conn.get.return_value.json.return_value = system_json['default']

        self.sys_inst = system.HPESystem(
            self.conn, '/redfish/v1/Systems/1',
            redfish_version='1.0.2')

    def test_attributes(self):
        self.assertEqual(sys_cons.SUPPORTED_LEGACY_BIOS_AND_UEFI,
                         self.sys_inst.supported_boot_mode)

    def test__get_hpe_one_button_secure_erase_action_element(self):
        value = self.sys_inst._get_hpe_one_button_secure_erase_action_element()
        self.assertEqual("/redfish/v1/Systems/1/Actions/Oem/Hpe/"
                         "HpeComputerSystemExt.SecureSystemErase",
                         value.target_uri)

    def test__get_hpe_one_button_secure_erase_action_element_missing_action(
            self):
        (self.sys_inst._hpe_actions.
         computer_system_ext_one_button_secure_erase) = None
        self.assertRaisesRegex(
            exception.MissingAttributeError,
            'Oem/Hpe/Actions/#HpeComputerSystemExt.SecureSystemErase is '
            'missing',
            self.sys_inst._get_hpe_one_button_secure_erase_action_element)

    def test__get_hpe_push_power_button_action_element(self):
        value = self.sys_inst._get_hpe_push_power_button_action_element()
        self.assertEqual("/redfish/v1/Systems/1/Actions/Oem/Hpe/"
                         "HpeComputerSystemExt.PowerButton/",
                         value.target_uri)
        self.assertEqual(["Press", "PressAndHold"], value.allowed_values)

    def test__get_hpe_push_power_button_action_element_missing_action(self):
        self.sys_inst._hpe_actions.computer_system_ext_powerbutton = None
        self.assertRaisesRegex(
            exception.MissingAttributeError,
            'Oem/Hpe/Actions/#HpeComputerSystemExt.PowerButton is missing',
            self.sys_inst._get_hpe_push_power_button_action_element)

    def test_push_power_button(self):
        self.sys_inst.push_power_button(
            sys_cons.PUSH_POWER_BUTTON_PRESS)
        self.sys_inst._conn.post.assert_called_once_with(
            '/redfish/v1/Systems/1/Actions/Oem/Hpe/'
            'HpeComputerSystemExt.PowerButton/',
            data={'PushType': 'Press'})

    def test_push_power_button_invalid_value(self):
        self.assertRaises(exception.InvalidInputError,
                          self.sys_inst.push_power_button, 'invalid-value')

    def test_bios_settings(self):
        self.conn.get.return_value.json.reset_mock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        actual_bios = self.sys_inst.bios_settings
        self.assertIsInstance(actual_bios,
                              bios.BIOSSettings)
        self.conn.get.return_value.json.assert_called_once_with()
        # reset mock
        self.conn.get.return_value.json.reset_mock()
        self.assertIs(actual_bios,
                      self.sys_inst.bios_settings)
        self.conn.get.return_value.json.assert_not_called()

    @mock.patch.object(sushy_system.System, 'set_system_boot_source')
    def test_update_persistent_boot_persistent(self,
                                               set_system_boot_source_mock):
        self.sys_inst.update_persistent_boot(['CDROM'], persistent=True)
        set_system_boot_source_mock.assert_called_once_with(
            sushy.BOOT_SOURCE_TARGET_CD,
            enabled=sushy.BOOT_SOURCE_ENABLED_CONTINUOUS)

    @mock.patch.object(sushy_system.System, 'set_system_boot_source')
    def test_update_persistent_boot_device_unknown_persistent(
            self, set_system_boot_source_mock):
        self.sys_inst.update_persistent_boot(['unknown'], persistent=True)
        set_system_boot_source_mock.assert_called_once_with(
            sushy.BOOT_SOURCE_TARGET_NONE,
            enabled=sushy.BOOT_SOURCE_ENABLED_CONTINUOUS)

    @mock.patch.object(sushy_system.System, 'set_system_boot_source')
    def test_update_persistent_boot_not_persistent(
            self, set_system_boot_source_mock):
        self.sys_inst.update_persistent_boot(['CDROM'], persistent=False)
        set_system_boot_source_mock.assert_called_once_with(
            sushy.BOOT_SOURCE_TARGET_CD,
            enabled=sushy.BOOT_SOURCE_ENABLED_ONCE)

    def test_bios_settings_on_refresh(self):
        # | GIVEN |
        with open('proliantutils/tests/redfish/json_samples/bios.json',
                  'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        # | WHEN & THEN |
        actual_bios_settings = self.sys_inst.bios_settings
        self.assertIsInstance(actual_bios_settings,
                              bios.BIOSSettings)

        # On refreshing the system instance...
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])

        self.sys_inst.invalidate()
        self.sys_inst.refresh(force=False)

        # | WHEN & THEN |
        self.assertTrue(actual_bios_settings._is_stale)

        # | GIVEN |
        with open('proliantutils/tests/redfish/json_samples/bios.json',
                  'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        # | WHEN & THEN |
        self.assertIsInstance(self.sys_inst.bios_settings,
                              bios.BIOSSettings)
        self.assertFalse(actual_bios_settings._is_stale)

    def test_update_persistent_boot_uefi_target(self):
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = (json.loads(f.read())[
                'System_op_for_update_persistent_boot_uefi_target'])
        self.sys_inst.uefi_target_override_devices = (system_json[
            'Boot']['UefiTargetBootSourceOverride@Redfish.AllowableValues'])
        self.sys_inst.update_persistent_boot(['ISCSI'], persistent=True)
        uefi_boot_settings = {
            'Boot': {'UefiTargetBootSourceOverride': 'PciRoot(0x0)/Pci(0x1C,0x0)/Pci(0x0,0x0)/MAC(98F2B3EEF886,0x0)/IPv4(172.17.1.32)/iSCSI(iqn.2001-04.com.paresh.boot:volume.bin,0x1,0x0,None,None,None,TCP)'}  # noqa
        }

        calls = [mock.call('/redfish/v1/Systems/1', data=uefi_boot_settings),
                 mock.call('/redfish/v1/Systems/1',
                           data={'Boot':
                                 {'BootSourceOverrideTarget': 'UefiTarget',
                                  'BootSourceOverrideEnabled': 'Continuous'}},
                           etag=None)]
        self.sys_inst._conn.patch.assert_has_calls(calls)

    def test_update_persistent_boot_uefi_no_iscsi_device(self):
        self.assertRaisesRegex(
            exception.IloError,
            'No UEFI iSCSI bootable device found on system.',
            self.sys_inst.update_persistent_boot, ['ISCSI'], True)

    def test_update_persistent_boot_uefi_target_fail(self):
        update_mock = mock.PropertyMock(
            side_effect=sushy.exceptions.SushyError)
        type(self.sys_inst).uefi_target_override_devices = update_mock
        self.assertRaisesRegex(
            exception.IloError,
            'Unable to get uefi target override devices.',
            self.sys_inst.update_persistent_boot, ['ISCSI'], True)
        del type(self.sys_inst).uefi_target_override_devices

    def test_pci_devices(self):
        pci_dev_return_value = None
        pci_dev1_return_value = None
        pci_coll_return_value = None
        self.conn.get.return_value.json.reset_mock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/pci_device_collection.json') as f:
            pci_coll_return_value = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/pci_device.json') as f:
            pci_dev_return_value = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/pci_device1.json') as f:
            pci_dev1_return_value = json.loads(f.read())
            self.conn.get.return_value.json.side_effect = (
                [pci_coll_return_value, pci_dev_return_value,
                 pci_dev1_return_value])
        actual_pci = self.sys_inst.pci_devices
        self.conn.get.return_value.json.reset_mock()
        self.assertIs(actual_pci,
                      self.sys_inst.pci_devices)
        self.conn.get.return_value.json.assert_not_called()

    def test_secure_boot_with_missing_path_attr(self):
        def _get_secure_boot():
            return self.sys_inst.secure_boot

        self.sys_inst._json.pop('SecureBoot')
        self.assertRaisesRegex(
            exception.MissingAttributeError,
            'attribute SecureBoot is missing',
            _get_secure_boot)

    def test_secure_boot(self):
        # | GIVEN |
        self.conn.get.return_value.json.reset_mock()
        with open('proliantutils/tests/redfish/json_samples/secure_boot.json',
                  'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])
        # | WHEN |
        actual_secure_boot = self.sys_inst.secure_boot
        # | THEN |
        self.assertIsInstance(actual_secure_boot,
                              secure_boot.SecureBoot)
        self.conn.get.return_value.json.assert_called_once_with()

        # reset mock
        self.conn.get.return_value.json.reset_mock()
        # | WHEN & THEN |
        # tests for same object on invoking subsequently
        self.assertIs(actual_secure_boot,
                      self.sys_inst.secure_boot)
        self.conn.get.return_value.json.assert_not_called()

    def test_secure_boot_on_refresh(self):
        # | GIVEN |
        with open('proliantutils/tests/redfish/json_samples/secure_boot.json',
                  'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])
        # | WHEN & THEN |
        actual_secure_boot = self.sys_inst.secure_boot
        self.assertIsInstance(actual_secure_boot, secure_boot.SecureBoot)

        # On refreshing the system instance...
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])

        self.sys_inst.invalidate()
        self.sys_inst.refresh(force=False)

        # | WHEN & THEN |
        self.assertTrue(actual_secure_boot._is_stale)

        # | GIVEN |
        with open('proliantutils/tests/redfish/json_samples/secure_boot.json',
                  'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])
        # | WHEN & THEN |
        self.assertIsInstance(self.sys_inst.secure_boot,
                              secure_boot.SecureBoot)
        self.assertFalse(actual_secure_boot._is_stale)

    @mock.patch.object(utils, 'get_subresource_path_by')
    def test_get_hpe_sub_resource_collection_path(self, res_mock):
        res = 'EthernetInterfaces'
        res_mock.return_value = '/redfish/v1/Systems/1/EthernetInterfaces'
        path = self.sys_inst._get_hpe_sub_resource_collection_path(res)
        self.assertTrue(res_mock.called)
        self.assertEqual(path, res_mock.return_value)

    @mock.patch.object(utils, 'get_subresource_path_by')
    def test_get_hpe_sub_resource_collection_path_oem_path(self, res_mock):
        res = 'EthernetInterfaces'
        error_val = exception.MissingAttributeError
        oem_path = '/redfish/v1/Systems/1/EthernetInterfaces'
        res_mock.side_effect = [error_val, oem_path]
        path = self.sys_inst._get_hpe_sub_resource_collection_path(res)
        self.assertTrue(res_mock.called)
        self.assertEqual(path, oem_path)

    @mock.patch.object(utils, 'get_subresource_path_by')
    def test_get_hpe_sub_resource_collection_path_fail(self, res_mock):
        error_val = exception.MissingAttributeError
        res_mock.side_effect = [error_val, error_val]
        self.assertRaises(
            exception.MissingAttributeError,
            self.sys_inst._get_hpe_sub_resource_collection_path,
            'EthernetInterfaces')
        self.assertTrue(res_mock.called)

    def test_ethernet_interfaces(self):
        self.conn.get.return_value.json.reset_mock()
        eth_coll = None
        eth_value = None
        path = ('proliantutils/tests/redfish/json_samples/'
                'ethernet_interface_collection.json')
        with open(path, 'r') as f:
            eth_coll = json.loads(f.read())
        with open('proliantutils/tests/redfish/json_samples/'
                  'ethernet_interface.json', 'r') as f:
            eth_value = (json.loads(f.read())['default'])
        self.conn.get.return_value.json.side_effect = [eth_coll,
                                                       eth_value]
        actual_macs = self.sys_inst.ethernet_interfaces.summary
        self.assertEqual({'Port 1': '12:44:6A:3B:04:11'},
                         actual_macs)
        self.assertIsInstance(self.sys_inst.ethernet_interfaces,
                              ethernet_interface.EthernetInterfaceCollection)

    def test_ethernet_interfaces_oem(self):
        self.conn = mock.MagicMock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            system_json = json.loads(f.read())
        self.conn.get.return_value.json.return_value = (
            system_json['System_for_oem_ethernet_interfaces'])

        self.sys_inst = system.HPESystem(
            self.conn, '/redfish/v1/Systems/1',
            redfish_version='1.0.2')

        self.conn.get.return_value.json.reset_mock()
        eth_coll = None
        eth_value = None
        path = ('proliantutils/tests/redfish/json_samples/'
                'ethernet_interface_collection.json')
        with open(path, 'r') as f:
            eth_coll = json.loads(f.read())
        with open('proliantutils/tests/redfish/json_samples/'
                  'ethernet_interface.json', 'r') as f:
            eth_value = (json.loads(f.read())['default'])
        self.conn.get.return_value.json.side_effect = [eth_coll,
                                                       eth_value]
        actual_macs = self.sys_inst.ethernet_interfaces.summary
        self.assertEqual({'Port 1': '12:44:6A:3B:04:11'},
                         actual_macs)
        self.assertIsInstance(self.sys_inst.ethernet_interfaces,
                              ethernet_interface.EthernetInterfaceCollection)

    def test_smart_storage(self):
        self.conn.get.return_value.json.reset_mock()
        value = None
        with open('proliantutils/tests/redfish/json_samples/'
                  'smart_storage.json', 'r') as f:
            value = (json.loads(f.read()))
        self.conn.get.return_value.json.return_value = value
        value = self.sys_inst.smart_storage
        self.assertIsInstance(value, smart_storage.HPESmartStorage)

    def test_storages(self):
        self.conn.get.return_value.json.reset_mock()
        coll = None
        value = None
        path = ('proliantutils/tests/redfish/json_samples/'
                'storage_collection.json')
        with open(path, 'r') as f:
            coll = json.loads(f.read())
        with open('proliantutils/tests/redfish/json_samples/'
                  'storage.json', 'r') as f:
            value = (json.loads(f.read()))
        self.conn.get.return_value.json.side_effect = [coll, value]
        self.assertIsInstance(self.sys_inst.storages,
                              storage.StorageCollection)

    def test_simple_storages(self):
        self.conn.get.return_value.json.reset_mock()
        coll = None
        value = None
        path = ('proliantutils/tests/redfish/json_samples/'
                'simple_storage_collection.json')
        with open(path, 'r') as f:
            coll = json.loads(f.read())
        with open('proliantutils/tests/redfish/json_samples/'
                  'simple_storage.json', 'r') as f:
            value = (json.loads(f.read()))
        self.conn.get.return_value.json.side_effect = [coll, value]
        self.assertIsInstance(self.sys_inst.simple_storages,
                              simple_storage.SimpleStorageCollection)

    def test_simple_storage_on_refresh(self):
        with open('proliantutils/tests/redfish/json_samples/'
                  'simple_storage_collection.json',
                  'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        actual_simple_storages = self.sys_inst.simple_storages
        self.assertIsInstance(actual_simple_storages,
                              simple_storage.SimpleStorageCollection)
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])

        self.sys_inst.invalidate()
        self.sys_inst.refresh(force=False)

        self.assertTrue(actual_simple_storages._is_stale)

        with open('proliantutils/tests/redfish/json_samples/'
                  'simple_storage_collection.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        self.assertIsInstance(self.sys_inst.simple_storages,
                              simple_storage.SimpleStorageCollection)
        self.assertFalse(actual_simple_storages._is_stale)

    def test_memory(self):
        self.conn.get.return_value.json.reset_mock()
        with open('proliantutils/tests/redfish/'
                  'json_samples/memory_collection.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        actual_memory = self.sys_inst.memory
        self.assertIsInstance(actual_memory,
                              memory.MemoryCollection)
        self.conn.get.return_value.json.assert_called_once_with()
        # reset mock
        self.conn.get.return_value.json.reset_mock()
        self.assertIs(actual_memory,
                      self.sys_inst.memory)
        self.conn.get.return_value.json.assert_not_called()

    def test_memory_collection_on_refresh(self):
        # | GIVEN |
        with open('proliantutils/tests/redfish/json_samples/'
                  'memory_collection.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        # | WHEN & THEN |
        actual_memory = self.sys_inst.memory
        self.assertIsInstance(actual_memory, memory.MemoryCollection)

        # On refreshing the system instance...
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])

        self.sys_inst.invalidate()
        self.sys_inst.refresh(force=False)

        # | WHEN & THEN |
        self.assertTrue(actual_memory._is_stale)

        # | GIVEN |
        with open('proliantutils/tests/redfish/json_samples/'
                  'memory_collection.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        # | WHEN & THEN |
        self.assertIsInstance(self.sys_inst.memory,
                              memory.MemoryCollection)
        self.assertFalse(actual_memory._is_stale)

    def test_storage_on_refresh(self):
        with open('proliantutils/tests/redfish/json_samples/'
                  'storage_collection.json',
                  'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        actual_storages = self.sys_inst.storages
        self.assertIsInstance(actual_storages, storage.StorageCollection)
        # On refreshing the system instance...
        with open('proliantutils/tests/redfish/'
                  'json_samples/system.json', 'r') as f:
            self.conn.get.return_value.json.return_value = (
                json.loads(f.read())['default'])

        self.sys_inst.invalidate()
        self.sys_inst.refresh(force=False)

        self.assertTrue(actual_storages._is_stale)

        with open('proliantutils/tests/redfish/json_samples/'
                  'simple_storage_collection.json', 'r') as f:
            self.conn.get.return_value.json.return_value = json.loads(f.read())
        self.assertIsInstance(self.sys_inst.storages,
                              storage.StorageCollection)
        self.assertFalse(actual_storages._is_stale)

    def test_get_host_post_state(self):
        expected = sys_cons.POST_STATE_FINISHEDPOST
        self.assertEqual(expected, self.sys_inst.post_state)

    @mock.patch.object(smart_storage_config, 'HPESmartStorageConfig',
                       autospec=True)
    def test_get_smart_storage_config(self, mock_ssc):
        ssc_element = '/redfish/v1/systems/1/smartstorageconfig/'
        ssc_inst = self.sys_inst.get_smart_storage_config(ssc_element)
        self.assertIsInstance(ssc_inst,
                              smart_storage_config.HPESmartStorageConfig.
                              __class__)
        mock_ssc.assert_called_once_with(
            self.conn, "/redfish/v1/systems/1/smartstorageconfig/",
            redfish_version='1.0.2')

    @mock.patch.object(system.HPESystem, 'get_smart_storage_config')
    def test_delete_raid(self, get_smart_storage_config_mock):
        config_id = ['/redfish/v1/systems/1/smartstorageconfig/']
        type(self.sys_inst).smart_storage_config_identities = (
            mock.PropertyMock(return_value=config_id))
        self.sys_inst.delete_raid()
        get_smart_storage_config_mock.assert_called_once_with(config_id[0])
        (get_smart_storage_config_mock.return_value.
         delete_raid.assert_called_once_with())

    @mock.patch.object(system.HPESystem, 'get_smart_storage_config')
    def test_delete_raid_controller_failed(self,
                                           get_smart_storage_config_mock):
        config_id = ['/redfish/v1/systems/1/smartstorageconfig/',
                     '/redfish/v1/systems/1/smartstorageconfig1/',
                     '/redfish/v1/systems/1/smartstorageconfig2/']
        type(self.sys_inst).smart_storage_config_identities = (
            mock.PropertyMock(return_value=config_id))
        get_smart_storage_config_mock.return_value.delete_raid.side_effect = (
            [None, sushy.exceptions.SushyError, None])
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to delete the "
            "raid configuration in one or more controllers with",
            self.sys_inst.delete_raid)

    @mock.patch.object(system.HPESystem, 'get_smart_storage_config')
    def test_delete_raid_logical_drive_not_found(
            self, get_smart_storage_config_mock):
        config_id = ['/redfish/v1/systems/1/smartstorageconfig/',
                     '/redfish/v1/systems/1/smartstorageconfig1/']
        type(self.sys_inst).smart_storage_config_identities = (
            mock.PropertyMock(return_value=config_id))
        get_smart_storage_config_mock.return_value.delete_raid.side_effect = (
            exception.IloLogicalDriveNotFoundError('No logical drive found'))
        self.assertRaisesRegex(
            exception.IloError,
            "No logical drives are found in any controllers. "
            "Nothing to delete.",
            self.sys_inst.delete_raid)

    def test_check_smart_storage_config_ids(self):
        type(self.sys_inst).smart_storage_config_identities = (
            mock.PropertyMock(return_value=None))
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to get the SmartStorageConfig "
            "controller configurations",
            self.sys_inst.check_smart_storage_config_ids)

    @mock.patch.object(system.HPESystem, 'check_smart_storage_config_ids')
    @mock.patch.object(system.HPESystem, '_parse_raid_config_data')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    def test_create_raid(self, get_smart_storage_config_model_mock,
                         parse_raid_config_mock,
                         check_smart_storage_config_ids_mock):
        ld1 = {'raid_level': '0', 'is_root_volume': True,
               'size_gb': 150,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        ld2 = {'raid_level': '1', 'size_gb': 200,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        raid_config = {'logical_disks': [ld1, ld2]}
        parse_data = {'HPE Smart Array P408i-p SR Gen10': [ld1, ld2]}
        parse_raid_config_mock.return_value = parse_data
        check_smart_storage_config_ids_mock.return_value = None
        self.sys_inst.create_raid(raid_config)
        get_smart_storage_config_model_mock.assert_called_once_with(
            'HPE Smart Array P408i-p SR Gen10')
        (get_smart_storage_config_model_mock.return_value.
         create_raid.assert_called_once_with(raid_config))

    @mock.patch.object(system.HPESystem, 'check_smart_storage_config_ids')
    @mock.patch.object(system.HPESystem, '_parse_raid_config_data')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    def test_create_raid_controller_not_found(
            self, get_smart_storage_config_model_mock, parse_raid_config_mock,
            check_smart_storage_config_ids_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller.json', 'r') as f:
            ac_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [
            ss_json, acc_json, ac_json]
        ld1 = {'raid_level': '1', 'size_gb': 200,
               'controller': 'HPE Gen10 Controller'}
        raid_config = {'logical_disks': [ld1]}
        parse_data = {'HPE Gen10 Controller': [ld1]}
        parse_raid_config_mock.return_value = parse_data
        check_smart_storage_config_ids_mock.return_value = None
        get_smart_storage_config_model_mock.return_value = None
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to create the raid "
            "configuration for one or more controllers with",
            self.sys_inst.create_raid, raid_config)

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_location')
    @mock.patch.object(system.HPESystem, 'get_smart_storage_config')
    def test__post_delete_read_raid(
            self, get_smart_storage_config_mock,
            array_controller_by_location_mock):
        config_id = ['/redfish/v1/systems/1/smartstorageconfig/']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        type(get_smart_storage_config_mock.return_value).location = 'Slot 0'
        model = 'HPE Smart Array P408i-a SR Gen10'
        type(array_controller_by_location_mock.return_value).model = model
        type(self.sys_inst).smart_storage_config_identities = (
            mock.PropertyMock(return_value=config_id))
        result = {'logical_disks': []}
        (get_smart_storage_config_mock.
         return_value.read_raid.return_value) = result
        self.assertEqual(result, self.sys_inst._post_delete_read_raid())
        get_smart_storage_config_mock.assert_called_once_with(config_id[0])

    @mock.patch.object(system.HPESystem, '_parse_raid_config_data')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    def test__post_create_read_raid(
            self, get_ssc_by_controller_model_mock,
            parse_raid_config_data_mock):
        ld1 = {'raid_level': '0', 'is_root_volume': True,
               'size_gb': 150,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        raid_config = {'logical_disks': [ld1]}
        parse_data = {'HPE Smart Array P408i-p SR Gen10': [ld1]}
        parse_raid_config_data_mock.return_value = parse_data
        result_ld1 = [{'size_gb': 149,
                       'physical_disks': [u'2I:1:1'],
                       'raid_level': u'0',
                       'controller': 'HPE Smart Array P408i-p SR Gen10',
                       'root_device_hint': {'wwn': u'0x600508B'},
                       'volume_name': u'01E6E63APFJHD'}]
        result = {'logical_disks': result_ld1}
        (get_ssc_by_controller_model_mock.
         return_value.read_raid.return_value) = result
        self.assertEqual(
            result,
            self.sys_inst._post_create_read_raid(raid_config=raid_config))
        get_ssc_by_controller_model_mock.assert_called_once_with(
            ld1['controller'])

    @mock.patch.object(system.HPESystem, '_parse_raid_config_data')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    def test__post_create_read_raid_logical_drive_not_found(
            self, get_ssc_by_controller_model_mock,
            parse_raid_config_data_mock):
        ld1 = {'raid_level': '0', 'is_root_volume': True,
               'size_gb': 150,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        raid_config = {'logical_disks': [ld1]}
        parse_data = {'HPE Smart Array P408i-p SR Gen10': [ld1]}
        parse_raid_config_data_mock.return_value = parse_data
        get_ssc_by_controller_model_mock.return_value.read_raid.side_effect = (
            exception.IloLogicalDriveNotFoundError('No logical drive found'))
        self.assertRaisesRegex(
            exception.IloError,
            "No logical drives are found in any controllers.",
            self.sys_inst._post_create_read_raid, raid_config)

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_location')
    @mock.patch.object(system.HPESystem, 'get_smart_storage_config')
    def test__post_delete_read_raid_failed(
            self, get_smart_storage_config_mock,
            array_controller_by_location_mock):
        config_id = ['/redfish/v1/systems/1/smartstorageconfig/']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        model = 'HPE Smart Array P408i-a SR Gen10'
        type(array_controller_by_location_mock.return_value).model = model
        type(self.sys_inst).smart_storage_config_identities = (
            mock.PropertyMock(return_value=config_id))
        get_smart_storage_config_mock.return_value.read_raid.side_effect = (
            sushy.exceptions.SushyError)
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to read the "
            "raid configuration in one or more controllers with Error:",
            self.sys_inst._post_delete_read_raid)

    @mock.patch.object(system.HPESystem, 'check_smart_storage_config_ids')
    @mock.patch.object(system.HPESystem, '_parse_raid_config_data')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    def test_create_raid_failed(self, get_smart_storage_config_model_mock,
                                parse_raid_config_mock,
                                check_smart_storage_config_ids_mock):
        ld1 = {'raid_level': '0', 'is_root_volume': True,
               'size_gb': 150,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        ld2 = {'raid_level': '1', 'size_gb': 200,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        raid_config = {'logical_disks': [ld1, ld2]}
        parse_data = {'HPE Smart Array P408i-p SR Gen10': [ld1, ld2]}
        check_smart_storage_config_ids_mock.return_value = None
        parse_raid_config_mock.return_value = parse_data
        (get_smart_storage_config_model_mock.
         return_value.create_raid.side_effect) = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to create the "
            "raid configuration for one or more controllers with Error:",
            self.sys_inst.create_raid, raid_config)

    def test__parse_raid_config_data(self):
        ld1 = {'raid_level': '0', 'is_root_volume': True,
               'size_gb': 150,
               'controller': 'HPE Smart Array P408i-a SR Gen10'}
        ld2 = {'raid_level': '1', 'size_gb': 200,
               'controller': 'HPE Smart Array P408i-a SR Gen10'}
        raid_config = {'logical_disks': [ld1, ld2]}
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller.json', 'r') as f:
            ac_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [
            ss_json, acc_json, ac_json]
        expected = {'HPE Smart Array P408i-a SR Gen10': [ld1, ld2]}
        self.assertEqual(expected,
                         self.sys_inst._parse_raid_config_data(raid_config))

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    @mock.patch.object(system.HPESystem, 'get_smart_storage_config')
    def test__get_smart_storage_config_by_controller_model(
            self, get_smart_storage_config_mock,
            array_controller_by_model_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        type(array_controller_by_model_mock.return_value).location = 'Slot 0'
        type(get_smart_storage_config_mock.return_value).location = 'Slot 0'
        self.assertEqual(
            'Slot 0',
            self.sys_inst._get_smart_storage_config_by_controller_model(
                'HPE Smart Array P408i-a SR Gen10').location)

    @mock.patch.object(system.HPESystem, '_parse_raid_config_data')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    def test__post_create_read_raid_failed_with_raid_config(
            self, get_ssc_by_controller_model_mock,
            parse_raid_config_data_mock):
        ld1 = {'raid_level': '0', 'is_root_volume': True,
               'size_gb': 150,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        raid_config = {'logical_disks': [ld1]}
        parse_data = {'HPE Smart Array P408i-p SR Gen10': [ld1]}
        parse_raid_config_data_mock.return_value = parse_data
        (get_ssc_by_controller_model_mock.
         return_value.read_raid.side_effect) = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to read the "
            "raid configuration in one or more controllers with Error:",
            self.sys_inst._post_create_read_raid, raid_config=raid_config)

    @mock.patch.object(system.HPESystem, '_post_create_read_raid')
    @mock.patch.object(system.HPESystem, 'check_smart_storage_config_ids')
    def test_read_raid_post_create(
            self, check_smart_storage_config_ids_mock,
            post_create_read_raid_mock):
        check_smart_storage_config_ids_mock.return_value = None
        ld1 = {'raid_level': '0', 'is_root_volume': True,
               'size_gb': 150,
               'controller': 'HPE Smart Array P408i-p SR Gen10'}
        raid_config = {'logical_disks': [ld1]}
        result_ld1 = [{'size_gb': 149,
                       'physical_disks': [u'2I:1:1'],
                       'raid_level': u'0',
                       'controller': 'HPE Smart Array P408i-p SR Gen10',
                       'root_device_hint': {'wwn': u'0x600508B'},
                       'volume_name': u'01E6E63APFJHD'}]
        result = {'logical_disks': result_ld1}
        post_create_read_raid_mock.return_value = result
        self.assertEqual(
            result, self.sys_inst.read_raid(raid_config=raid_config))

    @mock.patch.object(system.HPESystem, '_post_delete_read_raid')
    @mock.patch.object(system.HPESystem, 'check_smart_storage_config_ids')
    def test_read_raid_post_delete(
            self, check_smart_storage_config_ids_mock,
            post_delete_read_raid_mock):
        check_smart_storage_config_ids_mock.return_value = None
        result = {'logical_disks': []}
        post_delete_read_raid_mock.return_value = result
        self.assertEqual(
            result, self.sys_inst.read_raid())

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test_has_disk_erase_completed_true(
            self, array_controller_by_model_mock,
            get_all_controllers_model_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        type(array_controller_by_model_mock.
             return_value.physical_drives).has_disk_erase_completed = True
        self.assertEqual(True, self.sys_inst.has_disk_erase_completed())

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test_has_disk_erase_completed_false(
            self, array_controller_by_model_mock,
            get_all_controllers_model_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        type(array_controller_by_model_mock.
             return_value.physical_drives).has_disk_erase_completed = False
        self.assertEqual(False, self.sys_inst.has_disk_erase_completed())

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test_has_disk_erase_completed_failed(
            self, array_controller_by_model_mock,
            get_all_controllers_model_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        (self.conn.get.return_value.
         json.side_effect) = [ss_json, sushy.exceptions.SushyError]
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to get the status of sanitize disk "
            "erase. Error:",
            self.sys_inst.has_disk_erase_completed)

    @mock.patch.object(system.HPESystem,
                       '_get_hpe_one_button_secure_erase_action_element')
    def test_do_one_button_secure_erase(
            self, secure_erase_action_mock):
        target_uri = (
            '/redfish/v1/Systems/1/Actions/Oem/Hpe/'
            '#HpeComputerSystemExt.SecureSystemErase')
        data = {
            "SystemROMAndiLOErase": True,
            "UserDataErase": True}
        type(secure_erase_action_mock.return_value).target_uri = target_uri
        self.sys_inst.do_one_button_secure_erase()
        self.sys_inst._conn.post.assert_called_once_with(target_uri, data=data)

    @mock.patch.object(system.HPESystem,
                       '_get_hpe_one_button_secure_erase_action_element')
    def test_do_one_button_secure_erase_failed(
            self, secure_erase_action_mock):
        target_uri = (
            '/redfish/v1/Systems/1/Actions/Oem/Hpe/'
            '#HpeComputerSystemExt.SecureSystemErase')
        type(secure_erase_action_mock.return_value).target_uri = target_uri
        self.sys_inst._conn.post.side_effect = sushy.exceptions.SushyError
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to perform one button "
            "secure erase operation on the hardware. Error:",
            self.sys_inst.do_one_button_secure_erase)

    @mock.patch.object(system.HPESystem,
                       '_get_drives_has_raid')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test_do_disk_erase_hdd(
            self, array_controller_by_model_mock,
            get_ssc_by_controller_model_mock,
            get_all_controllers_model_mock,
            drives_raid_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        drives_raid_mock.return_value = []
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        (array_controller_by_model_mock.return_value.physical_drives.
         get_all_hdd_drives_locations.return_value) = ['2I:1:1']
        self.sys_inst.do_disk_erase('HDD', None)
        get_ssc_by_controller_model_mock.assert_called_once_with(
            'HPE Smart Array P408i-p SR Gen10')
        (get_ssc_by_controller_model_mock.return_value.
         disk_erase.assert_called_once_with(['2I:1:1'], 'HDD', None))

    @mock.patch.object(system.HPESystem,
                       '_get_drives_has_raid')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test_do_disk_erase_ssd(
            self, array_controller_by_model_mock,
            get_ssc_by_controller_model_mock,
            get_all_controllers_model_mock,
            drives_raid_mock):
        drives_raid_mock.return_value = []
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        (array_controller_by_model_mock.return_value.physical_drives.
         get_all_ssd_drives_locations.return_value) = ['2I:1:1']
        self.sys_inst.do_disk_erase('SSD', None)
        get_ssc_by_controller_model_mock.assert_called_once_with(
            'HPE Smart Array P408i-p SR Gen10')
        (get_ssc_by_controller_model_mock.return_value.
         disk_erase.assert_called_once_with(['2I:1:1'], 'SSD', None))

    @mock.patch.object(system.LOG, 'warn', autospec=True)
    @mock.patch.object(system.HPESystem,
                       '_get_disk_properties_by_drive_location')
    @mock.patch.object(system.HPESystem,
                       '_get_drives_has_raid')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test_do_disk_erase_with_raid(
            self, array_controller_by_model_mock,
            get_ssc_by_controller_model_mock,
            get_all_controllers_model_mock,
            drives_raid_mock, get_disk_prop_mock,
            system_log_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        drives_raid_mock.return_value = ['2I:1:2']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        (array_controller_by_model_mock.return_value.physical_drives.
         get_all_hdd_drives_locations.return_value) = ['2I:1:1', '2I:1:2']
        get_disk_prop_mock.return_value = {
            'Serial number': 'KWGER73R',
            'Size(GB)': 600,
            'Media type': 'HDD',
            'Location': '2I:1:2'}
        self.sys_inst.do_disk_erase('HDD', None)
        get_ssc_by_controller_model_mock.assert_called_once_with(
            'HPE Smart Array P408i-p SR Gen10')
        (get_ssc_by_controller_model_mock.return_value.
         disk_erase.assert_called_once_with(['2I:1:1'], 'HDD', None))
        disk_prop = {'Serial number': 'KWGER73R',
                     'Size(GB)': 600,
                     'Media type': 'HDD',
                     'Location': '2I:1:2'}
        system_log_mock.assert_called_once_with(
            "Skipping disk erase of %(disk_list)s "
            "with logical volumes on them."
            % {'disk_list': [disk_prop]})

    @mock.patch.object(system.HPESystem,
                       '_get_drives_has_raid')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(system.HPESystem,
                       '_get_smart_storage_config_by_controller_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    @mock.patch.object(system.LOG, 'warn', autospec=True)
    def test_do_disk_erase_with_S_and_P_series_controller(
            self, system_log_mock, array_controller_by_model_mock,
            get_ssc_by_controller_model_mock, get_all_controllers_model_mock,
            drives_raid_mock):
        drives_raid_mock.return_value = []
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array S100i SR Gen10',
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        (array_controller_by_model_mock.return_value.physical_drives.
         get_all_ssd_drives_locations.return_value) = ['2I:1:1']
        self.sys_inst.do_disk_erase('SSD', None)
        get_ssc_by_controller_model_mock.assert_called_once_with(
            'HPE Smart Array P408i-p SR Gen10')
        (get_ssc_by_controller_model_mock.return_value.
         disk_erase.assert_called_once_with(['2I:1:1'], 'SSD', None))
        system_log_mock.assert_called_once_with(
            "Smart array controller: HPE Smart Array S100i SR Gen10, doesn't "
            "support sanitize disk erase. All the disks of the controller are "
            "ignored.")

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    def test_do_disk_erase_failed(
            self, get_all_controllers_model_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        (self.conn.get.return_value.
         json.side_effect) = [ss_json, acc_json, sushy.exceptions.SushyError]
        self.assertRaisesRegex(
            exception.IloError,
            "The Redfish controller failed to perform the sanitize disk erase "
            "on smart storage controller: HPE Smart Array P408i-p SR Gen10, "
            "on disk_type: SSD with error:",
            self.sys_inst.do_disk_erase, 'SSD', None)

    @mock.patch.object(system.HPESystem, 'get_smart_storage_config')
    def test__get_drives_has_raid(
            self, get_smart_storage_config_mock):
        config_id = ['/redfish/v1/systems/1/smartstorageconfig/']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
            self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = ss_json
        type(self.sys_inst).smart_storage_config_identities = (
            mock.PropertyMock(return_value=config_id))
        (get_smart_storage_config_mock.
         return_value.get_drives_has_raid.return_value) = ["2I:1:2", "2I:1:1"]
        result = self.sys_inst._get_drives_has_raid()
        self.assertEqual(result, ["2I:1:2", "2I:1:1"])
        get_smart_storage_config_mock.assert_called_once_with(config_id[0])

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test__get_disk_properties_by_drive_location(
            self, array_controller_by_model_mock,
            get_all_controllers_model_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        prop = {
            'Serial number': 'KWGER73R',
            'Size(GB)': 600,
            'Media type': 'HDD',
            'Location': '2I:1:2'}
        (array_controller_by_model_mock.return_value.physical_drives.
         get_disk_properties_by_drive_location.return_value) = prop
        result = self.sys_inst._get_disk_properties_by_drive_location(
            '2I:1:1')
        self.assertEqual(result, prop)

    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'get_all_controllers_model')
    @mock.patch.object(array_controller.HPEArrayControllerCollection,
                       'array_controller_by_model')
    def test_get_disk_types(
            self, array_controller_by_model_mock,
            get_all_controllers_model_mock):
        get_all_controllers_model_mock.return_value = [
            'HPE Smart Array P408i-p SR Gen10']
        with open('proliantutils/tests/redfish/'
                  'json_samples/smart_storage.json', 'r') as f:
            ss_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/array_controller_collection.json', 'r') as f:
            acc_json = json.loads(f.read())
        self.conn.get.return_value.json.reset_mock()
        self.conn.get.return_value.json.side_effect = [ss_json, acc_json]
        (array_controller_by_model_mock.return_value.physical_drives.
         has_hdd.return_value) = True
        (array_controller_by_model_mock.return_value.physical_drives.
         has_ssd.return_value) = False
        types = ['HDD', 'SSD']
        self.assertEqual(list(set(types)), self.sys_inst.get_disk_types())
        array_controller_by_model_mock.assert_called_once_with(
            'HPE Smart Array P408i-p SR Gen10')

    @mock.patch.object(ethernet_interface.EthernetInterfaceCollection,
                       'get_uefi_device_path_by_mac')
    def test_get_nic_association_name_by_mac(self, uefi_device_path_mock):
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios.json', 'r') as f:
            bios_json = json.loads(f.read())
        with open('proliantutils/tests/redfish/'
                  'json_samples/bios_mappings.json', 'r') as f:
            bios_mappings_json = json.loads(f.read())
        path = ('proliantutils/tests/redfish/json_samples/'
                'ethernet_interface_collection.json')
        with open(path, 'r') as f:
            eth_coll = json.loads(f.read())
        self.conn.get.return_value.json.side_effect = [
            bios_json['Default'], bios_mappings_json['Default'],
            eth_coll]
        (uefi_device_path_mock.
         return_value) = 'PciRoot(0x2)/Pci(0x0,0x0)/Pci(0x0,0x2)'
        result = self.sys_inst.get_nic_association_name_by_mac(
            '12:44:6A:3B:04:11')
        self.assertEqual(result, 'NicBoot1')

    @mock.patch.object(ethernet_interface.EthernetInterfaceCollection,
                       'get_all_macs')
    def test_validate_macs(self, get_all_macs_mock):
        path = ('proliantutils/tests/redfish/json_samples/'
                'ethernet_interface_collection.json')
        with open(path, 'r') as f:
            eth_coll = json.loads(f.read())
        self.conn.get.return_value.json.side_effect = [eth_coll]
        get_all_macs_mock.return_value = [
            '12:44:6a:3b:04:11', '13:44:6a:3b:04:13']
        result = self.sys_inst.validate_macs(['12:44:6a:3b:04:11'])
        self.assertEqual(result, None)

    @mock.patch.object(ethernet_interface.EthernetInterfaceCollection,
                       'get_all_macs')
    def test_validate_macs_failed(self, get_all_macs_mock):
        path = ('proliantutils/tests/redfish/json_samples/'
                'ethernet_interface_collection.json')
        with open(path, 'r') as f:
            eth_coll = json.loads(f.read())
        self.conn.get.return_value.json.side_effect = [eth_coll]
        get_all_macs_mock.return_value = [
            '12:44:6a:3b:04:11', '13:44:6a:3b:04:13']
        self.assertRaisesRegex(
            exception.InvalidInputError,
            r"Given macs: \['14:23:AD:3B:4C:78'\] not found in the system",
            self.sys_inst.validate_macs,
            ['12:44:6a:3b:04:11', '14:23:AD:3B:4C:78'])
