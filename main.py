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

def lookup_by_name(name: str) -> list[dict]:
    name_lower = name.strip().lower()
    return [h for h in HERBS if name_lower in h["name"].lower()]

def lookup_by_benefit(benefit: str) -> list[dict]:
    benefit_lower = benefit.strip().lower()
    return [h for h in HERBS if any(benefit_lower in b.lower() for b in h["benefits"])]

def lookup_by_category(cat: str) -> list[dict]:
    cat_lower = cat.strip().lower()
    return [h for h in HERBS if cat_lower in h["category"].lower()]

def list_all_herbs() -> list[dict]:
    return HERBS

def list_all_categories() -> list[dict]:
    return CATEGORIES

def suggest_for_symptom(symptom: str) -> list[dict]:
    symptom_lower = symptom.strip().lower()
    results = []
    for h in HERBS:
        for b in h["benefits"]:
            if symptom_lower in b or symptom_lower in h["name"].lower() or symptom_lower in h["category"].lower():
                results.append(h)
                break
    return results

def get_herb_hashes_for_ledger(herb_name: str, benefit: str, category: str) -> dict:
    return {
        "nameHash": utf8_keccak(herb_name),
        "benefitHash": utf8_keccak(benefit),
        "categoryHash": utf8_keccak(category),
    }

# Simple remedy ideas (title -> list of herb names). For display only.
REMEDY_IDEAS = [
    {"title": "Calming tea blend", "herbs": ["Chamomile", "Lavender", "Lemon balm"]},
    {"title": "Digestive aid", "herbs": ["Ginger", "Peppermint"]},
    {"title": "Golden milk", "herbs": ["Turmeric", "Ginger"]},
    {"title": "Immune support tea", "herbs": ["Echinacea", "Elderberry", "Ginger"]},
]

# -----------------------------------------------------------------------------
# CLI HANDLERS
# -----------------------------------------------------------------------------

def cmd_lookup(args: argparse.Namespace) -> int:
    if args.name:
        results = lookup_by_name(args.name)
    elif args.benefit:
        results = lookup_by_benefit(args.benefit)
    elif args.category:
        results = lookup_by_category(args.category)
    else:
        print("Specify --name, --benefit, or --category", file=sys.stderr)
        return 1
    if not results:
        print("No matches found.", file=sys.stderr)
        return 1
    for h in results:
        print(json.dumps(h, indent=2))
    return 0

def cmd_list_herbs(args: argparse.Namespace) -> int:
    for h in list_all_herbs():
        print(f"{h['name']}\t{h['category']}\t{h['tags']}")
    return 0

def cmd_list_categories(args: argparse.Namespace) -> int:
    for c in list_all_categories():
        print(f"{c['id']}\t{c['label']}\t{c['herbs']}")
    return 0

def cmd_hash(args: argparse.Namespace) -> int:
    text = args.text.strip()
    if not text:
        print("Provide --text", file=sys.stderr)
        return 1
    h = utf8_keccak(text)
    print(h)
