# Copyright 2020 Hewlett Packard Enterprise Development LP
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

import sushy
from sushy.resources import base
from sushy.resources import common as sushy_common

from proliantutils import exception
from proliantutils.ilo import common
from proliantutils import log

LOG = log.get_logger(__name__)


class ActionsField(base.CompositeField):
    generate_csr = (sushy_common.
                    ResetActionField('#HpeHttpsCert.GenerateCSR'))
    import_cert = (sushy_common.
                   ResetActionField('#HpeHttpsCert.ImportCertificate'))


class HttpsCert(base.ResourceBase):

    cert_sign_request = base.Field('CertificateSigningRequest', required=True)
    _actions = ActionsField(['Actions'], required=True)

    def _get_https_cert_uri(self, cert_func):
        """Get the url for generating CSR

        :returns: generate csr url
        :raises: Missing resource error on missing url
        """
        url = self._actions[cert_func]
        if not url:
            if cert_func == 'generate_csr':
                missing_action = '#HpeHttpsCert.GenerateCSR'
            else:
                missing_action = '#HpeHttpsCert.ImportCertificate'
            raise (sushy.exceptions.
                   MissingActionError(action=missing_action,
                                      resource=self._path))
        return url

    def import_certificate(self, cert):
        """Adds the signed https certificate to the iLO.

        :param certificate: Signed HTTPS certificate.
        :raises: IloError, on an error from iLO.
        """
        action_data = {
            "Certificate": cert
        }

        target_uri = self._get_https_cert_uri('import_cert').target_uri
        try:
            self._conn.post(target_uri, data=action_data)
        except sushy.exceptions.SushyError as e:
            msg = (('The Redfish controller failed to import '
                    'certificate. Error: %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)  # noqa
            raise exception.IloError(msg)

    def generate_csr(self, csr_params):
        """Generates the certificate signing request.

        :param csr_params: A dictionary containing all the necessary
               information required to create CSR.
        :returns: Created CSR.
        :raises: IloError, on an error from iLO.
        """
        target_uri = self._get_https_cert_uri('generate_csr').target_uri
        try:
            self._conn.post(target_uri, data=csr_params)
        except sushy.exceptions.SushyError as e:
            msg = (('The Redfish controller failed to generate CSR '
                    'with given information. Error: %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)  # noqa
            raise exception.IloError(msg)

        self.wait_for_csr_to_create()

        csr = self.cert_sign_request

        return csr

    def wait_for_csr_to_create(self):
        """Continuosly polls for CSR to create.

        """

        def has_csr_created():
            """Check whether CSR is created.

            :returns: True upon successful creation of CSR otherwise False.
            """
            self.get_generate_csr_refresh()

            csr = self.cert_sign_request

            if not csr:
                return False
            return True

        common.wait_for_operation_to_complete(
            has_csr_created, delay_bw_retries=30,
            failover_msg='Generating CSR has failed.'
        )

    def get_generate_csr_refresh(self):
        # perform refresh
        try:
            self.refresh()
        except sushy.exceptions.SushyError as e:
            msg = (('Generating CSR progress not known. '
                    'Error: %(error)s') %
                   {'error': str(e)})
            LOG.debug(msg)
