#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2020-2021 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Example provides the usage of certificates validation. It validates previously created chains."""

#          Certificates' structure
#              CA Certificate
#              /      \
#             /        \
#           crt       chain_crt
#                        \
#                         \
#                      chain_crt2
import os
from os import path

from spsdk import SPSDKError
from spsdk.crypto import (
    RSAPublicKey,
    get_public_key_from_certificate,
    is_ca_flag_set,
    load_certificate,
    load_public_key,
    validate_certificate,
    validate_certificate_chain,
)


def main() -> None:
    """Main function."""
    # Set the folder for data (certificates, keys)
    data_dir = path.join(path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    # Load public key of CA certificate
    ca0_pubkey_rsa2048 = load_public_key(path.join(data_dir, "ca_publickey_rsa2048.pem"))
    # Load CA certificate
    ca0_cert = load_certificate(path.join(data_dir, "ca_cert_pem.crt"))
    # Obtain public key from CA certificate
    pubkey_from_ca0_cert = get_public_key_from_certificate(ca0_cert)
    # Check if public key of certificate has proper format
    assert isinstance(pubkey_from_ca0_cert, RSAPublicKey)
    # Compare CA's public key from file and the one from certificate
    if ca0_pubkey_rsa2048.public_numbers() != pubkey_from_ca0_cert.public_numbers():
        raise SPSDKError("Keys are not the same (the one from disc and the one from cert)")
    # Load certificate, which is singed by CA
    crt = load_certificate(path.join(data_dir, "crt_pem.crt"))
    if not validate_certificate(crt, ca0_cert):
        raise SPSDKError("The certificate is not valid")
    print("The certificate was signed by the CA.")
    # Load chain of certificate
    chain = ["chain_crt2_pem.crt", "chain_crt_pem.crt", "ca_cert_pem.crt"]
    chain_cert = [load_certificate(path.join(data_dir, cert_name)) for cert_name in chain]
    ch3_crt2 = load_certificate(path.join(data_dir, "chain_crt2_pem.crt"))
    ch3_crt = load_certificate(path.join(data_dir, "chain_crt_pem.crt"))
    ch3_ca = load_certificate(path.join(data_dir, "ca_cert_pem.crt"))
    # Validate the chain (if corresponding items in chain are singed by one another)
    if not validate_certificate_chain(chain_cert):
        raise SPSDKError("The certificate chain is not valid")
    print("The chain of certificates is valid.")
    # Checks if CA flag is set correctly
    if is_ca_flag_set(ch3_crt2):
        raise SPSDKError("CA flag is set")
    if not is_ca_flag_set(ch3_crt):
        raise SPSDKError("CA flag is not set")
    if not is_ca_flag_set(ch3_ca):
        raise SPSDKError("CA flag is not set")


if __name__ == "__main__":
    main()
