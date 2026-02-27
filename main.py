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
    return 0

def cmd_hash_batch(args: argparse.Namespace) -> int:
    names = [s.strip() for s in (args.names or "").split(",") if s.strip()]
    benefits = [s.strip() for s in (args.benefits or "").split(",") if s.strip()]
    categories = [s.strip() for s in (args.categories or "").split(",") if s.strip()]
    out = {}
    if names:
        out["nameHashes"] = [utf8_keccak(n) for n in names]
    if benefits:
        out["benefitHashes"] = [utf8_keccak(b) for b in benefits]
    if categories:
        out["categoryHashes"] = [utf8_keccak(c) for c in categories]
    print(json.dumps(out, indent=2))
    return 0

def cmd_config(args: argparse.Namespace) -> int:
    cfg = {
        "app": "HerbIT",
        "herb_count": len(HERBS),
        "category_count": len(CATEGORIES),
        "hash_algorithm": "keccak256 (SHA3-256 fallback)",
        "contract_note": "Herbo contract uses bytes32; compute hashes off-chain and pass to logHerbFree.",
    }
    print(json.dumps(cfg, indent=2))
    return 0

def cmd_constants(args: argparse.Namespace) -> int:
    # Mirrors Herbo.sol constants for reference (do not deploy with these; contract has its own)
    c = {
        "HRB_BPS_BASE": 10000,
        "HRB_MAX_FEE_BPS": 500,
        "HRB_MAX_ENTRIES": 2500,
        "HRB_MAX_CATEGORIES": 180,
        "HRB_MAX_BATCH_LOG": 35,
        "HRB_MAX_BATCH_CREDIT": 45,
        "HRB_MAX_REMEDIES": 1200,
        "HRB_MAX_REMEDY_BATCH": 28,
        "HRB_MAX_CAMPAIGNS": 95,
    }
    print(json.dumps(c, indent=2))
    return 0

def cmd_stats(args: argparse.Namespace) -> int:
    by_cat = {}
    for h in HERBS:
        by_cat[h["category"]] = by_cat.get(h["category"], 0) + 1
    print("Herbs:", len(HERBS))
    print("Categories:", len(CATEGORIES))
    print("By category:", json.dumps(by_cat, indent=2))
    return 0

def cmd_demo(args: argparse.Namespace) -> int:
    print("HerbIT demo — herb guide for natural and healthy living")
    print("Lookup 'Ginger':", lookup_by_name("Ginger"))
    print("Lookup benefit 'digestive':", [h["name"] for h in lookup_by_benefit("digestive")])
    print("Hash of 'Basil':", utf8_keccak("Basil"))
    print("Hash of 'Digestive support':", utf8_keccak("Digestive support"))
    return 0

def cmd_remedies(args: argparse.Namespace) -> int:
    for r in REMEDY_IDEAS:
        print(f"{r['title']}: {', '.join(r['herbs'])}")
    return 0

def cmd_suggest(args: argparse.Namespace) -> int:
    symptom = (args.symptom_opt or getattr(args, "symptom", None) or "").strip()
    if not symptom:
        print("Provide symptom or keyword (e.g. suggest digestive)", file=sys.stderr)
        return 1
    results = suggest_for_symptom(symptom)
    if not results:
        print("No herbs found for that keyword.", file=sys.stderr)
        return 1
    for h in results:
        print(f"{h['name']}\t{h['category']}\t{h['tags']}")
    return 0

def cmd_export_hashes(args: argparse.Namespace) -> int:
    data = get_herb_hashes_for_ledger(args.name.strip(), args.benefit.strip(), args.category.strip())
    j = json.dumps(data, indent=2)
    if args.file:
        Path(args.file).write_text(j, encoding="utf-8")
        print("Written to", args.file)
    else:
        print(j)
    return 0

def cmd_interactive(args: argparse.Namespace) -> int:
    print("HerbIT interactive. Commands: lookup <name|benefit|category> <value>, list-herbs, list-categories, hash <text>, suggest <keyword>, quit")
    while True:
        try:
            line = input("herbit> ").strip()
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                break
            parts = line.split(maxsplit=2)
            cmd = parts[0].lower() if parts else ""
            if cmd == "lookup" and len(parts) >= 3:
                kind, value = parts[1].lower(), parts[2]
                if kind == "name":
                    for h in lookup_by_name(value):
                        print(h)
                elif kind == "benefit":
                    for h in lookup_by_benefit(value):
                        print(h)
                elif kind == "category":
                    for h in lookup_by_category(value):
                        print(h)
                else:
                    print("Use name, benefit, or category")
            elif cmd == "list-herbs":
                cmd_list_herbs(args)
            elif cmd == "list-categories":
                cmd_list_categories(args)
            elif cmd == "hash" and len(parts) >= 2:
                print(utf8_keccak(parts[1]))
            elif cmd == "suggest" and len(parts) >= 2:
                for h in suggest_for_symptom(parts[1]):
                    print(h["name"], h["category"], h["tags"])
            else:
                print("Unknown or incomplete command. Try: lookup name Basil | list-herbs | hash Basil | suggest digestive")
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            break
    return 0

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="HerbIT — herb guide and Herbo ledger helpers")
    sub = p.add_subparsers(dest="command", help="Commands")

    lookup_p = sub.add_parser("lookup", help="Lookup herbs by name, benefit or category")
    lookup_p.add_argument("--name", type=str, help="Herb name (partial match)")
    lookup_p.add_argument("--benefit", type=str, help="Benefit keyword")
    lookup_p.add_argument("--category", type=str, help="Category id/label")
    lookup_p.set_defaults(func=cmd_lookup)

    sub.add_parser("list-herbs", help="List all herbs").set_defaults(func=cmd_list_herbs)
    sub.add_parser("list-categories", help="List all categories").set_defaults(func=cmd_list_categories)

    hash_p = sub.add_parser("hash", help="Keccak256 hash of text (for ledger)")
    hash_p.add_argument("--text", type=str, required=True, help="Text to hash")
    hash_p.set_defaults(func=cmd_hash)

    hb_p = sub.add_parser("hash-batch", help="Hash multiple names/benefits/categories")
    hb_p.add_argument("--names", type=str, help="Comma-separated names")
    hb_p.add_argument("--benefits", type=str, help="Comma-separated benefits")
    hb_p.add_argument("--categories", type=str, help="Comma-separated categories")
    hb_p.set_defaults(func=cmd_hash_batch)

    sub.add_parser("config", help="Show app config").set_defaults(func=cmd_config)
    sub.add_parser("constants", help="Show Herbo constant reference").set_defaults(func=cmd_constants)
    sub.add_parser("stats", help="Herb and category stats").set_defaults(func=cmd_stats)
    sub.add_parser("demo", help="Run a short demo").set_defaults(func=cmd_demo)
    sub.add_parser("remedies", help="List remedy ideas (title and herbs)").set_defaults(func=cmd_remedies)
    sub.add_parser("interactive", help="Interactive REPL").set_defaults(func=cmd_interactive)

    suggest_p = sub.add_parser("suggest", help="Suggest herbs for a symptom or keyword")
    suggest_p.add_argument("symptom", type=str, nargs="?", default="", help="Symptom or keyword")
    suggest_p.add_argument("--symptom", type=str, dest="symptom_opt", help="Alternative: --symptom value")
    suggest_p.set_defaults(func=cmd_suggest)

    export_p = sub.add_parser("export-hashes", help="Export name/benefit/category hashes for a herb")
    export_p.add_argument("--name", type=str, required=True, help="Herb name")
    export_p.add_argument("--benefit", type=str, required=True, help="Benefit description")
    export_p.add_argument("--category", type=str, required=True, help="Category (e.g. Digestive)")
    export_p.add_argument("--file", type=str, help="Write JSON to file")
    export_p.set_defaults(func=cmd_export_hashes)

    args = p.parse_args()
    if not args.command:
        p.print_help()
        return 0
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())

