import base64
import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta

import jwt
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key, pkcs12
from OpenSSL import crypto


class Decorators:
    """
    Decorators class for handling token refreshing
    for Microsoft Graph and Sharepoint Rest API
    """

    @staticmethod
    def refresh_graph_token(decorated):
        """
        Decorator to refresh the graph access token if it has expired
        """

        def wrapper(*args, **kwargs):
            """
            Wrapper function
            """
            if "GRAPH_BEARER_TOKEN_EXPIRES_AT" not in os.environ:
                expires_at = "01/01/1901 00:00:00"
            else:
                expires_at = os.environ["GRAPH_BEARER_TOKEN_EXPIRES_AT"]
            if (
                "GRAPH_BEARER_TOKEN" not in os.environ
                or datetime.strptime(expires_at, "%m/%d/%Y %H:%M:%S") < datetime.now()
            ):
                Decorators.get_graph_token()
            return decorated(*args, **kwargs)

        wrapper.__name__ = decorated.__name__
        return wrapper

    @staticmethod
    def refresh_sp_token(decorated):
        """
        Decorator to refresh the sharepoint rest API access token if it has expired
        """

        def wrapper(*args, **kwargs):
            """
            Wrapper function
            """
            if "SP_BEARER_TOKEN_EXPIRES_AT" not in os.environ:
                expires_at = "01/01/1901 00:00:00"
            else:
                expires_at = os.environ["SP_BEARER_TOKEN_EXPIRES_AT"]
            if (
                "SP_BEARER_TOKEN" not in os.environ
                or datetime.strptime(expires_at, "%m/%d/%Y %H:%M:%S") < datetime.now()
            ):
                Decorators.get_sp_token()
            return decorated(*args, **kwargs)

        wrapper.__name__ = decorated.__name__
        return wrapper

    @staticmethod
    def get_graph_token():
        """
        Get Microsoft Graph bearer token
        """
        if "GRAPH_LOGIN_BASE_URL" not in os.environ:
            raise Exception("Error, could not find GRAPH_LOGIN_BASE_URL in env")
        if "GRAPH_TENANT_ID" not in os.environ:
            raise Exception("Error, could not find GRAPH_TENANT_ID in env")
        if "GRAPH_CLIENT_ID" not in os.environ:
            raise Exception("Error, could not find GRAPH_CLIENT_ID in env")
        if "GRAPH_CLIENT_SECRET" not in os.environ:
            raise Exception("Error, could not find GRAPH_CLIENT_SECRET in env")
        if "GRAPH_GRANT_TYPE" not in os.environ:
            raise Exception("Error, could not find GRAPH_GRANT_TYPE in env")
        if "GRAPH_SCOPES" not in os.environ:
            raise Exception("Error, could not find GRAPH_SCOPES in env")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(
            os.environ["GRAPH_LOGIN_BASE_URL"]
            + os.environ["GRAPH_TENANT_ID"]
            + "/oauth2/v2.0/token",
            headers=headers,
            data={
                "client_id": os.environ["GRAPH_CLIENT_ID"],
                "client_secret": os.environ["GRAPH_CLIENT_SECRET"],
                "grant_type": os.environ["GRAPH_GRANT_TYPE"],
                "scope": os.environ["GRAPH_SCOPES"],
            },
            timeout=30,
        )
        try:
            os.environ["GRAPH_BEARER_TOKEN"] = response.json()["access_token"]
        except Exception as e:
            raise Exception(
                "Error, could not set OS env bearer token: " + str(response.content)
            )
        try:
            expires_at = datetime.now() + timedelta(
                seconds=response.json()["expires_in"]
            )
            os.environ["GRAPH_BEARER_TOKEN_EXPIRES_AT"] = expires_at.strftime(
                "%m/%d/%Y %H:%M:%S"
            )
        except Exception as e:
            print("Error, could not set os env expires at: ", e)
            raise Exception("Error, could not set os env expires at: " + str(e))

    @staticmethod
    def get_sp_token():
        """
        Gets Sharepoint Rest API bearer token.
        """
        if "SP_LOGIN_BASE_URL" not in os.environ:
            raise Exception("Error, could not find SP_LOGIN_BASE_URL in env")
        if "SP_TENANT_ID" not in os.environ:
            raise Exception("Error, could not find SP_TENANT_ID in env")
        if "SP_CLIENT_ID" not in os.environ:
            raise Exception("Error, could not find SP_CLIENT_ID in env")
        # if "SP_CLIENT_SECRET" not in os.environ:
        #     raise Exception("Error, could not find SP_CLIENT_SECRET in env")
        if "SP_CERTIFICATE_PATH" not in os.environ:
            raise Exception("Error, could not find SP_CERTIFICATE_PATH in env")
        if "SP_CERTIFICATE_PASSWORD" not in os.environ:
            raise Exception("Error, could not find SP_CERTIFICATE_PASSWORD in env")
        if "SP_GRANT_TYPE" not in os.environ:
            raise Exception("Error, could not find SP_GRANT_TYPE in env")
        if "SP_SITE" not in os.environ:
            raise Exception("Error, could not find SP_SITE in env")

        # Load the certificate
        with open(os.environ["SP_CERTIFICATE_PATH"], "rb") as cert_file:
            cert_data = cert_file.read()
        pfx = pkcs12.load_key_and_certificates(
            cert_data, str.encode(os.environ["SP_CERTIFICATE_PASSWORD"])
        )

        # Extract the private key and certificate
        private_key = pfx[0]
        certificate = pfx[1]

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Compute the SHA-1 thumbprint of the certificate
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        thumbprint = hashlib.sha1(cert_der).digest()
        thumbprint_b64 = (
            base64.urlsafe_b64encode(thumbprint).decode("utf-8").rstrip("=")
        )

        # JWT payload
        payload = {
            "aud": f"https://login.microsoftonline.com/{os.environ['GRAPH_TENANT_ID']}/oauth2/v2.0/token",
            "iss": os.environ["GRAPH_CLIENT_ID"],
            "sub": os.environ["GRAPH_CLIENT_ID"],
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 600,
        }

        # JWT header with x5t thumbprint
        headers = {"x5t": thumbprint_b64}

        # Generate the JWT assertion
        jwt_assertion = jwt.encode(
            payload, private_key_pem, algorithm="RS256", headers=headers
        )

        response = requests.post(
            os.environ["SP_LOGIN_BASE_URL"]
            + os.environ["SP_TENANT_ID"]
            + "/oauth2/v2.0/token",
            headers=headers,
            data={
                "client_id": os.environ["SP_CLIENT_ID"],
                "grant_type": os.environ["SP_GRANT_TYPE"],
                "scope": os.environ["SP_SCOPES"],
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": jwt_assertion,
            },
            timeout=30,
        )

        try:
            os.environ["SP_BEARER_TOKEN"] = response.json()["access_token"]
        except Exception as e:
            print("Error, could not set OS env bearer token: ", e)
            print(response.content)
            raise Exception("Error, could not set OS env bearer token: " + str(e))
        try:
            expires_at = datetime.now() + timedelta(
                seconds=float(response.json()["expires_in"])
            )
            os.environ["SP_BEARER_TOKEN_EXPIRES_AT"] = expires_at.strftime(
                "%m/%d/%Y %H:%M:%S"
            )
        except Exception as e:
            print("Error, could not set os env expires at: ", e)
            raise Exception("Error, could not set os env expires at: " + str(e))
