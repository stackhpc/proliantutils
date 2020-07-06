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

from ironic_python_agent import hardware

from proliantutils.hpssa import manager as hpssa_manager
from proliantutils import log
from proliantutils.sum import sum_controller

LOG = log.get_logger(__name__)

_RAID_APPLY_CONFIGURATION_ARGSINFO = {
    "raid_config": {
        "description": "The RAID configuration to apply.",
        "required": True,
    },
    "delete_existing": {
        "description": (
            "Setting this to 'True' indicates to delete existing RAID "
            "configuration prior to creating the new configuration. "
            "Default value is 'True'."
        ),
        "required": False,
    }
}

_FIRMWARE_UPDATE_SUM_ARGSINFO = {
    'url': {
        'description': (
            "The image location for SPP (Service Pack for Proliant) ISO."
        ),
        'required': True,
    },
    'checksum': {
        'description': (
            "The md5 checksum of the SPP image file."
        ),
        'required': True,
    },
    'components': {
        'description': (
            "The list of firmware component filenames. If not specified, "
            "SUM updates all the firmware components."
        ),
        'required': False,
    }
}


class ProliantHardwareManager(hardware.GenericHardwareManager):

    HARDWARE_MANAGER_VERSION = "3"

    def get_clean_steps(self, node, ports):
        """Return the clean steps supported by this hardware manager.

        This method returns the clean steps that are supported by
        proliant hardware manager.  This method is invoked on every
        hardware manager by Ironic Python Agent to give this information
        back to Ironic.

        :param node: A dictionary of the node object
        :param ports: A list of dictionaries containing information of ports
            for the node
        :returns: A list of dictionaries, each item containing the step name,
            interface and priority for the clean step.
        """
        return [
            {
                'step': 'create_configuration',
                'interface': 'raid',
                'priority': 0,
                'reboot_requested': False,
            },
            {
                'step': 'delete_configuration',
                'interface': 'raid',
                'priority': 0,
                'reboot_requested': False,
            },
            {
                'step': 'erase_devices',
                'interface': 'deploy',
                'priority': 0,
                'reboot_requested': False,
            },
            {
                'step': 'update_firmware_sum',
                'interface': 'management',
                'priority': 0,
                'reboot_requested': False,
            },
        ]

    def get_deploy_steps(self, node, ports):
        """Return the deploy steps supported by this hardware manager.

        This method returns the deploy steps that are supported by
        proliant hardware manager.  This method is invoked on every
        hardware manager by Ironic Python Agent to give this information
        back to Ironic.

        :param node: A dictionary of the node object
        :param ports: A list of dictionaries containing information of ports
            for the node
        :returns: A list of dictionaries, each item containing the step name,
            interface, priority, reboot_requested and
            argsinfo for the deploy step.
        """
        return [
            {
                'step': 'apply_configuration',
                'interface': 'raid',
                'priority': 0,
                'reboot_requested': False,
                'argsinfo': _RAID_APPLY_CONFIGURATION_ARGSINFO,
            },
            {
                'step': 'flash_firmware_sum',
                'interface': 'management',
                'priority': 0,
                'reboot_requested': False,
                'argsinfo': _FIRMWARE_UPDATE_SUM_ARGSINFO,
            },
        ]

    def evaluate_hardware_support(cls):
        return hardware.HardwareSupport.SERVICE_PROVIDER

    def apply_configuration(self, node, ports, raid_config,
                            delete_existing=True):
        """Apply RAID configuration.

        :param node: A dictionary of the node object.
        :param ports: A list of dictionaries containing information
                      of ports for the node.
        :param raid_config: The configuration to apply.
        :param delete_existing: Whether to delete the existing configuration.
        :returns: The current RAID configuration of the below format.
            raid_config = {
                'logical_disks': [{
                    'size_gb': 100,
                    'raid_level': 1,
                    'physical_disks': [
                        '5I:0:1',
                        '5I:0:2'],
                    'controller': 'Smart array controller'
                    },
                ]
            }
        """
        if delete_existing:
            self.delete_configuration(node, ports)
        LOG.debug("Creating raid with configuration %(raid_config)s",
                  {'raid_config': raid_config})
        return hpssa_manager.create_configuration(raid_config=raid_config)

    def create_configuration(self, node, ports):
        """Create RAID configuration on the bare metal.

        This method creates the desired RAID configuration as read from
        node['target_raid_config'].

        :param node: A dictionary of the node object
        :param ports: A list of dictionaries containing information of ports
            for the node
        :returns: The current RAID configuration of the below format.
            raid_config = {
                'logical_disks': [{
                    'size_gb': 100,
                    'raid_level': 1,
                    'physical_disks': [
                        '5I:0:1',
                        '5I:0:2'],
                    'controller': 'Smart array controller'
                    },
                ]
            }
        """
        target_raid_config = node.get('target_raid_config', {}).copy()
        if not target_raid_config:
            LOG.debug("No target_raid_config found")
            return {}

        LOG.debug("Creating raid with configuration %(raid_config)s",
                  {'raid_config': target_raid_config})
        return hpssa_manager.create_configuration(
            raid_config=target_raid_config)

    def delete_configuration(self, node, ports):
        """Deletes RAID configuration on the bare metal.

        This method deletes all the RAID disks on the bare metal.
        :param node: A dictionary of the node object
        :param ports: A list of dictionaries containing information of ports
            for the node
        """
        return hpssa_manager.delete_configuration()

    def erase_devices(self, node, port):
        """Erase the drives on the bare metal.

        This method erase all the drives which supports sanitize and the drives
        which are not part of any logical volume on the bare metal. It calls
        generic erase method after the success of Sanitize disk erase.
        :param node: A dictionary of the node object.
        :param port: A list of dictionaries containing information of ports
            for the node.
        :raises exception.HPSSAOperationError, if there is a failure on the
            erase operation on the controllers.
        :returns: The dictionary of controllers with the drives and erase
            status for each drive.
        """
        result = {}
        result['Disk Erase Status'] = hpssa_manager.erase_devices()

        result.update(super(ProliantHardwareManager,
                            self).erase_devices(node, port))
        return result

    def update_firmware_sum(self, node, port):
        """Performs SUM based firmware update on the bare metal node.

        This method performs firmware update on all or some of the firmware
        components on the bare metal node.
        :param node: A dictionary of the node object.
        :param port: A list of dictionaries containing information of ports
            for the node.
        :returns: A string with return code and the statistics of
            updated/failed components.
        :raises: SUMOperationError, when the SUM based firmware update
            operation on the node fails.
        """
        url = node['clean_step']['args'].get('url')
        checksum = node['clean_step']['args'].get('checksum')
        components = node['clean_step']['args'].get('components')
        return sum_controller.update_firmware(node, url, checksum,
                                              components=components)

    def flash_firmware_sum(self, node, port, url,
                           checksum, components=None):
        """Performs SUM based firmware update on the bare metal node.

        This method performs firmware update on all or some of the firmware
        components on the bare metal node.
        :param node: A dictionary of the node object.
        :param port: A list of dictionaries containing information of ports
            for the node.
        :param url: URL of SPP (Service Pack for Proliant) ISO.
        :param checksum: MD5 checksum of SPP ISO to verify the image.
        :param components: List of filenames of the firmware components to be
            flashed. If not provided, the firmware update is performed on all
            the firmware components.
        :returns: A string with return code and the statistics of
            updated/failed components.
        :raises: SUMOperationError, when the SUM based firmware update
            operation on the node fails.
        """
        LOG.debug("Flashing firmware from %(url)s for components %(comp)s",
                  {'url': url, 'comp': components})
        return sum_controller.update_firmware(node, url, checksum,
                                              components=components)
