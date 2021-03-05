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

from base64 import b64decode
import json
import re

from OpenSSL.crypto import FILETYPE_ASN1
from OpenSSL.crypto import load_certificate
from six.moves.urllib import parse
import sushy
from sushy.resources.system import mappings as sushy_map
from sushy import utils

from proliantutils import exception
from proliantutils.ilo import constants as ilo_cons
from proliantutils.ilo import firmware_controller
from proliantutils.ilo import operations
from proliantutils import log
from proliantutils.redfish import main
from proliantutils.redfish.resources import gpu_common
from proliantutils.redfish.resources.manager import constants as mgr_cons
from proliantutils.redfish.resources.system import constants as sys_cons
from proliantutils.redfish.resources.system.storage \
    import common as common_storage
from proliantutils.redfish import utils as rf_utils
from proliantutils import utils as common_utils

"""
Class specific for Redfish APIs.
"""

GET_POWER_STATE_MAP = {
    sushy.SYSTEM_POWER_STATE_ON: 'ON',
    sushy.SYSTEM_POWER_STATE_POWERING_ON: 'ON',
    sushy.SYSTEM_POWER_STATE_OFF: 'OFF',
    sushy.SYSTEM_POWER_STATE_POWERING_OFF: 'OFF'
}

POWER_RESET_MAP = {
    'ON': sushy.RESET_ON,
    'OFF': sushy.RESET_FORCE_OFF,
}

DEVICE_COMMON_TO_REDFISH = {
    'NETWORK': sushy.BOOT_SOURCE_TARGET_PXE,
    'HDD': sushy.BOOT_SOURCE_TARGET_HDD,
    'CDROM': sushy.BOOT_SOURCE_TARGET_CD,
    'ISCSI': sushy.BOOT_SOURCE_TARGET_UEFI_TARGET,
    'UEFIHTTP': sushy.BOOT_SOURCE_TARGET_UEFI_HTTP,
    'NONE': sushy.BOOT_SOURCE_TARGET_NONE
}

DEVICE_REDFISH_TO_COMMON = {v: k for k, v in DEVICE_COMMON_TO_REDFISH.items()}

BOOT_MODE_MAP = {
    sys_cons.BIOS_BOOT_MODE_LEGACY_BIOS: 'LEGACY',
    sys_cons.BIOS_BOOT_MODE_UEFI: 'UEFI'
}

BOOT_MODE_MAP_REV = (
    utils.revert_dictionary(BOOT_MODE_MAP))

PERSISTENT_BOOT_MAP = {
    sushy.BOOT_SOURCE_TARGET_PXE: 'NETWORK',
    sushy.BOOT_SOURCE_TARGET_HDD: 'HDD',
    sushy.BOOT_SOURCE_TARGET_CD: 'CDROM',
    sushy.BOOT_SOURCE_TARGET_UEFI_TARGET: 'NETWORK',
    sushy.BOOT_SOURCE_TARGET_UEFI_HTTP: 'UEFIHTTP',
    sushy.BOOT_SOURCE_TARGET_NONE: 'NONE'
}

GET_SECUREBOOT_CURRENT_BOOT_MAP = {
    sys_cons.SECUREBOOT_CURRENT_BOOT_ENABLED: True,
    sys_cons.SECUREBOOT_CURRENT_BOOT_DISABLED: False
}

GET_POST_STATE_MAP = {
    sys_cons.POST_STATE_NULL: 'Null',
    sys_cons.POST_STATE_UNKNOWN: 'Unknown',
    sys_cons.POST_STATE_RESET: 'Reset',
    sys_cons.POST_STATE_POWEROFF: 'PowerOff',
    sys_cons.POST_STATE_INPOST: 'InPost',
    sys_cons.POST_STATE_INPOSTDISCOVERY: 'InPostDiscoveryComplete',
    sys_cons.POST_STATE_FINISHEDPOST: 'FinishedPost'
}

# Assuming only one system and one manager present as part of
# collection, as we are dealing with iLO's here.
PROLIANT_MANAGER_ID = '1'
PROLIANT_SYSTEM_ID = '1'
PROLIANT_CHASSIS_ID = '1'

BOOT_OPTION_MAP = {'BOOT_ONCE': True,
                   'BOOT_ALWAYS': False,
                   'NO_BOOT': False}

VIRTUAL_MEDIA_MAP = {'FLOPPY': mgr_cons.VIRTUAL_MEDIA_FLOPPY,
                     'CDROM': mgr_cons.VIRTUAL_MEDIA_CD}

SUPPORTED_BOOT_MODE_MAP = {
    sys_cons.SUPPORTED_LEGACY_BIOS_ONLY: (
        ilo_cons.SUPPORTED_BOOT_MODE_LEGACY_BIOS_ONLY),
    sys_cons.SUPPORTED_UEFI_ONLY: ilo_cons.SUPPORTED_BOOT_MODE_UEFI_ONLY,
    sys_cons.SUPPORTED_LEGACY_BIOS_AND_UEFI: (
        ilo_cons.SUPPORTED_BOOT_MODE_LEGACY_BIOS_AND_UEFI)
}

_CERTIFICATE_PATTERN = (
    r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----')

LOG = log.get_logger(__name__)


class RedfishOperations(operations.IloOperations):
    """Operations supported on redfish based hardware.

    This class holds APIs which are currently supported via Redfish mode
    of operation. This is a growing list which needs to be updated as and when
    the existing API/s (of its cousin RIS and RIBCL interfaces) are migrated.
    For operations currently supported on the client object, please refer:
    *proliantutils.ilo.client.SUPPORTED_REDFISH_METHODS*
    """

    def __init__(self, redfish_controller_ip, username, password,
                 bios_password=None, cacert=None, root_prefix='/redfish/v1/'):
        """A class representing supported RedfishOperations

        :param redfish_controller_ip: The ip address of the Redfish controller.
        :param username: User account with admin/server-profile access
            privilege
        :param password: User account password
        :param bios_password: bios password
        :param cacert: a path to a CA_BUNDLE file or directory with
            certificates of trusted CAs. If set to None, the driver will
            ignore verifying the SSL certificate; if it's a path the driver
            will use the specified certificate or one of the certificates in
            the directory. Defaults to None.
        :param root_prefix: The default URL prefix. This part includes
            the root service and version. Defaults to /redfish/v1
        """
        super(RedfishOperations, self).__init__()
        address = ('https://' + redfish_controller_ip)
        LOG.debug('Redfish address: %s', address)
        verify = False if cacert is None else cacert

        # for error reporting purpose
        self.host = redfish_controller_ip
        self._root_prefix = root_prefix
        self._username = username

        try:
            self._sushy = main.HPESushy(
                address, username=username, password=password,
                root_prefix=root_prefix, verify=verify)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller at "%(controller)s" has '
                          'thrown error. Error %(error)s') %
                   {'controller': address, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloConnectionError(msg)

    def __del__(self):
        try:
            if self._sushy:
                self._sushy.close()
        except AttributeError:
            pass

    def _get_sushy_system(self, system_id):
        """Get the sushy system for system_id

        :param system_id: The identity of the System resource
        :returns: the Sushy system instance
        :raises: IloError
        """
        system_url = parse.urljoin(self._sushy.get_system_collection_path(),
                                   system_id)
        try:
            return self._sushy.get_system(system_url)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish System "%(system)s" was not found. '
                          'Error %(error)s') %
                   {'system': system_id, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def _get_sushy_manager(self, manager_id):
        """Get the sushy Manager for manager_id

        :param manager_id: The identity of the Manager resource
        :returns: the Sushy Manager instance
        :raises: IloError
        """
        manager_url = parse.urljoin(self._sushy.get_manager_collection_path(),
                                    manager_id)
        try:
            return self._sushy.get_manager(manager_url)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish Manager "%(manager)s" was not found. '
                          'Error %(error)s') %
                   {'manager': manager_id, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def _get_sushy_chassis(self, chassis_id):
        """Get the sushy chassis for chassis_id

        :param chassis_id: The identity of the Chassis resource
        :returns: the Sushy Chassis instance
        :raises: IloError
        """
        chassis_url = parse.urljoin(self._sushy.get_chassis_collection_path(),
                                    chassis_id)
        try:
            return self._sushy.get_chassis(chassis_url)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish Chassis "%(chassis)s" was not found. '
                          'Error %(error)s') %
                   {'chassis': chassis_id, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_product_name(self):
        """Gets the product name of the server.

        :returns: server model name.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        return sushy_system.model

    def get_host_power_status(self):
        """Request the power state of the server.

        :returns: Power State of the server, 'ON' or 'OFF'
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        return GET_POWER_STATE_MAP.get(sushy_system.power_state)

    def reset_server(self):
        """Resets the server.

        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            sushy_system.reset_system(sushy.RESET_FORCE_RESTART)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to reset server. '
                          'Error %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def set_host_power(self, target_value):
        """Sets the power state of the system.

        :param target_value: The target value to be set. Value can be:
            'ON' or 'OFF'.
        :raises: IloError, on an error from iLO.
        :raises: InvalidInputError, if the target value is not
            allowed.
        """
        if target_value not in POWER_RESET_MAP:
            msg = ('The parameter "%(parameter)s" value "%(target_value)s" is '
                   'invalid. Valid values are: %(valid_power_values)s' %
                   {'parameter': 'target_value', 'target_value': target_value,
                    'valid_power_values': POWER_RESET_MAP.keys()})
            raise exception.InvalidInputError(msg)

        # Check current power status, do not act if it's in requested state.
        current_power_status = self.get_host_power_status()
        if current_power_status == target_value:
            LOG.debug(self._("Node is already in '%(target_value)s' power "
                             "state."), {'target_value': target_value})
            return

        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            sushy_system.reset_system(POWER_RESET_MAP[target_value])
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to set power state '
                          'of server to %(target_value)s. Error %(error)s') %
                   {'target_value': target_value, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def press_pwr_btn(self):
        """Simulates a physical press of the server power button.

        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            sushy_system.push_power_button(sys_cons.PUSH_POWER_BUTTON_PRESS)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to press power button'
                          ' of server. Error %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def hold_pwr_btn(self):
        """Simulate a physical press and hold of the server power button.

        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            sushy_system.push_power_button(
                sys_cons.PUSH_POWER_BUTTON_PRESS_AND_HOLD)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to press and hold '
                          'power button of server. Error %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def activate_license(self, key):
        """Activates iLO license.

        :param key: iLO license key.
        :raises: IloError, on an error from iLO.
        """
        sushy_manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            sushy_manager.set_license(key)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update '
                          'the license. Error %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_one_time_boot(self):
        """Retrieves the current setting for the one time boot.

        :returns: Returns boot device that would be used in next
                  boot. Returns 'Normal' if no device is set.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        if (sushy_system.boot.enabled == sushy.BOOT_SOURCE_ENABLED_ONCE):
            return DEVICE_REDFISH_TO_COMMON.get(sushy_system.boot.target)
        else:
            # value returned by RIBCL if one-time boot setting are absent
            return 'Normal'

    def get_pending_boot_mode(self):
        """Retrieves the pending boot mode of the server.

        Gets the boot mode to be set on next reset.
        :returns: either LEGACY or UEFI.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            return BOOT_MODE_MAP.get(
                sushy_system.bios_settings.pending_settings.boot_mode)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The pending BIOS Settings was not found. Error '
                          '%(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_current_boot_mode(self):
        """Retrieves the current boot mode of the server.

        :returns: Current boot mode, LEGACY or UEFI.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            return BOOT_MODE_MAP.get(sushy_system.bios_settings.boot_mode)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The current BIOS Settings was not found. Error '
                          '%(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def _validate_virtual_media(self, device):
        """Check if the device is valid device.

        :param device: virtual media device
        :raises: IloInvalidInputError, if the device is not valid.
        """
        if device not in VIRTUAL_MEDIA_MAP:
            msg = (self._("Invalid device '%s'. Valid devices: FLOPPY or "
                          "CDROM.")
                   % device)
            LOG.debug(msg)
            raise exception.IloInvalidInputError(msg)

    def eject_virtual_media(self, device):
        """Ejects the Virtual Media image if one is inserted.

        :param device: virual media device
        :raises: IloError, on an error from iLO.
        :raises: IloInvalidInputError, if the device is not valid.
        """
        self._validate_virtual_media(device)
        manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            vmedia_device = (
                manager.virtual_media.get_member_device(
                    VIRTUAL_MEDIA_MAP[device]))
            if not vmedia_device.inserted:
                LOG.debug(self._("No media available in the device '%s' to "
                                 "perform eject operation.") % device)
                return

            LOG.debug(self._("Ejecting the media image '%(url)s' from the "
                             "device %(device)s.") %
                      {'url': vmedia_device.image, 'device': device})
            vmedia_device.eject_media()
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller failed to eject the virtual"
                          " media device '%(device)s'. Error %(error)s.") %
                   {'device': device, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def insert_virtual_media(self, url, device):
        """Inserts the Virtual Media image to the device.

        :param url: URL to image
        :param device: virual media device
        :raises: IloError, on an error from iLO.
        :raises: IloInvalidInputError, if the device is not valid.
        """
        self._validate_virtual_media(device)
        manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            vmedia_device = (
                manager.virtual_media.get_member_device(
                    VIRTUAL_MEDIA_MAP[device]))
            if vmedia_device.inserted:
                vmedia_device.eject_media()

            LOG.debug(self._("Inserting the image url '%(url)s' to the "
                             "device %(device)s.") %
                      {'url': url, 'device': device})
            vmedia_device.insert_media(url)
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller failed to insert the media "
                          "url %(url)s in the virtual media device "
                          "'%(device)s'. Error %(error)s.") %
                   {'url': url, 'device': device, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def set_vm_status(self, device='FLOPPY',
                      boot_option='BOOT_ONCE', write_protect='YES'):
        """Sets the Virtual Media drive status

        It sets the boot option for virtual media device.
        Note: boot option can be set only for CD device.

        :param device: virual media device
        :param boot_option: boot option to set on the virtual media device
        :param write_protect: set the write protect flag on the vmedia device
                              Note: It's ignored. In Redfish it is read-only.
        :raises: IloError, on an error from iLO.
        :raises: IloInvalidInputError, if the device is not valid.
        """
        # CONNECT is a RIBCL call. There is no such property to set in Redfish.
        if boot_option == 'CONNECT':
            return

        self._validate_virtual_media(device)

        if boot_option not in BOOT_OPTION_MAP:
            msg = (self._("Virtual media boot option '%s' is invalid.")
                   % boot_option)
            LOG.debug(msg)
            raise exception.IloInvalidInputError(msg)

        manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            vmedia_device = (
                manager.virtual_media.get_member_device(
                    VIRTUAL_MEDIA_MAP[device]))
            vmedia_device.set_vm_status(BOOT_OPTION_MAP[boot_option])
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller failed to set the virtual "
                          "media status for '%(device)s'. Error %(error)s") %
                   {'device': device, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    @firmware_controller.check_firmware_update_component
    def update_firmware(self, file_url, component_type):
        """Updates the given firmware on the server for the given component.

        :param file_url: location of the raw firmware file. Extraction of the
                         firmware file (if in compact format) is expected to
                         happen prior to this invocation.
        :param component_type: Type of component to be applied to.
        :raises: IloError, on an error from iLO.
        """
        try:
            update_service_inst = self._sushy.get_update_service()
            update_service_inst.flash_firmware(self, file_url)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update firmware '
                          'with firmware %(file)s Error %(error)s') %
                   {'file': file_url, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def _is_boot_mode_uefi(self):
        """Checks if the system is in uefi boot mode.

        :return: 'True' if the boot mode is uefi else 'False'
        """
        boot_mode = self.get_current_boot_mode()
        return (boot_mode == BOOT_MODE_MAP.get(sys_cons.BIOS_BOOT_MODE_UEFI))

    def get_persistent_boot_device(self):
        """Get current persistent boot device set for the host

        :returns: persistent boot device for the system
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        # Return boot device if it is persistent.
        if ((sushy_system.
             boot.enabled) == sushy.BOOT_SOURCE_ENABLED_CONTINUOUS):
            return PERSISTENT_BOOT_MAP.get(sushy_system.boot.target)
        # Check if we are in BIOS boot mode.
        # There is no resource to fetch boot device order for BIOS boot mode
        if not self._is_boot_mode_uefi():
            return None

        try:
            boot_device = (sushy_system.bios_settings.boot_settings.
                           get_persistent_boot_device())
            return PERSISTENT_BOOT_MAP.get(boot_device)
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller is unable to get "
                          "persistent boot device. Error %(error)s") %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def set_pending_boot_mode(self, boot_mode):
        """Sets the boot mode of the system for next boot.

        :param boot_mode: either 'uefi' or 'legacy'.
        :raises: IloInvalidInputError, on an invalid input.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)

        if boot_mode.upper() not in BOOT_MODE_MAP_REV.keys():
            msg = (('Invalid Boot mode: "%(boot_mode)s" specified, valid boot '
                    'modes are either "uefi" or "legacy"')
                   % {'boot_mode': boot_mode})
            raise exception.IloInvalidInputError(msg)

        try:
            sushy_system.bios_settings.pending_settings.set_pending_boot_mode(
                BOOT_MODE_MAP_REV.get(boot_mode.upper()))
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to set '
                          'pending boot mode to %(boot_mode)s. '
                          'Error: %(error)s') %
                   {'boot_mode': boot_mode, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_persistent_boot(self, devices=[]):
        """Changes the persistent boot device order for the host

        :param devices: ordered list of boot devices
        :raises: IloError, on an error from iLO.
        :raises: IloInvalidInputError, if the given input is not valid.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        # Check if the input is valid
        for item in devices:
            if item.upper() not in DEVICE_COMMON_TO_REDFISH:
                msg = (self._('Invalid input "%(device)s". Valid devices: '
                              'NETWORK, HDD, ISCSI, UEFIHTTP or CDROM.') %
                       {'device': item})
                raise exception.IloInvalidInputError(msg)

        try:
            sushy_system.update_persistent_boot(
                devices, persistent=True)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update '
                          'persistent boot device %(devices)s.'
                          'Error: %(error)s') %
                   {'devices': devices, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def set_one_time_boot(self, device):
        """Configures a single boot from a specific device.

        :param device: Device to be set as a one time boot device
        :raises: IloError, on an error from iLO.
        :raises: IloInvalidInputError, if the given input is not valid.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        # Check if the input is valid
        if device.upper() not in DEVICE_COMMON_TO_REDFISH:
            msg = (self._('Invalid input "%(device)s". Valid devices: '
                          'NETWORK, HDD, ISCSI, UEFIHTTP or CDROM.') %
                   {'device': device})
            raise exception.IloInvalidInputError(msg)

        try:
            sushy_system.update_persistent_boot(
                [device], persistent=False)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to set '
                          'one time boot device %(device)s. '
                          'Error: %(error)s') %
                   {'device': device, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def reset_ilo_credential(self, password):
        """Resets the iLO password.

        :param password: The password to be set.
        :raises: IloError, if account not found or on an error from iLO.
        """
        try:
            acc_service = self._sushy.get_account_service()
            member = acc_service.accounts.get_member_details(self._username)
            if member is None:
                msg = (self._("No account found with username: %s")
                       % self._username)
                LOG.debug(msg)
                raise exception.IloError(msg)
            member.update_credentials(password)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update '
                          'credentials for %(username)s. Error %(error)s') %
                   {'username': self._username, 'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_supported_boot_mode(self):
        """Get the system supported boot modes.

        :return: any one of the following proliantutils.ilo.constants:

            SUPPORTED_BOOT_MODE_LEGACY_BIOS_ONLY,
            SUPPORTED_BOOT_MODE_UEFI_ONLY,
            SUPPORTED_BOOT_MODE_LEGACY_BIOS_AND_UEFI
        :raises: IloError, if account not found or on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            return SUPPORTED_BOOT_MODE_MAP.get(
                sushy_system.supported_boot_mode)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to get the '
                          'supported boot modes. Error: %s') % e)
            LOG.debug(msg)
            raise exception.IloError(msg)

    def _update_security_parameter(self, sec_param, ignore=False):
        """Sets the ignore flag for the security parameter.

        :param sec_param: Name of the security parameter.
        :param ignore : True when security parameter needs to be ignored.
               If passed False, security param will not be ignored.
               If nothing passed default will be False.
        """
        sushy_manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            security_params = (
                sushy_manager.securityservice.securityparamscollectionuri)
            param_members = security_params.get_members()
            for param in param_members:
                if sec_param in param.name:
                    param.update_security_param_ignore_status(ignore)
                    break
            else:
                msg = (self._('Specified parameter "%(param)s" is not '
                              'a Security Dashboard Parameter.') %
                       {'param': sec_param})
                raise exception.IloInvalidInputError(msg)
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller is unable to update "
                          "resource or its member. Error "
                          "%(error)s)") % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_password_complexity(self, enable=True, ignore=False):
        """Update the Password_Complexity security param.

        :param enable: A boolean param, True when Password_Complexity needs
               to be enabled. If passed False, Password_Complexity security
               param will be disabled. If nothing passed default will be True.
        :param ignore : A boolean param, True when Password_Complexity needs
               to be ignored. If passed False, Password_Complexity security
               param will not be ignored. If nothing passed default will be
               False.
        :raises: IloError, on an error from iLO.
        """
        acc_service = self._sushy.get_account_service()
        try:
            self._update_security_parameter(sec_param="Password Complexity",
                                            ignore=ignore)
            acc_service.update_enforce_passwd_complexity(enable)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update the '
                          'security dashboard parameter '
                          '``Password_Complexity``. '
                          'Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_require_login_for_ilo_rbsu(self, enable=True, ignore=False):
        """Update the RequiredLoginForiLORBSU security param.

        :param enable: A boolean param, True when RequiredLoginForiLORBSU
               needs to be enabled. If passed False, RequiredLoginForiLORBSU
               security param will be disabled. If nothing passed default
               will be True.
        :param ignore : A boolean param, True when RequiredLoginForiLORBSU
               needs to be ignored. If passed False, RequiredLoginForiLORBSU
               security param will not be ignored. If nothing passed default
               will be False.
        :raises: IloError, on an error from iLO.
        """
        sushy_manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            self._update_security_parameter(sec_param="Require Login",
                                            ignore=ignore)
            sushy_manager.update_login_for_ilo_rbsu(enable)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update the '
                          'security dashboard parameter '
                          '``RequiredLoginForiLORBSU``. '
                          'Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_require_host_authentication(self, enable=True, ignore=False):
        """Update the RequireHostAuthentication security param.

        :param enable: A boolean param, True when RequireHostAuthentication
               needs to be enabled. If passed False, RequireHostAuthentication
               security param will be disabled. If nothing passed
               default will be True.
        :param ignore : A boolean param, True when RequireHostAuthentication
               needs to be ignored. If passed False, RequireHostAuthentication
               security param will not be ignored. If nothing passed
               default will be False.
        :raises: IloError, on an error from iLO.
        """
        sushy_manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            self._update_security_parameter(sec_param="Host Authentication",
                                            ignore=ignore)
            sushy_manager.update_host_authentication(enable)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update the '
                          'security dashboard paramater '
                          '``RequireHostAuthentication``. '
                          'Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_minimum_password_length(self, passwd_length=None, ignore=False):
        """Update the MinPasswordLength security param.

        :param passwd_length: Minimum lenght of password used. If nothing
               passed default will be None.
        :param ignore : A boolean param, True when MinPasswordLength needs to
               be ignored. If passed False, MinPasswordLength security param
               will not be ignored. If nothing passed default will be False.
        """
        acc_service = self._sushy.get_account_service()
        try:
            self._update_security_parameter(sec_param="Minimum",
                                            ignore=ignore)
            acc_service.update_min_passwd_length(passwd_length)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update the '
                          'security dashboard paramater '
                          '``MinPasswordLength``. '
                          'Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_ipmi_over_lan(self, enable=False, ignore=False):
        """Update the IPMI/DCMI_Over_LAN security param.

        :param enable: A boolean param, True when IPMI/DCMI_Over_LAN needs to
               be enabled. If passed False, IPMI/DCMI_Over_LAN security param
               will be disabled. If nothing passed default will be False.
        :param ignore : A boolean param, True when IPMI/DCMI_Over_LAN needs to
               be ignored. If passed False, IPMI/DCMI_Over_LAN security param
               will not be ignored. If nothing passed default will be False.
        :raises: IloError, on an error from iLO.
        """
        sushy_manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            self._update_security_parameter(sec_param="IPMI", ignore=ignore)
            sushy_manager.networkprotocol.update_ipmi_enabled(enable)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update the '
                          'security dashboard paramater '
                          '``IPMI/DCMI_Over_LAN``. '
                          'Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_authentication_failure_logging(self, logging_threshold=None,
                                              ignore=False):
        """Update the Authentication_failure_Logging security param.

        :param logging_threshold: Value of authenication failure logging
               threshold. If nothing passed default will be None.
        :param ignore : A boolean param, True when
               Authentication_failure_Logging needs to be ignored. If passed
               False, Authentication_failure_Logging security param will not
               be ignored. If nothing passed default will be False.
        :raises: IloError, on an error from iLO.
        """
        acc_service = self._sushy.get_account_service()
        try:
            self._update_security_parameter(sec_param="Failure Logging",
                                            ignore=ignore)
            acc_service.update_auth_failure_logging(logging_threshold)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update the '
                          'security dashboard paramater '
                          '``Authentication_failure_Logging``. '
                          'Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def update_secure_boot(self, enable=True, ignore=False):
        """Update Secure_Boot security param on the server.

        :param enable: A boolean param, True when Secure_Boot needs to be
               enabled. If passed False, Secure_Boot security param will
               be disabled. If nothing passed default will be True.
        :param ignore : A boolean param, True when Secure_boot needs to be
               ignored. If passed False, Secure_boot security param will
               not be ignored. If nothing passed default will be False.
        """
        try:
            self._update_security_parameter(sec_param="Secure Boot",
                                            ignore=ignore)
            self.set_secure_boot_mode(enable)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to update the '
                          'security dashboard paramater ``Secure_boot``. '
                          'Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_security_dashboard_values(self):
        """Gets all the parameters related to security dashboard.

        :return: a dictionary of the security dashboard values
                 with their security status and security parameters
                 with their complete details and security status.
        :raises: IloError, if security dashboard or their params
            not found or on an error from iLO.
        """
        sec_capabilities = {}
        sushy_manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        try:
            security_dashboard = (
                sushy_manager.securityservice.securitydashboard)
            security_params = (
                sushy_manager.securityservice.securityparamscollectionuri)
            sec_capabilities.update(
                {'server_configuration_lock_status': (
                 security_dashboard.server_configuration_lock_status),
                 'overall_security_status': (
                 security_dashboard.overall_status)})
            security_parameters = {}
            param_members = security_params.get_members()
            for param in param_members:
                param_dict = {param.name: {'security_status': param.status,
                                           'state': param.state,
                                           'ignore': param.ignore}}
                if param.description:
                    param_dict[param.name].update(
                        {'description': param.description})
                if param.recommended_action:
                    param_dict[param.name].update(
                        {'recommended_action': param.recommended_action})
                security_parameters.update(param_dict)
            sec_capabilities.update(
                {'security_parameters': security_parameters})
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller is unable to get "
                          "resource or its members. Error "
                          "%(error)s)") % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

        return sec_capabilities

    def _parse_security_dashboard_values_for_capabilities(self):
        """Parses the security dashboard parameters.

        :returns: a dictionary of only those security parameters and their
            security status which are applicable for ironic.
        """
        values = self.get_security_dashboard_values()
        ironic_sec_capabilities = {}
        ironic_sec_capabilities.update(
            {'overall_security_status': values.get('overall_security_status')})
        param_values = values.get('security_parameters')
        p_map = {'Last Firmware Scan Result': 'last_firmware_scan_result',
                 'Security Override Switch': 'security_override_switch'}
        p_keys = p_map.keys()
        for p_key, p_val in param_values.items():
            if p_key in p_keys:
                p_dict = {p_map.get(p_key): p_val.get('security_status')}
                ironic_sec_capabilities.update(p_dict)
        return ironic_sec_capabilities

    def get_server_capabilities(self):
        """Returns the server capabilities

        raises: IloError on an error from iLO.
        """
        capabilities = {}
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        sushy_manager = self._get_sushy_manager(PROLIANT_MANAGER_ID)
        sushy_chassis = self._get_sushy_chassis(PROLIANT_CHASSIS_ID)
        try:
            count = len(sushy_system.pci_devices.gpu_devices)
            boot_mode = rf_utils.get_supported_boot_mode(
                sushy_system.supported_boot_mode)
            capabilities.update(
                {'pci_gpu_devices': count,
                 'ilo_firmware_version': sushy_manager.firmware_version,
                 'rom_firmware_version': sushy_system.rom_version,
                 'server_model': sushy_system.model,
                 'nic_capacity': sushy_system.pci_devices.max_nic_capacity,
                 'boot_mode_bios': boot_mode.boot_mode_bios,
                 'boot_mode_uefi': boot_mode.boot_mode_uefi})

            tpm_state = sushy_system.bios_settings.tpm_state
            all_key_to_value_expression_tuples = [
                ('sriov_enabled',
                 sushy_system.bios_settings.sriov == sys_cons.SRIOV_ENABLED),
                ('cpu_vt',
                 sushy_system.bios_settings.cpu_vt == (
                     sys_cons.CPUVT_ENABLED)),
                ('trusted_boot',
                 (tpm_state == sys_cons.TPM_PRESENT_ENABLED
                  or tpm_state == sys_cons.TPM_PRESENT_DISABLED)),
                ('secure_boot', self._has_secure_boot()),
                ('iscsi_boot',
                 (sushy_system.bios_settings.iscsi_resource.
                  is_iscsi_boot_supported())),
                ('hardware_supports_raid',
                 len(sushy_system.smart_storage.array_controllers.
                     members_identities) > 0),
                ('has_ssd',
                 common_storage.has_ssd(sushy_system)),
                ('has_rotational',
                 common_storage.has_rotational(sushy_system)),
                ('has_nvme_ssd',
                 common_storage.has_nvme_ssd(sushy_system))
            ]

            all_key_to_value_expression_tuples += (
                [('logical_raid_level_' + x, True)
                 for x in sushy_system.smart_storage.logical_raid_levels])

            all_key_to_value_expression_tuples += (
                [('drive_rotational_' + str(x) + '_rpm', True)
                 for x in
                 common_storage.get_drive_rotational_speed_rpm(sushy_system)])

            capabilities.update(
                {key: 'true'
                 for (key, value) in all_key_to_value_expression_tuples
                 if value})

            memory_data = sushy_system.memory.details()

            if memory_data.has_nvdimm_n:
                capabilities.update(
                    {'persistent_memory': (
                     json.dumps(memory_data.has_persistent_memory)),
                     'nvdimm_n': (
                     json.dumps(memory_data.has_nvdimm_n)),
                     'logical_nvdimm_n': (
                     json.dumps(memory_data.has_logical_nvdimm_n))})

            gpu_capabilities = gpu_common.gpu_capabilities(sushy_system,
                                                           sushy_chassis)
            for member in gpu_capabilities:
                for key in member:
                    capabilities.update(member.get(key))

            capabilities.update(
                self._parse_security_dashboard_values_for_capabilities())

        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller is unable to get "
                          "resource or its members. Error "
                          "%(error)s)") % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)
        return capabilities

    def reset_bios_to_default(self):
        """Resets the BIOS settings to default values.

        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            sushy_system.bios_settings.update_bios_to_default()
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller is unable to update bios "
                          "settings to default Error %(error)s") %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_secure_boot_mode(self):
        """Get the status of secure boot.

        :returns: True, if enabled, else False
        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is not supported
                 on the server.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            secure_boot_enabled = GET_SECUREBOOT_CURRENT_BOOT_MAP.get(
                sushy_system.secure_boot.current_boot)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to provide '
                          'information about secure boot on the server. '
                          'Error: %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloCommandNotSupportedError(msg)

        if secure_boot_enabled:
            LOG.debug(self._("Secure boot is Enabled"))
        else:
            LOG.debug(self._("Secure boot is Disabled"))
        return secure_boot_enabled

    def _has_secure_boot(self):
        try:
            self._get_sushy_system(PROLIANT_SYSTEM_ID).secure_boot
        except (exception.MissingAttributeError, sushy.exceptions.SushyError):
            return False
        return True

    def set_secure_boot_mode(self, secure_boot_enable):
        """Enable/Disable secure boot on the server.

        Resetting the server post updating this settings is needed
        from the caller side to make this into effect.
        :param secure_boot_enable: True, if secure boot needs to be
               enabled for next boot, else False.
        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is not supported
                 on the server.
        """
        if self._is_boot_mode_uefi():
            sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
            try:
                sushy_system.secure_boot.enable_secure_boot(secure_boot_enable)
            except exception.InvalidInputError as e:
                msg = (self._('Invalid input. Error %(error)s')
                       % {'error': str(e)})
                LOG.debug(msg)
                raise exception.IloError(msg)
            except sushy.exceptions.SushyError as e:
                msg = (self._('The Redfish controller failed to set secure '
                              'boot settings on the server. Error: %(error)s')
                       % {'error': str(e)})
                LOG.debug(msg)
                raise exception.IloError(msg)
        else:
            msg = (self._('System is not in UEFI boot mode. "SecureBoot" '
                          'related resources cannot be changed.'))
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def reset_secure_boot_keys(self):
        """Reset secure boot keys to manufacturing defaults.

        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is not supported
                 on the server.
        """
        if self._is_boot_mode_uefi():
            sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
            try:
                sushy_system.secure_boot.reset_keys(
                    sys_cons.SECUREBOOT_RESET_KEYS_DEFAULT)
            except sushy.exceptions.SushyError as e:
                msg = (self._('The Redfish controller failed to reset secure '
                              'boot keys on the server. Error %(error)s')
                       % {'error': str(e)})
                LOG.debug(msg)
                raise exception.IloError(msg)
        else:
            msg = (self._('System is not in UEFI boot mode. "SecureBoot" '
                          'related resources cannot be changed.'))
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def clear_secure_boot_keys(self):
        """Reset all keys.

        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is not supported
                 on the server.
        """
        if self._is_boot_mode_uefi():
            sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
            try:
                sushy_system.secure_boot.reset_keys(
                    sys_cons.SECUREBOOT_RESET_KEYS_DELETE_ALL)
            except sushy.exceptions.SushyError as e:
                msg = (self._('The Redfish controller failed to clear secure '
                              'boot keys on the server. Error %(error)s')
                       % {'error': str(e)})
                LOG.debug(msg)
                raise exception.IloError(msg)
        else:
            msg = (self._('System is not in UEFI boot mode. "SecureBoot" '
                          'related resources cannot be changed.'))
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def get_essential_properties(self):
        """Constructs the dictionary of essential properties

        Constructs the dictionary of essential properties, named
        cpu, cpu_arch, local_gb, memory_mb. The MACs are also returned
        as part of this method.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            # TODO(nisha): Add local_gb here and return after
            # local_gb changes are merged.
            # local_gb = sushy_system.storage_summary
            prop = {'memory_mb': (sushy_system.memory_summary.size_gib * 1024),
                    'cpus': sushy_system.processors.summary.count,
                    'cpu_arch': sushy_map.PROCESSOR_ARCH_VALUE_MAP_REV.get(
                    sushy_system.processors.summary.architecture),
                    'local_gb': common_storage.get_local_gb(sushy_system)}
            return {'properties': prop,
                    'macs': sushy_system.ethernet_interfaces.summary}
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to get the '
                          'resource data. Error %(error)s')
                   % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def _change_iscsi_target_settings(self, iscsi_info, macs=[]):
        """Change iSCSI target settings.

        :param macs: List of target mac for iSCSI.
        :param iscsi_info: A dictionary that contains information of iSCSI
                           target like target_name, lun, ip_address, port etc.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        association_names = []
        try:
            if macs:
                sushy_system.validate_macs(macs)
                association_names = [
                    sushy_system.get_nic_association_name_by_mac(
                        mac) for mac in macs]
            else:
                pci_settings_map = (
                    sushy_system.bios_settings.
                    bios_mappings.pci_settings_mappings)
                for mapping in pci_settings_map:
                    for subinstance in mapping['Subinstances']:
                        for association in subinstance['Associations']:
                            if 'NicBoot' in association:
                                association_names.append(association)

            if not association_names:
                msg = ('No macs were found on the system')
                raise exception.IloError(msg)

            # Set iSCSI info to all nics
            iscsi_infos = []
            for association_name in association_names:
                data = iscsi_info.copy()
                data['iSCSIAttemptName'] = association_name
                data['iSCSINicSource'] = association_name
                data['iSCSIAttemptInstance'] = (
                    association_names.index(association_name) + 1)
                iscsi_infos.append(data)

            iscsi_data = {'iSCSISources': iscsi_infos}
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to get the '
                          'bios mappings. Error %(error)s')
                   % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

        try:
            (sushy_system.bios_settings.iscsi_resource.
             iscsi_settings.update_iscsi_settings(iscsi_data))
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller is failed to update iSCSI "
                          "settings. Error %(error)s") %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def set_iscsi_info(self, target_name, lun, ip_address,
                       port='3260', auth_method=None, username=None,
                       password=None, macs=[]):
        """Set iSCSI details of the system in UEFI boot mode.

        The initiator system is set with the target details like
        IQN, LUN, IP, Port etc.
        :param target_name: Target Name for iSCSI.
        :param lun: logical unit number.
        :param ip_address: IP address of the target.
        :param port: port of the target.
        :param auth_method : either None or CHAP.
        :param username: CHAP Username for authentication.
        :param password: CHAP secret.
        :param macs: List of target macs for iSCSI.
        :raises: IloCommandNotSupportedInBiosError, if the system is
                 in the bios boot mode.
        """
        if(self._is_boot_mode_uefi()):
            iscsi_info = {}
            iscsi_info['iSCSITargetName'] = target_name
            iscsi_info['iSCSILUN'] = lun
            iscsi_info['iSCSITargetIpAddress'] = ip_address
            iscsi_info['iSCSITargetTcpPort'] = int(port)
            iscsi_info['iSCSITargetInfoViaDHCP'] = False
            iscsi_info['iSCSIConnection'] = 'Enabled'
            if (auth_method == 'CHAP'):
                iscsi_info['iSCSIAuthenticationMethod'] = 'Chap'
                iscsi_info['iSCSIChapUsername'] = username
                iscsi_info['iSCSIChapSecret'] = password
            self._change_iscsi_target_settings(iscsi_info, macs)
        else:
            msg = 'iSCSI boot is not supported in the BIOS boot mode'
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def unset_iscsi_info(self, macs=[]):
        """Disable iSCSI boot option in UEFI boot mode.

        :param macs: List of target macs for iSCSI.
        :raises: IloCommandNotSupportedInBiosError, if the system is
                 in the BIOS boot mode.
        """
        if(self._is_boot_mode_uefi()):
            iscsi_info = {'iSCSIConnection': 'Disabled'}
            self._change_iscsi_target_settings(iscsi_info, macs)
        else:
            msg = 'iSCSI boot is not supported in the BIOS boot mode'
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def set_iscsi_initiator_info(self, initiator_iqn):
        """Set iSCSI initiator information in iLO.

        :param initiator_iqn: Initiator iqn for iLO.
        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedInBiosError, if the system is
                 in the BIOS boot mode.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        if(self._is_boot_mode_uefi()):
            iscsi_data = {'iSCSIInitiatorName': initiator_iqn}
            try:
                (sushy_system.bios_settings.iscsi_resource.
                 iscsi_settings.update_iscsi_settings(iscsi_data))
            except sushy.exceptions.SushyError as e:
                msg = (self._("The Redfish controller has failed to update "
                              "iSCSI settings. Error %(error)s") %
                       {'error': str(e)})
                LOG.debug(msg)
                raise exception.IloError(msg)
        else:
            msg = 'iSCSI initiator cannot be updated in BIOS boot mode'
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def get_iscsi_initiator_info(self):
        """Give iSCSI initiator information of iLO.

        :returns: iSCSI initiator information.
        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedInBiosError, if the system is
                 in the BIOS boot mode.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        if(self._is_boot_mode_uefi()):
            try:
                iscsi_initiator = (
                    sushy_system.bios_settings.iscsi_resource.iscsi_initiator)
            except sushy.exceptions.SushyError as e:
                msg = (self._('The Redfish controller has failed to get the '
                              'iSCSI initiator. Error %(error)s')
                       % {'error': str(e)})
                LOG.debug(msg)
                raise exception.IloError(msg)
            return iscsi_initiator
        else:
            msg = 'iSCSI initiator cannot be retrieved in BIOS boot mode'
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def inject_nmi(self):
        """Inject NMI, Non Maskable Interrupt.

        Inject NMI (Non Maskable Interrupt) for a node immediately.

        :raises: IloError, on an error from iLO
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        if sushy_system.power_state != sushy.SYSTEM_POWER_STATE_ON:
            raise exception.IloError("Server is not in powered on state.")

        try:
            sushy_system.reset_system(sushy.RESET_NMI)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The Redfish controller failed to inject nmi to '
                          'server. Error %(error)s') % {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_host_post_state(self):
        """Get the current state of system POST.

        Retrieves current state of system POST.

        :returns: POST state of the server. The valida states are:-
                  null, Unknown, Reset, PowerOff, InPost,
                  InPostDiscoveryComplete and FinishedPost.
        :raises: IloError, on an error from iLO
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        return GET_POST_STATE_MAP.get(sushy_system.post_state)

    def read_raid_configuration(self, raid_config=None):
        """Read the logical drives from the system

        :param raid_config: None in case of post-delete read or in case of
                            post-create a dictionary containing target raid
                            configuration data. This data stucture should be as
                            follows:
                            raid_config = {'logical_disks': [{'raid_level': 1,
                            'size_gb': 100, 'physical_disks': ['6I:1:5'],
                            'controller': 'HPE Smart Array P408i-a SR Gen10'},
                            <info-for-logical-disk-2>]}
        :raises: IloError, on an error from iLO.
        :returns: A dictionary containing list of logical disks
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        return sushy_system.read_raid(raid_config=raid_config)

    def delete_raid_configuration(self):
        """Delete the raid configuration on the hardware."""
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        sushy_system.delete_raid()

    def do_disk_erase(self, disk_type, pattern=None):
        """Perform the out-of-band sanitize disk erase on the hardware.

        :param disk_type: Media type of disk drives either 'HDD' or 'SSD'.
        :param pattern: Erase pattern, if nothing passed default
                        ('overwrite' for 'HDD', and 'block' for 'SSD') will
                        be used.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        sushy_system.do_disk_erase(disk_type, pattern)

    def has_disk_erase_completed(self):
        """Get out-of-band sanitize disk erase status.

        :returns: True if disk erase completed on all controllers
                  otherwise False
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        return sushy_system.has_disk_erase_completed()

    def do_one_button_secure_erase(self):
        """Perform the one button secure erase on the hardware.

        The One-button secure erase process resets iLO and deletes all licenses
        stored there, resets BIOS settings, and deletes all AHS and warranty
        data stored on the system. It also erases supported non-volatile
        storage data and deletes any deployment settings profiles.

        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        sushy_system.do_one_button_secure_erase()

    def get_current_bios_settings(self, only_allowed_settings=False):
        """Get current BIOS settings.

        :param: only_allowed_settings: True when only allowed BIOS settings
                are to be returned. If False, All the BIOS settings supported
                by iLO are returned.
        :return: a dictionary of current BIOS settings is returned. Depending
                 on the 'only_allowed_settings', either only the allowed
                 settings are returned or all the supported settings are
                 returned.
        :raises: IloError, on an error from iLO
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            current_settings = sushy_system.bios_settings.json
        except sushy.exceptions.SushyError as e:
            msg = (self._('The current BIOS Settings were not found. Error '
                          '%(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

        attributes = current_settings.get("Attributes")
        if only_allowed_settings and attributes:
            return common_utils.apply_bios_properties_filter(
                attributes, ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES)
        return attributes

    def get_pending_bios_settings(self, only_allowed_settings=False):
        """Get pending BIOS settings.

        :param: only_allowed_settings: True when only allowed BIOS settings are
                to be returned. If False, All the BIOS settings supported by
                iLO are returned.
        :return: a dictionary of pending BIOS settings is returned. Depending
                 on the 'only_allowed_settings', either only the allowed
                 settings are returned or all the supported settings are
                 returned.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            settings = sushy_system.bios_settings.pending_settings.json
        except sushy.exceptions.SushyError as e:
            msg = (self._('The pending BIOS Settings were not found. Error '
                          '%(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

        attributes = settings.get("Attributes")
        if only_allowed_settings and attributes:
            return common_utils.apply_bios_properties_filter(
                attributes, ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES)
        return attributes

    def set_bios_settings(self, data=None, only_allowed_settings=False):
        """Sets current BIOS settings to the provided data.

        :param: only_allowed_settings: True when only allowed BIOS settings
                are to be set. If False, all the BIOS settings supported by
                iLO and present in the 'data' are set.
        :param: data: a dictionary of BIOS settings to be applied. Depending
                on the 'only_allowed_settings', either only the allowed
                settings are set or all the supported settings that are in the
                'data' are set.
        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is not supported
                 on the server.
        """
        if not data:
            raise exception.IloError("Could not apply settings with"
                                     " empty data")

        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        if only_allowed_settings:
            unsupported_settings = [key for key in data if key not in (
                ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES)]
            if unsupported_settings:
                msg = ("Could not apply settings as one or more settings are"
                       " not supported. Unsupported settings are %s."
                       " Supported settings are %s." % (
                           unsupported_settings,
                           ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES))
                raise exception.IloError(msg)
        try:
            settings_required = sushy_system.bios_settings.pending_settings
            settings_required.update_bios_data_by_patch(data)
        except sushy.exceptions.SushyError as e:
            msg = (self._('The pending BIOS Settings resource not found.'
                          ' Error %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def get_default_bios_settings(self, only_allowed_settings=False):
        """Get default BIOS settings.

        :param: only_allowed_settings: True when only allowed BIOS settings
                are to be returned. If False, All the BIOS settings supported
                by iLO are returned.
        :return: a dictionary of default BIOS settings(factory settings).
                 Depending on the 'only_allowed_settings', either only the
                 allowed settings are returned or all the supported settings
                 are returned.
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            settings = sushy_system.bios_settings.default_settings
        except sushy.exceptions.SushyError as e:
            msg = (self._('The default BIOS Settings were not found. Error '
                          '%(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)
        if only_allowed_settings:
            return common_utils.apply_bios_properties_filter(
                settings, ilo_cons.SUPPORTED_REDFISH_BIOS_PROPERTIES)
        return settings

    def create_raid_configuration(self, raid_config):
        """Create the raid configuration on the hardware.

        Based on user raid_config input, it will create raid

        :param raid_config: A dictionary containing target raid configuration
                            data. This data stucture should be as follows:
                            raid_config = {'logical_disks': [{'raid_level': 1,
                            'size_gb': 100, 'physical_disks': ['6I:1:5'],
                            'controller': 'HPE Smart Array P408i-a SR Gen10'},
                            <info-for-logical-disk-2>]}
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        sushy_system.create_raid(raid_config)

    def get_bios_settings_result(self):
        """Gets the result of the bios settings applied

        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is
                 not supported on the server.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            settings_result = sushy_system.bios_settings.messages
        except sushy.exceptions.SushyError as e:
            msg = (self._('The BIOS Settings results were not found. Error '
                          '%(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)
        status = "failed" if len(settings_result) > 1 else "success"
        return {"status": status, "results": settings_result}

    def get_available_disk_types(self):
        """Get the list of all disk type available in server

        :returns: A list containing disk types
        :raises: IloError, on an error from iLO.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        return sushy_system.get_disk_types()

    def get_http_boot_url(self):
        """Sets current BIOS settings to the provided data.

        :raises: IloError, on an error from iLO.
        :return: Returns the setting 'UrlBootFile' if set previously.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        url = None
        try:
            settings = sushy_system.bios_settings.json
            attributes = settings.get('Attributes')
            url = attributes.get('UrlBootFile')
        except sushy.exceptions.SushyError as e:
            msg = (self._('The attribute "UrlBootFile" not found.'
                          ' Error %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)
        return url

    def set_http_boot_url(self, url, is_dhcp_enabled=True):
        """Sets HTTP boot URL to boot from it.

        :param: url: HTTP URL of the image to be booted on the iLO.
        :param: is_dhcp_enabled: True if no static IP is set on the node and
                preferred to use DHCP service running in the network.
                If False, the MAC is expected to be configured with static IP.
        :raises: IloError, on an error from iLO.
        """
        if not url:
            raise exception.IloError("Could not set http url with"
                                     " empty URL")
        data = {
            'PreBootNetwork': 'Auto',
            'UrlBootFile': url,
            'Dhcpv4': 'Enabled' if is_dhcp_enabled else 'Disabled'
        }

        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)
        try:
            settings_required = sushy_system.bios_settings.pending_settings
            settings_required.update_bios_data_by_post(data)
        except sushy.exceptions.SushyError as e:
            msg = (self._('Could not set HTTPS URL on the iLO.'
                          ' Error %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)

    def add_tls_certificate(self, cert_file_list):
        """Adds the TLS certificates to the iLO.

        :param cert_file_list: List of TLS certificate files

        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is
                 not supported on the server.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)

        if(self._is_boot_mode_uefi()):
            cert_list = []
            for cert_file in cert_file_list:
                with open(cert_file, 'r') as f:
                    data = json.dumps(f.read())
                p = re.sub(r"\"", "", data)
                q = re.sub(r"\\n", "\r\n", p).rstrip()

                c_list = re.findall(_CERTIFICATE_PATTERN, q, re.DOTALL)

                if len(c_list) == 0:
                    LOG.warning("Could not find any valid certificate in "
                                "%(cert_file)s. Ignoring." %
                                {"cert_file": cert_file})
                    continue

                for content in c_list:
                    cert = {}
                    cert['X509Certificate'] = content
                    cert_list.append(cert)

            if len(cert_list) == 0:
                msg = (self._("No valid certificate in %(cert_file_list)s.") %
                       {"cert_file_list": cert_file_list})
                LOG.debug(msg)
                raise exception.IloError(msg)

            cert_dict = {}
            cert_dict['NewCertificates'] = cert_list
            try:
                (sushy_system.bios_settings.tls_config.
                 tls_config_settings.add_tls_certificate(cert_dict))
            except sushy.exceptions.SushyError as e:
                msg = (self._("The Redfish controller has failed to upload "
                              "TLS certificate. Error %(error)s") %
                       {'error': str(e)})
                LOG.debug(msg)
                raise exception.IloError(msg)
        else:
            msg = 'TLS certificate cannot be upload in BIOS boot mode'
            raise exception.IloCommandNotSupportedInBiosError(msg)

    def remove_tls_certificate(self, cert_file_list=[]):
        """Removes the TLS certificate from the iLO.

        :param cert_file_list: List of TLS certificate files

        :raises: IloError, on an error from iLO.
        :raises: IloCommandNotSupportedError, if the command is
                 not supported on the server.
        """
        sushy_system = self._get_sushy_system(PROLIANT_SYSTEM_ID)

        if not self._is_boot_mode_uefi():
            msg = 'TLS certificates cannot be removed in BIOS boot mode'
            raise exception.IloCommandNotSupportedInBiosError(msg)

        cert_dict = {}
        del_cert_list = []

        if not cert_file_list:
            tls_certificates = (sushy_system.bios_settings.tls_config.
                                tls_certificates)
            for cert in tls_certificates:
                fp = cert.get("FingerPrint")
                cert_fp = {
                    "FingerPrint": fp
                }
                del_cert_list.append(cert_fp)

        else:
            for cert_file in cert_file_list:
                with open(cert_file, 'r') as f:
                    data = json.dumps(f.read())
                    p = re.sub(r"\"", "", data)
                    q = re.sub(r"\\n", "\r\n", p).rstrip()

                    c_list = re.findall(_CERTIFICATE_PATTERN, q, re.DOTALL)

                    if len(c_list) == 0:
                        LOG.warning("Could not find any valid certificate in "
                                    "%(cert_file)s. Ignoring." %
                                    {"cert_file": cert_file})
                        continue

                    for content in c_list:
                        pem_lines = [line.strip() for line in (
                            content.strip().split('\n'))]

                        try:
                            der_data = b64decode(''.join(pem_lines[1:-1]))
                        except ValueError:
                            LOG.warning("Illegal base64 encountered "
                                        "in the certificate.")
                        else:
                            cert = load_certificate(FILETYPE_ASN1, der_data)
                            fp = cert.digest('sha256').decode('ascii')
                            cert_fp = {
                                "FingerPrint": fp
                            }
                            del_cert_list.append(cert_fp)

        if len(del_cert_list) == 0:
            msg = (self._("No valid certificate in %(cert_file_list)s.") %
                   {"cert_file_list": cert_file_list})
            raise exception.IloError(msg)

        cert_dict.update({"DeleteCertificates": del_cert_list})

        try:
            (sushy_system.bios_settings.tls_config.
             tls_config_settings.remove_tls_certificate(cert_dict))
        except sushy.exceptions.SushyError as e:
            msg = (self._("The Redfish controller has failed to remove "
                          "TLS certificate. Error %(error)s") %
                   {'error': str(e)})
            LOG.debug(msg)
            raise exception.IloError(msg)
