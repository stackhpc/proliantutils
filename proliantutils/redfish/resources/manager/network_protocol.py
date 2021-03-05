# Copyright 2021 Hewlett Packard Enterprise Development LP
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


class NetworkProtocol(base.ResourceBase):

    identity = base.Field('Id', required=True)
    """The identity for the instance."""

    name = base.Field("Name")
    """Name of the service"""

    ipmi_enabled = base.Field(["IPMI", "ProtocolEnabled"])
    """True if IPMI network protocol is enabled else False"""

    def update_ipmi_enabled(self, enable):
        if not isinstance(enable, bool):
            msg = ('The parameter "%(parameter)s" value "%(value)s" is '
                   'invalid. Valid values are: True/False.' %
                   {'parameter': 'enable', 'value': enable})
            raise exception.InvalidInputError(msg)

        ipmi_data = {"IPMI": {"ProtocolEnabled": enable}}
        self._conn.patch(self.path, data=ipmi_data)
