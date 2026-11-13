#!/usr/bin/env python3
"""Flrig EMCOMM - double-click this file (or run: python3 run.py) to start.

A station list that tunes your radio through flrig.
Copyright (C) 2026 KW3KW. GNU GPL v3 or later - see LICENSE.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flrig_emcomm.__main__ import main  # noqa: E402

main()
