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

from sushy.resources import base
from sushy import utils as sushy_utils

from proliantutils.redfish import utils


class TLSConfig(base.ResourceBase):
    """Class that represents the TLS Configuration.

    This class extends the functionality of base resource class
    from sushy.
    """

    tls_certificates = base.Field('Certificates')
    """The certificates currently configured"""

    @property
    @sushy_utils.cache_it
    def tls_config_settings(self):
        """Property to provide reference to TLS configuration settings instance

        It is calculated once when the first time it is queried. On refresh,
        this property gets reset.
        """
        return TLSConfigSettings(
            self._conn,
            utils.get_subresource_path_by(
                self, ["@Redfish.Settings", "SettingsObject"]),
            redfish_version=self.redfish_version)


class TLSConfigSettings(base.ResourceBase):
    """Class that represents the TLS configuration settings.

    This class extends the functionality of base resource class
    from sushy.
    """

    def add_tls_certificate(self, cert_data):
        """Update tls certificate

        :param data: default tls certs data
        """
        self._conn.put(self.path, data=cert_data)

    def remove_tls_certificate(self, cert_data):
        """Update tls certificate

        :param data: default tls certs data
        """
        self._conn.put(self.path, data=cert_data)
