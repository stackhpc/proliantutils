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

__author__ = 'HPE'

from sushy.resources import base
from sushy import utils as sushy_utils

from proliantutils import log
from proliantutils.redfish.resources.manager import security_dashboard
from proliantutils.redfish.resources.manager import security_params


LOG = log.get_logger(__name__)


class SecurityService(base.ResourceBase):

    identity = base.Field('Id', required=True)
    """The identity for the instance."""

    security_params_collection_uri = (
        base.Field(["Links", "SecurityParams", "@odata.id"],
                   required=True))
    security_dashboard_uri = (
        base.Field(["Links", "SecurityDashboard", "@odata.id"],
                   required=True))

    @property
    @sushy_utils.cache_it
    def securitydashboard(self):
        """This property gets the instance for security dashboard

        :returns: an instance of security dashboard
        """
        return security_dashboard.SecurityDashboard(
            self._conn, self.security_dashboard_uri,
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def securityparamscollectionuri(self):
        """Gets the list of instances for security params

        :returns: the list of instances of security params.
        """
        return security_params.SecurityParamsCollection(
            self._conn, self.security_params_collection_uri,
            redfish_version=self.redfish_version)
