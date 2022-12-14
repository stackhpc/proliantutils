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

from proliantutils import exception
from proliantutils import log

LOG = log.get_logger(__name__)


class SecurityParams(base.ResourceBase):

    identity = base.Field('Id', required=True)
    """The identity for the instance."""

    status = base.Field('SecurityStatus', required=True)
    """Security status of the server"""

    name = base.Field('Name', required=True)
    state = base.Field('State', required=True)
    ignore = base.Field('Ignore', required=True)
    description = base.Field('Description')
    recommended_action = base.Field('RecommendedAction')

    def update_security_param_ignore_status(self, ignore):
        if not isinstance(ignore, bool):
            msg = ('The parameter "%(parameter)s" value "%(value)s" is '
                   'invalid. Valid values are: True/False.' %
                   {'parameter': 'ignore', 'value': ignore})
            raise exception.InvalidInputError(msg)
        data = {"Ignore": ignore}
        self._conn.patch(self.path, data=data)


class SecurityParamsCollection(base.ResourceCollectionBase):

    @property
    def _resource_type(self):
        return SecurityParams
