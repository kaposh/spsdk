#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2020-2022 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Testing the SDPHost application."""


from unittest.mock import patch

from click.testing import CliRunner

import spsdk
from spsdk.apps import sdphost
from spsdk.utils.serial_proxy import SerialProxy

data_responses = {
    b"\x05\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00": b"\x56\x78\x78\x56\xf0\xf0\xf0\xf0"
}


def test_version():
    runner = CliRunner()
    result = runner.invoke(sdphost.main, ["--version"])
    assert result.exit_code == 0
    assert spsdk.__version__ in result.output


def test_get_property(caplog):
    # There's a problem with logging under CliRunner
    # https://github.com/pytest-dev/pytest/issues/3344
    # caplog is set to disable all logging output
    # Comment the following line to see logging info, however there will be an failure
    caplog.set_level(100_000)
    runner = CliRunner()
    cmd = "-p com12 error-status"
    with patch("spsdk.sdp.interfaces.uart.Serial", SerialProxy.init_proxy(data_responses)):
        result = runner.invoke(sdphost.main, cmd.split())
        assert result.exit_code == 0
        assert "Response status = 4042322160 (0xf0f0f0f0) HAB Success." in result.output
