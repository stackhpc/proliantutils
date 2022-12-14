# Copyright 2018 Hewlett Packard Enterprise Development LP
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

__author__ = 'HPE'

import re

import sushy
from sushy.resources import base
from sushy.resources.system import system
from sushy import utils as sushy_utils

from proliantutils import exception
from proliantutils import log
from proliantutils.redfish.resources.system import bios
from proliantutils.redfish.resources.system import constants
from proliantutils.redfish.resources.system import ethernet_interface
from proliantutils.redfish.resources.system import mappings
from proliantutils.redfish.resources.system import memory
from proliantutils.redfish.resources.system import pci_device
from proliantutils.redfish.resources.system import secure_boot
from proliantutils.redfish.resources.system import smart_storage_config
from proliantutils.redfish.resources.system.storage import \
    constants as storage_const
from proliantutils.redfish.resources.system.storage import \
    mappings as storage_map
from proliantutils.redfish.resources.system.storage import simple_storage
from proliantutils.redfish.resources.system.storage import \
    smart_storage as hpe_smart_storage
from proliantutils.redfish.resources.system.storage import storage
from proliantutils.redfish import utils


LOG = log.get_logger(__name__)

PERSISTENT_BOOT_DEVICE_MAP = {
    'CDROM': sushy.BOOT_SOURCE_TARGET_CD,
    'NETWORK': sushy.BOOT_SOURCE_TARGET_PXE,
    'ISCSI': sushy.BOOT_SOURCE_TARGET_UEFI_TARGET,
    'HDD': sushy.BOOT_SOURCE_TARGET_HDD,
    'UEFIHTTP': sushy.BOOT_SOURCE_TARGET_UEFI_HTTP
}


class PowerButtonActionField(base.CompositeField):
    allowed_values = base.Field('PushType@Redfish.AllowableValues',
                                adapter=list)

    target_uri = base.Field('target', required=True)


class OneButtonSecureEraseActionField(base.CompositeField):
    target_uri = base.Field('target', required=True)


class HpeActionsField(base.CompositeField):
    computer_system_ext_powerbutton = (
        PowerButtonActionField('#HpeComputerSystemExt.PowerButton'))

    computer_system_ext_one_button_secure_erase = (
        OneButtonSecureEraseActionField(
            '#HpeComputerSystemExt.SecureSystemErase'))


class HPESystem(system.System):
    """Class that extends the functionality of System resource class

    This class extends the functionality of System resource class
    from sushy
    """

    model = base.Field(['Model'])
    rom_version = base.Field(['Oem', 'Hpe', 'Bios', 'Current',
                             'VersionString'])
    uefi_target_override_devices = (base.Field([
        'Boot',
        'UefiTargetBootSourceOverride@Redfish.AllowableValues'],
        adapter=list))

    smart_storage_config_identities = base.Field(
        ['Oem', 'Hpe', 'SmartStorageConfig'],
        adapter=sushy_utils.get_members_identities)

    supported_boot_mode = base.MappedField(
        ['Oem', 'Hpe', 'Bios', 'UefiClass'], mappings.SUPPORTED_BOOT_MODE,
        default=constants.SUPPORTED_LEGACY_BIOS_ONLY)
    """System supported boot mode."""
    post_state = base.MappedField(
        ['Oem', 'Hpe', 'PostState'], mappings.POST_STATE_MAP,
        default=constants.POST_STATE_NULL)
    """System POST state"""

    _hpe_actions = HpeActionsField(['Oem', 'Hpe', 'Actions'], required=True)
    """Oem specific system extensibility actions"""

    def _get_hpe_push_power_button_action_element(self):
        push_action = self._hpe_actions.computer_system_ext_powerbutton
        if not push_action:
            raise exception.MissingAttributeError(
                attribute='Oem/Hpe/Actions/#HpeComputerSystemExt.PowerButton',
                resource=self.path)

        return push_action

    def _get_hpe_one_button_secure_erase_action_element(self):
        one_button_secure_erase_action = (
            self._hpe_actions.computer_system_ext_one_button_secure_erase)
        if not one_button_secure_erase_action:
            raise exception.MissingAttributeError(
                attribute=(
                    'Oem/Hpe/Actions/#HpeComputerSystemExt.SecureSystemErase'),
                resource=self.path)

        return one_button_secure_erase_action

    def do_one_button_secure_erase(self):
        """Perform the one button secure erase on the hardware.

        The One-button secure erase process resets iLO and deletes all licenses
        stored there, resets BIOS settings, and deletes all AHS and warranty
        data stored on the system. It also erases supported non-volatile
        storage data and deletes any deployment settings profiles.

        :raises: IloError, on an error from iLO.
        """
        try:
            target_uri = (
                self._get_hpe_one_button_secure_erase_action_element().
                target_uri)
            data = {
                "SystemROMAndiLOErase": True,
                "UserDataErase": True
            }
            self._conn.post(target_uri, data=data)
        except sushy.exceptions.SushyError as e:
            msg = ("The Redfish controller failed to perform one button "
                   "secure erase operation on the hardware. Error: %(error)s"
                   % {'error': str(e)})
            raise exception.IloError(msg)

    def push_power_button(self, target_value):
        """Reset the system in hpe exclusive manner.

        :param target_value: The target value to be set.
        :raises: InvalidInputError, if the target value is not
            allowed.
        :raises: SushyError, on an error from iLO.
        """
        if target_value not in mappings.PUSH_POWER_BUTTON_VALUE_MAP_REV:
            msg = ('The parameter "%(parameter)s" value "%(target_value)s" is '
                   'invalid. Valid values are: %(valid_power_values)s' %
                   {'parameter': 'target_value', 'target_value': target_value,
                    'valid_power_values': (
                        mappings.PUSH_POWER_BUTTON_VALUE_MAP_REV.keys())})
            raise exception.InvalidInputError(msg)

        value = mappings.PUSH_POWER_BUTTON_VALUE_MAP_REV[target_value]
        target_uri = (
            self._get_hpe_push_power_button_action_element().target_uri)

        self._conn.post(target_uri, data={'PushType': value})

    @property
    @sushy_utils.cache_it
    def bios_settings(self):
        """Property to provide reference to `BIOSSettings` instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return bios.BIOSSettings(
            self._conn, utils.get_subresource_path_by(self, 'Bios'),
            redfish_version=self.redfish_version)

    def update_persistent_boot(self, devices=[], persistent=False):
        """Changes the persistent boot device order in BIOS boot mode for host

        Note: It uses first boot device from the devices and ignores rest.

        :param devices: ordered list of boot devices
        :param persistent: Boolean flag to indicate if the device to be set as
                           a persistent boot device
        :raises: IloError, on an error from iLO.
        :raises: IloInvalidInputError, if the given input is not valid.
        """
        device = PERSISTENT_BOOT_DEVICE_MAP.get(devices[0].upper())
        if device == sushy.BOOT_SOURCE_TARGET_UEFI_TARGET:
            try:
                uefi_devices = self.uefi_target_override_devices
                iscsi_device = None
                for uefi_device in uefi_devices:
                    if uefi_device is not None and 'iSCSI' in uefi_device:
                        iscsi_device = uefi_device
                        break

                if iscsi_device is None:
                    msg = 'No UEFI iSCSI bootable device found on system.'
                    raise exception.IloError(msg)

            except sushy.exceptions.SushyError as e:
                msg = ('Unable to get uefi target override devices. '
                       'Error %s') % (str(e))
                raise exception.IloError(msg)

            uefi_boot_settings = {
                'Boot': {'UefiTargetBootSourceOverride': iscsi_device}
            }
            self._conn.patch(self.path, data=uefi_boot_settings)
        elif device is None:
            device = sushy.BOOT_SOURCE_TARGET_NONE

        tenure = (sushy.BOOT_SOURCE_ENABLED_CONTINUOUS
                  if persistent else sushy.BOOT_SOURCE_ENABLED_ONCE)
        self.set_system_boot_source(device, enabled=tenure)

    @property
    @sushy_utils.cache_it
    def pci_devices(self):
        """Provides the collection of PCI devices

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return pci_device.PCIDeviceCollection(
            self._conn, utils.get_subresource_path_by(
                self, ['Oem', 'Hpe', 'Links', 'PCIDevices']))

    @property
    @sushy_utils.cache_it
    def secure_boot(self):
        """Property to provide reference to `SecureBoot` instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return secure_boot.SecureBoot(
            self._conn, utils.get_subresource_path_by(self, 'SecureBoot'),
            redfish_version=self.redfish_version)

    def _get_hpe_sub_resource_collection_path(self, sub_res):
        path = None
        try:
            path = utils.get_subresource_path_by(self, sub_res)
        except exception.MissingAttributeError:
            path = utils.get_subresource_path_by(
                self, ['Oem', 'Hpe', 'Links', sub_res])
        return path

    @property
    @sushy_utils.cache_it
    def ethernet_interfaces(self):
        """Provide reference to EthernetInterfacesCollection instance"""
        return ethernet_interface.EthernetInterfaceCollection(
            self._conn,
            self._get_hpe_sub_resource_collection_path('EthernetInterfaces'),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def smart_storage(self):
        """This property gets the object for smart storage.

        This property gets the object for smart storage.
        There is no collection for smart storages.
        :returns: an instance of smart storage
        """
        return hpe_smart_storage.HPESmartStorage(
            self._conn, utils.get_subresource_path_by(
                self, ['Oem', 'Hpe', 'Links', 'SmartStorage']),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def storages(self):
        """This property gets the list of instances for Storages

        This property gets the list of instances for Storages
        :returns: a list of instances of Storages
        """
        return storage.StorageCollection(
            self._conn, utils.get_subresource_path_by(self, 'Storage'),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def simple_storages(self):
        """This property gets the list of instances for SimpleStorages

        :returns: a list of instances of SimpleStorages
        """
        return simple_storage.SimpleStorageCollection(
            self._conn, utils.get_subresource_path_by(self, 'SimpleStorage'),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def memory(self):
        """Property to provide reference to `MemoryCollection` instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return memory.MemoryCollection(
            self._conn, utils.get_subresource_path_by(self, 'Memory'),
            redfish_version=self.redfish_version)

    def get_smart_storage_config(self, smart_storage_config_url):
        """Returns a SmartStorageConfig Instance for each controller."""
        return (smart_storage_config.
                HPESmartStorageConfig(self._conn, smart_storage_config_url,
                                      redfish_version=self.redfish_version))

    def _get_smart_storage_config_by_controller_model(self, controller_model):
        """Returns a SmartStorageConfig Instance for controller by model.

        :returns: SmartStorageConfig Instance for controller
        """
        ac = self.smart_storage.array_controllers.array_controller_by_model(
            controller_model)
        if ac:
            for ssc_id in self.smart_storage_config_identities:
                ssc_obj = self.get_smart_storage_config(ssc_id)
                if ac.location == ssc_obj.location:
                    return ssc_obj

    def check_smart_storage_config_ids(self):
        """Check SmartStorageConfig controllers is there in hardware.

        :raises: IloError, on an error from iLO.
        """
        if self.smart_storage_config_identities is None:
            msg = ('The Redfish controller failed to get the '
                   'SmartStorageConfig controller configurations.')
            LOG.debug(msg)
            raise exception.IloError(msg)

    def delete_raid(self):
        """Delete the raid configuration on the hardware.

        Loops through each SmartStorageConfig controller and clears the
        raid configuration.

        :raises: IloError, on an error from iLO.
        """
        self.check_smart_storage_config_ids()
        any_exceptions = []
        ld_exc_count = 0
        for config_id in self.smart_storage_config_identities:
            try:
                ssc_obj = self.get_smart_storage_config(config_id)
                ssc_obj.delete_raid()
            except exception.IloLogicalDriveNotFoundError:
                ld_exc_count += 1
            except sushy.exceptions.SushyError as e:
                any_exceptions.append((config_id, str(e)))

        if any_exceptions:
            msg = ('The Redfish controller failed to delete the '
                   'raid configuration in one or more controllers with '
                   'Error: %(error)s' % {'error': str(any_exceptions)})
            raise exception.IloError(msg)

        if ld_exc_count == len(self.smart_storage_config_identities):
            msg = ('No logical drives are found in any controllers. Nothing '
                   'to delete.')
            raise exception.IloLogicalDriveNotFoundError(msg)

    def _get_drives_has_raid(self):
        drives = []
        ssc_ids = self.smart_storage_config_identities
        for ssc_id in ssc_ids:
            ssc_obj = self.get_smart_storage_config(ssc_id)
            drives.extend(ssc_obj.get_drives_has_raid())
        return drives

    def _get_disk_properties_by_drive_location(self, location):
        controllers = (
            self.smart_storage.array_controllers.get_all_controllers_model())
        for controller in controllers:
            controller_obj = (
                self.smart_storage.array_controllers.array_controller_by_model(
                    controller))
            properties = (
                controller_obj.physical_drives.
                get_disk_properties_by_drive_location(location))
            if properties:
                return properties

    def do_disk_erase(self, disk_type, pattern):
        """Performs out-of-band sanitize disk erase on the hardware.

        :param disk_type: Media type of disk drives either 'HDD' or 'SSD'.
        :param pattern: Erase pattern, if nothing passed default
                        ('overwrite' for 'HDD', and 'block' for 'SSD') will
                        be used.
        :raises: IloError, on an error from iLO.
        """
        try:
            current_controller = None
            controllers = (
                self.smart_storage.array_controllers.
                get_all_controllers_model())
            for controller in controllers:
                current_controller = controller
                # Will filter out S controller by controller model ex.
                # 'HPE Smart Array S100i SR Gen10'.
                if re.search("^HPE Smart Array S[0-9]{3}", controller) is None:
                    controller_obj = (
                        self.smart_storage.array_controllers.
                        array_controller_by_model(controller))
                    ssc_obj = (
                        self._get_smart_storage_config_by_controller_model(
                            controller))
                    if disk_type == (storage_map.MEDIA_TYPE_MAP_REV[
                                     storage_const.MEDIA_TYPE_HDD]):
                        disks = (
                            controller_obj.
                            physical_drives.get_all_hdd_drives_locations())
                    else:
                        disks = (
                            controller_obj.
                            physical_drives.get_all_ssd_drives_locations())

                    assigned_disks = self._get_drives_has_raid()

                    unassigned_disks = list(set(disks) - set(assigned_disks))

                    if unassigned_disks:
                        ssc_obj.disk_erase(unassigned_disks, disk_type,
                                           pattern)

                    if assigned_disks:
                        disk_list = []
                        for disk in assigned_disks:
                            disk_prop = (
                                self._get_disk_properties_by_drive_location(
                                    disk))
                            if disk_prop['Media type'] is disk_type:
                                disk_list.append(disk_prop)

                        if disk_list:
                            LOG.warn("Skipping disk erase of %(disk_list)s "
                                     "with logical volumes on them."
                                     % {'disk_list': disk_list})
                else:
                    LOG.warn("Smart array controller: %(controller)s, doesn't "
                             "support sanitize disk erase. All the disks of "
                             "the controller are ignored."
                             % {'controller': current_controller})
        except sushy.exceptions.SushyError as e:
            msg = ("The Redfish controller failed to perform the sanitize "
                   "disk erase on smart storage controller: %(controller)s, "
                   "on disk_type: %(disk_type)s with error: %(error)s"
                   % {'controller': current_controller, 'disk_type': disk_type,
                      'error': str(e)})
            raise exception.IloError(msg)

    def has_disk_erase_completed(self):
        """Get out-of-band sanitize disk erase status.

        :returns: True if disk erase completed on all controllers
                  otherwise False
        :raises: IloError, on an error from iLO.
        """
        try:
            controllers = (self.smart_storage.array_controllers.
                           get_all_controllers_model())
            for controller in controllers:
                controller_obj = (self.smart_storage.array_controllers.
                                  array_controller_by_model(controller))
                if controller_obj.physical_drives.has_disk_erase_completed:
                    continue
                else:
                    return False
            return True
        except sushy.exceptions.SushyError as e:
            msg = ('The Redfish controller failed to get the status of '
                   'sanitize disk erase. Error: %(error)s'
                   % {'error': str(e)})
            raise exception.IloError(msg)

    def _parse_raid_config_data(self, raid_config):
        """It will parse raid config data based on raid controllers

        :param raid_config: A dictionary containing target raid configuration
                            data. This data stucture should be as follows:
                            raid_config = {'logical_disks': [{'raid_level': 1,
                            'size_gb': 100, 'controller':
                            'HPE Smart Array P408i-a SR Gen10'},
                            <info-for-logical-disk-2>]}
        :returns: A dictionary of controllers, each containing list of
                  their respected logical drives.
        """
        default = (
            self.smart_storage.array_controllers.get_default_controller.model)
        controllers = {default: []}
        for ld in raid_config['logical_disks']:
            if 'controller' not in ld.keys():
                controllers[default].append(ld)
            else:
                ctrl = ld['controller']
                if ctrl not in controllers:
                    controllers[ctrl] = []
                controllers[ctrl].append(ld)
        return controllers

    def create_raid(self, raid_config):
        """Create the raid configuration on the hardware.

        :param raid_config: A dictionary containing target raid configuration
                            data. This data stucture should be as follows:
                            raid_config = {'logical_disks': [{'raid_level': 1,
                            'size_gb': 100, 'physical_disks': ['6I:1:5'],
                            'controller': 'HPE Smart Array P408i-a SR Gen10'},
                            <info-for-logical-disk-2>]}
        :raises: IloError, on an error from iLO.
        """
        self.check_smart_storage_config_ids()
        any_exceptions = []
        controllers = self._parse_raid_config_data(raid_config)
        # Creating raid on rest of the controllers
        for controller in controllers:
            try:
                config = {'logical_disks': controllers[controller]}
                ssc_obj = (
                    self._get_smart_storage_config_by_controller_model(
                        controller))
                if ssc_obj:
                    ssc_obj.create_raid(config)
                else:
                    members = (
                        self.smart_storage.array_controllers.get_members())
                    models = [member.model for member in members]
                    msg = ('Controller not found. Available controllers are: '
                           '%(models)s' % {'models': models})
                    any_exceptions.append((controller, msg))
            except sushy.exceptions.SushyError as e:
                any_exceptions.append((controller, str(e)))

        if any_exceptions:
            msg = ('The Redfish controller failed to create the '
                   'raid configuration for one or more controllers with '
                   'Error: %(error)s' % {'error': str(any_exceptions)})
            raise exception.IloError(msg)

    def _post_create_read_raid(self, raid_config):
        """Read the logical drives from the system after post-create raid

        :param raid_config: A dictionary containing target raid configuration
                            data. This data stucture should be as follows:
                            raid_config = {'logical_disks': [{'raid_level': 1,
                            'size_gb': 100, 'physical_disks': ['6I:1:5'],
                            'controller': 'HPE Smart Array P408i-a SR Gen10'},
                            <info-for-logical-disk-2>]}
        :raises: IloLogicalDriveNotFoundError, if no controllers are configured
        :raises: IloError, if any error form iLO
        :returns: A dictionary containing list of logical disks
        """
        controllers = self._parse_raid_config_data(raid_config)
        ld_exc_count = 0
        any_exceptions = []
        config = {'logical_disks': []}
        for controller in controllers:
            try:
                ssc_obj = (
                    self._get_smart_storage_config_by_controller_model(
                        controller))
                if ssc_obj:
                    result = ssc_obj.read_raid(controller=controller)
                    config['logical_disks'].extend(result['logical_disks'])
            except exception.IloLogicalDriveNotFoundError:
                ld_exc_count += 1
            except sushy.exceptions.SushyError as e:
                any_exceptions.append((controller, str(e)))

        if ld_exc_count == len(controllers):
            msg = 'No logical drives are found in any controllers.'
            raise exception.IloLogicalDriveNotFoundError(msg)
        if any_exceptions:
            msg = ('The Redfish controller failed to read the '
                   'raid configuration in one or more controllers with '
                   'Error: %(error)s' % {'error': str(any_exceptions)})
            raise exception.IloError(msg)
        return config

    def _post_delete_read_raid(self):
        """Read the logical drives from the system after post-delete raid

        :raises: IloError, if any error form iLO
        :returns: Empty dictionary with format: {'logical_disks': []}
        """
        any_exceptions = []
        ssc_ids = self.smart_storage_config_identities
        config = {'logical_disks': []}
        for ssc_id in ssc_ids:
            try:
                ssc_obj = self.get_smart_storage_config(ssc_id)
                ac_obj = (
                    self.smart_storage.array_controllers.
                    array_controller_by_location(ssc_obj.location))
                if ac_obj:
                    model = ac_obj.model
                    result = ssc_obj.read_raid()
                    if result:
                        config['logical_disks'].extend(result['logical_disks'])
            except sushy.exceptions.SushyError as e:
                any_exceptions.append((model, str(e)))

        if any_exceptions:
            msg = ('The Redfish controller failed to read the '
                   'raid configuration in one or more controllers with '
                   'Error: %(error)s' % {'error': str(any_exceptions)})
            raise exception.IloError(msg)
        return config

    def read_raid(self, raid_config=None):
        """Read the logical drives from the system

        :param raid_config: None or a dictionary containing target raid
                            configuration data. This data stucture should be as
                            follows:
                            raid_config = {'logical_disks': [{'raid_level': 1,
                            'size_gb': 100, 'physical_disks': ['6I:1:5'],
                            'controller': 'HPE Smart Array P408i-a SR Gen10'},
                            <info-for-logical-disk-2>]}
        :returns: A dictionary containing list of logical disks
        """
        self.check_smart_storage_config_ids()
        if raid_config:
            # When read called after create raid, user can pass raid config
            # as a input
            result = self._post_create_read_raid(raid_config=raid_config)
        else:
            # When read called after delete raid, there will be no input
            # passed by user then
            result = self._post_delete_read_raid()
        return result

    def get_disk_types(self):
        """Get the list of all disk type available in server

        :returns: A list containing disk types
        :raises: IloError, on an error from iLO.
        """
        disk_types = []
        try:
            controllers = (self.smart_storage.array_controllers.
                           get_all_controllers_model())
            for controller in controllers:
                controller_obj = (self.smart_storage.array_controllers.
                                  array_controller_by_model(controller))
                if controller_obj.physical_drives.has_rotational:
                    disk_types.append(storage_map.MEDIA_TYPE_MAP_REV[
                                      storage_const.MEDIA_TYPE_HDD])
                if controller_obj.physical_drives.has_ssd:
                    disk_types.append(storage_map.MEDIA_TYPE_MAP_REV[
                                      storage_const.MEDIA_TYPE_SSD])
            return list(set(disk_types))
        except sushy.exceptions.SushyError as e:
            msg = ('The Redfish controller failed to get list of disk types. '
                   'Error: %(error)s'
                   % {'error': str(e)})
            raise exception.IloError(msg)

    def validate_macs(self, macs):
        """Validate given macs are there in system

        :param macs: List of macs
        :raises: InvalidInputError, if macs not valid
        """
        macs_available = self.ethernet_interfaces.get_all_macs()
        if not set(macs).issubset(macs_available):
            msg = ("Given macs: %(macs)s not found in the system"
                   % {'macs': list(set(macs) - set(macs_available))})
            raise exception.InvalidInputError(msg)

    def get_nic_association_name_by_mac(self, mac):
        """Return nic association name by mac address

        :mac: Mac address.
        :returns: Nic association name. Ex. NicBoot1
        """
        mappings = self.bios_settings.bios_mappings.pci_settings_mappings
        correlatable_id = self.ethernet_interfaces.get_uefi_device_path_by_mac(
            mac)
        for mapping in mappings:
            for subinstance in mapping['Subinstances']:
                for association in subinstance['Associations']:
                    if subinstance.get('CorrelatableID') == correlatable_id:
                        return [name for name in subinstance[
                            'Associations'] if 'NicBoot' in name][0]
