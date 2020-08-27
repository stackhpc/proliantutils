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


class SecurityDashboard(base.ResourceBase):

    identity = base.Field('Id', required=True)
    """The identity for the instance."""

    overall_status = base.Field('OverallSecurityStatus', required=True)
    """Overall security status of the server"""

    server_configuration_lock_status = (
        base.Field('ServerConfigurationLockStatus', required=True))

    security_param_uri = base.Field(["SecurityParameters", "@odata.id"])
