#!/usr/bin/env python3
"""
HerbIT — CLI for herb guide and Herbo ledger helpers.
Natural and healthy living: lookup herbs, benefits, categories; compute hashes for the ledger.
Usage:
  python herbit_app.py lookup --name "Basil"
  python herbit_app.py lookup --benefit "digestive"
  python herbit_app.py list-herbs
  python herbit_app.py list-categories
  python herbit_app.py hash --text "Basil"
  python herbit_app.py hash-batch --names "Basil,Ginger" --benefits "Digestive,Anti-inflammatory"
  python herbit_app.py suggest digestive
  python herbit_app.py export-hashes --name "Basil" --benefit "Digestive support" --category "Digestive" [--file out.json]
  python herbit_app.py config | constants | stats | demo | remedies | interactive
"""

from __future__ import annotations

# HerbIT is the CLI companion for EatToLive.health and the Herbo contract.
# All hashes are computed locally; no private keys or RPC required for lookup/hash commands.

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
