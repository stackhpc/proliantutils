# Copyright 2017 Hewlett Packard Enterprise Development LP
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

import sushy
from sushy.resources import base
from sushy import utils as sushy_utils

from proliantutils import exception
from proliantutils import log
from proliantutils.redfish.resources.system import constants as sys_cons
from proliantutils.redfish.resources.system import iscsi
from proliantutils.redfish.resources.system import mappings
from proliantutils.redfish.resources.system import tls_config
from proliantutils.redfish import utils

LOG = log.get_logger(__name__)

BOOT_SOURCE_TARGET_TO_PARTIAL_STRING_MAP = {
    sushy.BOOT_SOURCE_TARGET_CD: ('HPE Virtual CD-ROM',),
    sushy.BOOT_SOURCE_TARGET_PXE: ('NIC', 'PXE'),
    sushy.BOOT_SOURCE_TARGET_UEFI_TARGET: ('ISCSI',),
    sushy.BOOT_SOURCE_TARGET_HDD: ('Logical Drive', 'HDD', 'Storage', 'LogVol')
}


class BIOSSettings(base.ResourceBase):
    """Class that defines the functionality for BIOS Resources."""

    messages = base.Field(['@Redfish.Settings', 'Messages'])
    boot_mode = base.MappedField(["Attributes", "BootMode"],
                                 mappings.GET_BIOS_BOOT_MODE_MAP)

    sriov = base.MappedField(['Attributes', 'Sriov'], mappings.SRIOV_MAP)

    tpm_state = base.MappedField(["Attributes", "TpmState"], mappings.TPM_MAP)

    cpu_vt = base.MappedField(["Attributes", "ProcVirtualization"],
                              mappings.CPUVT_MAP)

    @property
    @sushy_utils.cache_it
    def pending_settings(self):
        """Property to provide reference to bios_pending_settings instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return BIOSPendingSettings(
            self._conn, utils.get_subresource_path_by(
                self, ["@Redfish.Settings", "SettingsObject"]),
            redfish_version=self.redfish_version)

    @property
    def default_settings(self):
        """Property to provide default BIOS settings

        It gets the current default settings on the node.
        """
        return self._get_base_configs().default_config

    @property
    @sushy_utils.cache_it
    def boot_settings(self):
        """Property to provide reference to bios boot instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return BIOSBootSettings(
            self._conn, utils.get_subresource_path_by(
                self, ["Oem", "Hpe", "Links", "Boot"]),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def iscsi_resource(self):
        """Property to provide reference to bios iscsi resource instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return iscsi.ISCSIResource(
            self._conn, utils.get_subresource_path_by(
                self, ["Oem", "Hpe", "Links", "iScsi"]),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def tls_config(self):
        """Property to provide reference to BIOS TLS configuration instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return tls_config.TLSConfig(
            self._conn, utils.get_subresource_path_by(
                self, ["Oem", "Hpe", "Links", "TlsConfig"]),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def bios_mappings(self):
        """Property to provide reference to bios mappings instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return BIOSMappings(
            self._conn, utils.get_subresource_path_by(
                self, ["Oem", "Hpe", "Links", "Mappings"]),
            redfish_version=self.redfish_version)

    @sushy_utils.cache_it
    def _get_base_configs(self):
        """Method that returns object of bios base configs."""
        return BIOSBaseConfigs(
            self._conn, utils.get_subresource_path_by(
                self, ["Oem", "Hpe", "Links", "BaseConfigs"]),
            redfish_version=self.redfish_version)

    def update_bios_to_default(self):
        """Updates bios default settings"""
        self.pending_settings.update_bios_data_by_post(
            self._get_base_configs().default_config)


class BIOSBaseConfigs(base.ResourceBase):
    """Class that defines the functionality for BIOS base configuration."""

    default_config = base.Field(
        "BaseConfigs", adapter=lambda base_configs: base_configs[0]['default'])


class BIOSPendingSettings(base.ResourceBase):
    """Class that defines the functionality for BIOS pending settings."""

    boot_mode = base.MappedField(["Attributes", "BootMode"],
                                 mappings.GET_BIOS_BOOT_MODE_MAP)

    def set_pending_boot_mode(self, boot_mode):
        """Sets the boot mode of the system for next boot.

        :param boot_mode: either sys_cons.BIOS_BOOT_MODE_LEGACY_BIOS,
         sys_cons.BIOS_BOOT_MODE_UEFI.
        """
        bios_properties = {
            'BootMode': mappings.GET_BIOS_BOOT_MODE_MAP_REV.get(boot_mode)
        }

        if boot_mode == sys_cons.BIOS_BOOT_MODE_UEFI:
            bios_properties['UefiOptimizedBoot'] = 'Enabled'

        self.update_bios_data_by_patch(bios_properties)

    def update_bios_data_by_post(self, data):
        """Update bios data by post

        :param data: default bios config data
        """
        bios_settings_data = {
            'Attributes': data
        }
        self._conn.post(self.path, data=bios_settings_data)

    def update_bios_data_by_patch(self, data):
        """Update bios data by patch

        :param data: default bios config data
        """
        bios_settings_data = {
            'Attributes': data
        }
        self._conn.patch(self.path, data=bios_settings_data)


class BIOSBootSettings(base.ResourceBase):

    boot_sources = base.Field("BootSources", adapter=list)
    persistent_boot_config_order = base.Field("PersistentBootConfigOrder",
                                              adapter=list)

    def get_persistent_boot_device(self):
        """Get current persistent boot device set for the host

        :returns: persistent boot device for the system
        :raises: IloError, on an error from iLO.
        """
        boot_string = None
        if not self.persistent_boot_config_order or not self.boot_sources:
            msg = ('Boot sources or persistent boot config order not found')
            LOG.debug(msg)
            raise exception.IloError(msg)

        preferred_boot_device = self.persistent_boot_config_order[0]
        for boot_source in self.boot_sources:
            if ((boot_source.get("StructuredBootString") is not None) and (
                    preferred_boot_device
                    == boot_source.get("StructuredBootString"))):
                boot_string = boot_source["BootString"]
                break
        else:
            msg = (('Persistent boot device failed, as no matched boot '
                    'sources found for device: %(persistent_boot_device)s')
                   % {'persistent_boot_device': preferred_boot_device})
            LOG.debug(msg)
            raise exception.IloError(msg)

        for key, value in BOOT_SOURCE_TARGET_TO_PARTIAL_STRING_MAP.items():
            for val in value:
                if val in boot_string:
                    return key
        return sushy.BOOT_SOURCE_TARGET_NONE

    def get_uefi_boot_string(self, mac):
        """Get uefi iscsi boot string for the host

        :returns: iscsi boot string for the system
        :raises: IloError, on an error from iLO.
        """
        boot_sources = self.boot_sources
        if not boot_sources:
            msg = ('Boot sources are not found')
            LOG.debug(msg)
            raise exception.IloError(msg)

        for boot_source in boot_sources:
            if (mac.upper() in boot_source['UEFIDevicePath']
                    and 'iSCSI' in boot_source['UEFIDevicePath']):
                return boot_source['StructuredBootString']
        else:
            msg = ('MAC provided "%s" is Invalid' % mac)
            raise exception.IloInvalidInputError(msg)


class BIOSMappings(base.ResourceBase):
    """Class that defines the functionality for BIOS mappings."""

    pci_settings_mappings = base.Field("BiosPciSettingsMappings",
                                       adapter=list)
