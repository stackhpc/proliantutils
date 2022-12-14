# Copyright 2017 Hewlett Packard Enterprise Development LP
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

from sushy.resources import base
from sushy import utils as sushy_utils

from proliantutils.redfish.resources.system.storage import mappings
from proliantutils.redfish import utils


class HPELogicalDrive(base.ResourceBase):
    """This class represents the LogicalDrives resource"""

    identity = base.Field('Id')

    name = base.Field('Name')

    description = base.Field('Description')

    capacity_mib = base.Field('CapacityMiB', adapter=int)

    raid = base.MappedField('Raid', mappings.RAID_LEVEL_MAP)


class HPELogicalDriveCollection(base.ResourceCollectionBase):
    """This class represents the collection of LogicalDrives resource"""

    @property
    def _resource_type(self):
        return HPELogicalDrive

    @property
    @sushy_utils.cache_it
    def maximum_size_mib(self):
        """Gets the biggest logical drive

        :returns size in MiB.
        """
        return utils.max_safe([member.capacity_mib
                               for member in self.get_members()])

    @property
    @sushy_utils.cache_it
    def logical_raid_levels(self):
        """Gets the raid level for each logical volume

        :returns the set of list of raid levels configured.
        """
        lg_raid_lvls = set()
        for member in self.get_members():
            lg_raid_lvls.add(mappings.RAID_LEVEL_MAP_REV.get(member.raid))
        return lg_raid_lvls
