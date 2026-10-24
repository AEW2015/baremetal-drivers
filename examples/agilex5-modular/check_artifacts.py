#!/usr/bin/env python3
"""Read-only exact identity gate for an instructor-qualified SOF/handoff pair."""
import argparse,json,sys
from pathlib import Path
from bench import digest

def check(profile,sof,handoff):
    expected=json.loads(Path(profile).read_text())
    if not isinstance(expected,dict) or not all(k in expected for k in ('name','device','sof_sha256','handoff_sha256')):
        raise ValueError('Profile must define name, device and both artifact hashes.')
    actual={'sof_sha256':digest(sof),'handoff_sha256':digest(handoff)}
    matched=expected.get('qualification')=='recorded-bench-pass' and all(actual[k]==expected.get(k) for k in actual)
    return {'status':'match' if matched else 'unqualified','profile':expected['name'],'device':expected['device'],
            **actual,'scope':'Exact identity of a previously qualified pair; not an electrical or new-board compatibility test.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',default=str(Path(__file__).resolve().parent/'profiles/modular-es-ddr1600.json'))
    p.add_argument('--sof',required=True);p.add_argument('--handoff',required=True)
    a=p.parse_args()
    try:result=check(a.profile,a.sof,a.handoff)
    except (OSError,ValueError,KeyError) as exc:print(f'ERROR: cannot check artifact pair: {exc}',file=sys.stderr);return 1
    print(json.dumps(result,indent=2))
    if result['status']!='match':
        print('STOP: pair is not in the selected qualified profile. Preserve its build reports and obtain instructor qualification; changing expected hashes does not qualify it.',file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
