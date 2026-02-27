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

# -----------------------------------------------------------------------------
# HERB DATA (local guide — not medical advice)
# -----------------------------------------------------------------------------

HERBS = [
    {"name": "Basil", "benefits": ["antioxidant", "anti-inflammatory", "digestive", "stress"], "category": "culinary", "tags": "culinary · digestive"},
    {"name": "Chamomile", "benefits": ["calming", "sleep", "digestive"], "category": "calm", "tags": "calm · sleep"},
    {"name": "Echinacea", "benefits": ["immune"], "category": "immune", "tags": "immune"},
    {"name": "Ginger", "benefits": ["nausea", "anti-inflammatory", "digestive", "circulation"], "category": "digestive", "tags": "digestive · warming"},
    {"name": "Lavender", "benefits": ["relaxation", "sleep", "mood"], "category": "calm", "tags": "calm · aroma"},
    {"name": "Peppermint", "benefits": ["digestive", "clarity"], "category": "digestive", "tags": "digestive · cooling"},
    {"name": "Turmeric", "benefits": ["anti-inflammatory", "antioxidant"], "category": "inflammatory", "tags": "inflammatory · spice"},
    {"name": "Thyme", "benefits": ["antimicrobial", "respiratory"], "category": "respiratory", "tags": "respiratory · culinary"},
    {"name": "Rosemary", "benefits": ["memory", "circulation", "antioxidant"], "category": "cognitive", "tags": "cognitive · culinary"},
    {"name": "Sage", "benefits": ["throat", "antioxidant"], "category": "throat", "tags": "throat · antioxidant"},
    {"name": "Fennel", "benefits": ["digestive", "bloating"], "category": "digestive", "tags": "digestive"},
    {"name": "Elderberry", "benefits": ["immune"], "category": "immune", "tags": "immune"},
    {"name": "Lemon balm", "benefits": ["calming", "mood", "digestive"], "category": "calm", "tags": "calm · digestive"},
    {"name": "Valerian", "benefits": ["sleep", "calming"], "category": "calm", "tags": "sleep"},
    {"name": "Passionflower", "benefits": ["calming", "sleep", "anxiety"], "category": "calm", "tags": "calm · sleep"},
    {"name": "Oregano", "benefits": ["antimicrobial", "antioxidant"], "category": "culinary", "tags": "culinary"},
    {"name": "Dandelion", "benefits": ["digestive", "detox", "liver"], "category": "digestive", "tags": "digestive"},
]

CATEGORIES = [
    {"id": "digestive", "label": "Digestive", "herbs": "ginger, peppermint, fennel, chamomile"},
    {"id": "calm", "label": "Calm & sleep", "herbs": "lavender, chamomile, lemon balm"},
    {"id": "immune", "label": "Immune", "herbs": "echinacea, elderberry"},
    {"id": "respiratory", "label": "Respiratory", "herbs": "thyme, eucalyptus"},
    {"id": "inflammatory", "label": "Anti-inflammatory", "herbs": "turmeric, ginger"},
    {"id": "culinary", "label": "Culinary & wellness", "herbs": "basil, rosemary, sage"},
]

# Keccak256-style hash for bytes (EVM-compatible: use py-evm or eth_abi in production)
def keccak256_hex(data: bytes) -> str:
    try:
        from Crypto.Hash import keccak
        h = keccak.new(digest_bits=256)
        h.update(data)
        return "0x" + h.hexdigest()
    except Exception:
        pass
    # Fallback: SHA3-256 (same as Keccak-256 for many implementations)
    h = hashlib.sha3_256(data)
    return "0x" + h.hexdigest()

def utf8_keccak(text: str) -> str:
    return keccak256_hex(text.encode("utf-8"))

# -----------------------------------------------------------------------------
# LOOKUP
# -----------------------------------------------------------------------------

