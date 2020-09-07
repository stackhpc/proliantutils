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
from sushy.resources.manager import manager
from sushy import utils as sushy_utils

from proliantutils import exception
from proliantutils.redfish.resources.manager import network_protocol
from proliantutils.redfish.resources.manager import security_service
from proliantutils.redfish.resources.manager import virtual_media
from proliantutils.redfish import utils


class HPEManager(manager.Manager):
    """Class that extends the functionality of Manager resource class

    This class extends the functionality of Manager resource class
    from sushy
    """
    required_login_foriLORBSU = base.Field(
        ["Oem", "Hpe", "RequiredLoginForiLORBSU"])
    require_host_authentication = base.Field(
        ["Oem", "Hpe", "RequireHostAuthentication"])

    def set_license(self, key):
        """Set the license on a redfish system

        :param key: license key
        """
        data = {'LicenseKey': key}
        license_service_uri = (utils.get_subresource_path_by(self,
                               ['Oem', 'Hpe', 'Links', 'LicenseService']))
        self._conn.post(license_service_uri, data=data)

    @property
    @sushy_utils.cache_it
    def virtual_media(self):
        """Property to provide reference to `VirtualMediaCollection` instance.

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return virtual_media.VirtualMediaCollection(
            self._conn, utils.get_subresource_path_by(self, 'VirtualMedia'),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def securityservice(self):
        return security_service.SecurityService(
            self._conn, utils.get_subresource_path_by(
                self, ['Oem', 'Hpe', 'Links', 'SecurityService']),
            redfish_version=self.redfish_version)

    @property
    @sushy_utils.cache_it
    def networkprotocol(self):
        return network_protocol.NetworkProtocol(
            self._conn, utils.get_subresource_path_by(self, 'NetworkProtocol'),
            redfish_version=self.redfish_version)

    def update_login_for_ilo_rbsu(self, enable):
        if not isinstance(enable, bool):
            msg = ('The parameter "%(parameter)s" value "%(value)s" is '
                   'invalid. Valid values are: True/False.' %
                   {'parameter': 'enable', 'value': enable})
            raise exception.InvalidInputError(msg)

        data = {"Oem": {"Hpe": {"RequiredLoginForiLORBSU": enable}}}
        self._conn.patch(self.path, data=data)

    def update_host_authentication(self, enable):
        if not isinstance(enable, bool):
            msg = ('The parameter "%(parameter)s" value "%(value)s" is '
                   'invalid. Valid values are: True/False.' %
                   {'parameter': 'enable', 'value': enable})
            raise exception.InvalidInputError(msg)

        data = {"Oem": {"Hpe": {"RequireHostAuthentication": enable}}}
        self._conn.patch(self.path, data=data)
