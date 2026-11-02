#!/usr/bin/env python3
"""Read the checked-in release manifest without depending on the caller cwd."""
import json,sys
from pathlib import Path
PINS=json.loads(Path(__file__).with_name('stack-versions.json').read_text())
if __name__=='__main__':
 value=PINS
 for key in sys.argv[1].split('.'):value=value[key]
 print(value)
