import json
import copy
import httplib

import requests

__all__ = [
    'PuppetHTTPAPIClient'
]


class PuppetHTTPAPIClient(object):
    BASE_GET_HEADERS = {
        'Accept': 'text/pson'
    }
    BASE_POST_HEADERS = {
        'Content-Type': 'text/pson'
    }

    def __init__(self, master_hostname, master_port, client_cert_path,
                 client_cert_key_path, ca_cert_path=None):
        """
        :param master_hostname: Puppet master hostname or IP address.
        :type master_hostname: ``str``

        :param master_port: Puppet master port.
        :type master_port: ``int``

        :param client_cert_path: Path to the client certificate which is used
                                 for authentication.
        :type client_cert_path: ``str``

        :param client_cert_key_path: Path to the private key for the client
                                     certificate.
        :type client_cert_key_path: ``str``

        :param ca_cert_path: Path to the CA certificate file. Note: If path to
                             CA certificate file is not specified, no cert
                             verification is performed.
        :type ca_cert_path: ``str``
        """
        self._master_hostname = master_hostname
        self._master_port = master_port
        self._client_cert_path = client_cert_path
        self._client_cert_key_path = client_cert_key_path
        self._ca_cert_path = ca_cert_path

        self._base_url = 'https://%s:%s' % (self._master_hostname,
                                            self._master_port)

    def cert_sign(self, environment, host):
        """
        Sign a certificate.

        :param environment: Environment to operate on.
        :type environment: ``str``

        :param host: Host to sign the certificate for.
        :type host: ``str``

        :rtype: ``bool``
        """
        path = '/%s/certificate_status/%s/' % (environment, host)
        method = 'PUT'
        payload = {'desired_state': 'signed'}
        response = self._request(path=path, method=method, payload=payload)
        return response.status_code in [httplib.OK]

    def cert_revoke(self, environment, host):
        """
        Revoke a certificate.

        :param environment: Environment to operate on.
        :type environment: ``str``

        :param host: Host to revoke the certificate for.
        :type host: ``str``
        """
        path = '/%s/certificate_status/%s/' % (environment, host)
        method = 'PUT'
        payload = {'desired_state': 'revoked'}
        response = self._request(path=path, method=method, payload=payload)
        return response.status_code in [httplib.OK]

    def cert_clean(self, environment, host):
        """
        Clean a certificate.

        :param environment: Environment to operate on.
        :type environment: ``str``

        :param host: Host to clean the certificate for.
        :type host: ``str``
        """
        status1 = self.cert_revoke(environment=environment, host=host)
        status2 = self.cert_discard_info(environment=environment, host=host)
        return status1 and status2

    def cert_discard_info(self, environment, host):
        """
        Cause the certificate authority to discard all SSL information
        regarding a host (including any certificates, certificate requests,
        and keys). This does not revoke the certificate if one is present.

        :param environment: Environment to operate on.
        :type environment: ``str``

        :param host: Host to discard the certificate info for.
        :type host: ``str``
        """
        path = '/%s/certificate_status/%s/' % (environment, host)
        method = 'DELETE'
        response = self._request(path=path, method=method)
        return response.status_code in [httplib.OK]

    def _request(self, path, method='GET', headers=None, payload=None):
        url = self._base_url + path

        request_headers = copy.deepcopy(self.BASE_GET_HEADERS)

        if method.upper in ['POST', 'PUT']:
            request_headers.update(self.BASE_POST_HEADERS)

        if headers:
            request_headers.update(headers)

        if payload:
            data = json.dumps(payload)
        else:
            data = None

        cert = (self._client_cert_path, self._client_cert_key_path)

        if self._ca_cert_path:
            verify = self._ca_cert_path
        else:
            verify = False

        response = requests.request(url=url, method=method,
                                    headers=request_headers, data=data,
                                    cert=cert, verify=verify)
        return response
