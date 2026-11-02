#!/usr/bin/env python3
"""Inventory catalog source coverage and readability signals, not correctness grades."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'examples/agilex5-modular/catalog.json'
OUTPUT = ROOT / 'tools/education/example-audit.json'
REPORT = ROOT / 'docs/education-audit.md'
START = '<!-- source-inventory:start -->'
END = '<!-- source-inventory:end -->'
SOURCE_SUFFIXES = {'.c', '.h', '.S', '.s', '.py', '.sh', '.sv', '.v', '.cpp', '.ld', '.tcl'}


def inventory():
    catalog = json.loads(CATALOG.read_text())
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    records = []
    for example in catalog['examples']:
        source = ROOT / example['source']
        if not source.exists():
            raise ValueError('Missing catalog source: ' + example['source'])
        candidates = [source] if source.is_file() else [ROOT / name for name in tracked
            if name.startswith(example['source'].rstrip('/') + '/')]
        files = []
        for path in sorted(candidates):
            if path.suffix not in SOURCE_SUFFIXES:
                continue
            relative = path.relative_to(ROOT)
            if any(part in {'build', 'runs', 'validation', '.deps', '__pycache__'} for part in relative.parts):
                continue
            data = path.read_bytes()
            lines = data.decode(errors='replace').splitlines()
            files.append({'path': relative.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(),
                          'lines': len(lines), 'lines_over_100_columns': sum(len(line) > 100 for line in lines)})
        records.append({'id': example['id'], 'family': example['family'], 'source': example['source'],
                        'files': files})
    return {'scope': 'All catalog entry paths inventoried. Long lines are review signals, not defects or compliance grades. Directory entries include tracked authored sources, excluding build/run/evidence trees. A loader path does not mean fetched vendor sources were inspected.',
            'examples': records}


def section(data):
    lines = [START, '## Source inventory', '',
             'All **' + str(len(data['examples'])) + '** registered entry paths exist. This census lists source coverage,',
             'rather than certifying every implementation. Directory entries can overlap;',
             'legacy loader entries do not include their fetched vendor dependency.', '',
             '| Example | Source entry | Source files inventoried | Lines over 100 columns |',
             '|---|---|---:|---:|']
    base = 'https://github.com/AEW2015/baremetal-drivers/tree/main/'
    for row in data['examples']:
        count = sum(file['lines_over_100_columns'] for file in row['files'])
        lines.append(f"| `{row['id']}` | [{row['source']}]({base}{row['source']}) | {len(row['files'])} | {count} |")
    lines.extend(['', 'Regenerate with `python3 tools/education/audit_examples.py`.',
                  'The JSON record includes per-file source hashes and metrics.', END])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = inventory()
    serialized = json.dumps(data, indent=2) + '\n'
    before = REPORT.read_text()
    prefix, rest = before.split(START, 1)
    _, suffix = rest.split(END, 1)
    rendered = prefix + section(data) + suffix
    if args.check:
        if OUTPUT.read_text() != serialized or before != rendered:
            raise SystemExit('Stale education inventory; run python3 tools/education/audit_examples.py')
    else:
        OUTPUT.write_text(serialized)
        REPORT.write_text(rendered)
    print(f"Verified {len(data['examples'])} catalog source entries; signals are not compliance grades")


if __name__ == '__main__':
    main()
