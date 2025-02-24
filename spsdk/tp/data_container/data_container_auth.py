#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2021-2022 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Module for all Authenticators used in DataContainer."""

from abc import abstractmethod
from typing import Mapping, Optional

from crcmod.predefined import mkPredefinedCrcFun
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import cmac, hashes, hmac
from cryptography.hazmat.primitives.ciphers import algorithms

from spsdk.utils.crypto.backend_openssl import openssl_backend
from spsdk.utils.easy_enum import Enum

from ..exceptions import SPSDKTpError


class AuthenticationType(Enum):
    """Available Authentication types."""

    NONE = (0, "none", "None")
    AES_CMAC = (0x10, "aes-cmac", "AES-CMAC")
    HMAC_256 = (0x11, "hmac-256", "HMAC / SHA-256")
    ECDSA_256 = (0x20, "ecdsa-256", "ECDSA / P-256 / SHA-256")
    CRC32 = (0xFE, "crc32", "CRC32")


class AuthenticationProvider:
    """Base abstract class for Authenticators."""

    #: Type of Authenticator, see: `AuthenticationType`
    TYPE = AuthenticationType.NONE
    #: Expected length of Authentication code/signature
    DATA_LEN = 0

    @classmethod
    @abstractmethod
    def sign(cls, data: bytes, key: bytes) -> bytes:
        """Generate signature/authentication code."""

    @classmethod
    @abstractmethod
    def validate(cls, data: bytes, signature: bytes, key: bytes) -> bool:
        """Validate signature/authentication code."""


# pylint: disable=invalid-name
class AES_CMAC(AuthenticationProvider):
    """AES-CMAC Authenticator."""

    TYPE = AuthenticationType.AES_CMAC
    DATA_LEN = 16

    @classmethod
    def sign(cls, data: bytes, key: bytes) -> bytes:
        """Generate CMAC authentication code."""
        cipher = cmac.CMAC(algorithm=algorithms.AES(key))
        cipher.update(data=data)
        return cipher.finalize()

    @classmethod
    def validate(cls, data: bytes, signature: bytes, key: bytes) -> bool:
        """Validate CMAC authentication code."""
        cipher = cmac.CMAC(algorithm=algorithms.AES(key))
        cipher.update(data=data)
        try:
            cipher.verify(signature=signature)
            return True
        except InvalidSignature:
            return False


# pylint: disable=invalid-name
class _HMAC(AuthenticationProvider):
    """Base for HMAC Authenticators."""

    HASHER: Optional[hashes.HashAlgorithm] = None

    @classmethod
    def sign(cls, data: bytes, key: bytes) -> bytes:
        """Generate hash authentication code."""
        assert cls.HASHER
        hasher = hmac.HMAC(key=key, algorithm=cls.HASHER)
        hasher.update(data)
        return hasher.finalize()

    @classmethod
    def validate(cls, data: bytes, signature: bytes, key: bytes) -> bool:
        """Validate hash authentication code."""
        assert cls.HASHER
        hasher = hmac.HMAC(key=key, algorithm=cls.HASHER)
        hasher.update(data)
        try:
            hasher.verify(signature=signature)
            return True
        except InvalidSignature:
            return False


# pylint: disable=invalid-name
class HMAC_256(_HMAC):
    """HMAC-256 Authenticator."""

    TYPE = AuthenticationType.HMAC_256
    DATA_LEN = 32
    HASHER = hashes.SHA256()


# pylint: disable=invalid-name
class _CRC(AuthenticationProvider):
    """Base for CRC Authenticators."""

    CRC_NAME = "invalid-crc-name"

    @classmethod
    def sign(cls, data: bytes, key: Optional[bytes] = None) -> bytes:
        """Generate CRC code."""
        crc_func = mkPredefinedCrcFun(cls.CRC_NAME)
        crc = crc_func(data)
        crc_bytes = int.to_bytes(crc, length=cls.DATA_LEN, byteorder="little")
        return crc_bytes

    @classmethod
    def validate(cls, data: bytes, signature: bytes, key: Optional[bytes] = None) -> bool:
        """Validate CRC code."""
        crc_func = mkPredefinedCrcFun(cls.CRC_NAME)
        crc = crc_func(data)
        crc_bytes = int.to_bytes(crc, length=cls.DATA_LEN, byteorder="little")
        return crc_bytes == signature


# pylint: disable=invalid-name
class CRC32(_CRC):
    """CRC Authenticator using CRC32 settings."""

    TYPE = AuthenticationType.CRC32
    DATA_LEN = 4
    CRC_NAME = "crc32"


# pylint: disable=invalid-name
class ECDSA_256(AuthenticationProvider):
    """ECDSA Authenticator using ECC P-256."""

    TYPE = AuthenticationType.ECDSA_256
    DATA_LEN = 64

    @classmethod
    def sign(cls, data: bytes, key: bytes) -> bytes:
        """Generate ECDSA signature."""
        return openssl_backend.ecc_sign(key, data)

    @classmethod
    def validate(cls, data: bytes, signature: bytes, key: bytes) -> bool:
        """Validate ECDSA signature."""
        return openssl_backend.ecc_verify(key, signature, data)


_AUTHENTICATORS: Mapping[int, AuthenticationProvider] = {
    AuthenticationType.AES_CMAC: AES_CMAC,  # type: ignore
    AuthenticationType.HMAC_256: HMAC_256,  # type: ignore
    AuthenticationType.ECDSA_256: ECDSA_256,  # type: ignore
    AuthenticationType.CRC32: CRC32,  # type: ignore
}


def _get_auth_provider(auth_type: AuthenticationType) -> AuthenticationProvider:
    try:
        provider = _AUTHENTICATORS[auth_type]
        return provider
    except KeyError as exc:
        if auth_type in AuthenticationType.tags():
            raise SPSDKTpError(
                f"Authenticator '{AuthenticationType.desc(auth_type)}' ({auth_type}) is not supported yet"
            ) from exc
        raise SPSDKTpError(f"Unknown AUTH TYPE: {auth_type}") from exc


def get_auth_data_len(auth_type: AuthenticationType) -> int:
    """Get expected length of signature/authentication code.

    :param auth_type: Type of authenticator
    :raises SPSDKTpError: Unknown type of Authenticator
    :return: Length of signature/authentication code
    """
    auth_provider = _get_auth_provider(auth_type=auth_type)
    return auth_provider.DATA_LEN


def sign(data: bytes, auth_type: AuthenticationType, key: bytes) -> bytes:
    """Generate signature/authentication code.

    :param data: Data to create signature/authentication code from
    :param auth_type: Type of Authenticator
    :param key: Key used for Authenticator
    :raises SPSDKTpError: [description]
    :return: Signature/authentication code
    """
    auth_provider = _get_auth_provider(auth_type=auth_type)
    return auth_provider.sign(data=data, key=key)


def validate(data: bytes, signature: bytes, auth_type: AuthenticationType, key: bytes) -> bool:
    """Validate signature/authentication code.

    :param data: Data to validate
    :param signature: Signature/authentication code to validate
    :param auth_type: Authenticator to use
    :param key: Key for Authenticator
    :raises SPSDKTpError: Unknown Authenticator type
    :return: True if signature/authentication code is valid
    """
    auth_provider = _get_auth_provider(auth_type=auth_type)
    return auth_provider.validate(data=data, signature=signature, key=key)
