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

from proliantutils import exception
from proliantutils.redfish.resources.account_service import account
from proliantutils.redfish import utils

DEFAULT_PASSWORD_LENGTH = 8
DEFAULT_AUTH_FAIL_LOGGING = 1


class HPEAccountService(base.ResourceBase):
    """Class that extends the functionality of AccountService resource class

    This class extends the functionality of Account resource class
    from sushy
    """
    min_passwd_length = base.Field(["Oem", "Hpe", "MinPasswordLength"])
    enforce_passwd_complexity = base.Field(
        ["Oem", "Hpe", "EnforcePasswordComplexity"])

    @property
    @sushy_utils.cache_it
    def accounts(self):
        """Property to provide instance of HPEAccountCollection"""
        return account.HPEAccountCollection(
            self._conn, utils.get_subresource_path_by(self, 'Accounts'),
            redfish_version=self.redfish_version)

    def update_min_passwd_length(self, passwd_length):
        if passwd_length is None:
            passwd_length = DEFAULT_PASSWORD_LENGTH
        valid_lengths = list(range(40))
        if (passwd_length not in valid_lengths):
            raise exception.InvalidParameterValueError(
                parameter='MinPasswordLength', value=passwd_length,
                valid_values='0 to 39')
        p_data = {"Oem": {"Hpe": {"MinPasswordLength": passwd_length}}}
        self._conn.patch(self.path, data=p_data)

    def update_enforce_passwd_complexity(self, enable):
        if not isinstance(enable, bool):
            msg = ('The parameter "%(parameter)s" value "%(value)s" is '
                   'invalid. Valid values are: True/False.' %
                   {'parameter': 'enable', 'value': enable})
            raise exception.InvalidInputError(msg)

        data = {"Oem": {"Hpe": {"EnforcePasswordComplexity": enable}}}
        self._conn.patch(self.path, data=data)

    def update_auth_failure_logging(self, logging_threshold):
        if logging_threshold is None:
            logging_threshold = DEFAULT_AUTH_FAIL_LOGGING
        valid_values = [0, 1, 2, 3, 5]
        if (logging_threshold not in valid_values):
            raise exception.InvalidParameterValueError(
                parameter='AuthFailureLoggingThreshold',
                value=logging_threshold, valid_values=valid_values)
        p_data = {"Oem": {"Hpe": {
                  "AuthFailureLoggingThreshold": logging_threshold}}}
        self._conn.patch(self.path, data=p_data)
