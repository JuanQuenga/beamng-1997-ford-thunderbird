#!/usr/bin/env python3
"""Package only authored assets, with fresh validation reports, into two ZIPs."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ID='juan_tb97'
DIST=ROOT/'dist'
DIST.mkdir(exist_ok=True)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def report(name):return json.loads((ROOT/name).read_text())


static=report('validation.json')
model=report('model-validation.json')
rls=report('rls-validation.json')
OUT=ROOT/'build'/'vehicles'/ID
assert static['files']=={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},'Rerun validate_package.py'
assert model['dae_sha256']==sha(OUT/(ID+'.dae')),'Rerun validate_model.py'
assert rls['metadata_sha256']=={p.name:sha(p) for p in OUT.glob('info*.json')},'Rerun check_rls.py'

docs=['README.md','TESTING.md','SOURCES.md','BUILD.md','CONTRIBUTING.md','LICENSE.txt']
mod=DIST/'thunderbird_1997_prototype.zip'
with zipfile.ZipFile(mod,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(ROOT/'build'))
    for doc in docs:z.write(ROOT/doc,'documentation/'+doc)
    z.writestr('READ_ME_FIRST.txt',
        '1997 Ford Thunderbird LX experimental prototype\n'
        'V6 and V8 configurations. Target BeamNG 0.40.x.\n'
        'No in-game test has been performed. RLS runtime compatibility is unverified.\n'
        'Leave this ZIP compressed and put it in the active BeamNG user folder/mods.\n'
        'Test in Freeroam, then a disposable RLS career before using an existing save.\n'
        'See documentation/README.md and documentation/TESTING.md.\n')
    for name in ['validation.json','model-validation.json','rls-validation.json']:
        z.write(ROOT/name,'documentation/'+name)

source=DIST/'thunderbird_1997_source.zip'
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    files=[ROOT/p for p in docs+['validation.json','model-validation.json','rls-validation.json']]
    files+=list((ROOT/'tools').glob('*.py'))
    files+=list((ROOT/'source').glob('*.json'))
    files+=[ROOT/'source/thunderbird_1997.blend']
    files+=list((ROOT/'renders').glob('*.png'))
    for p in sorted(files):z.write(p,p.relative_to(ROOT))

for p in [mod,source]:
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
with zipfile.ZipFile(mod) as z:
    prefix='vehicles/'+ID+'/'
    for filename,digest in static['files'].items():
        assert hashlib.sha256(z.read(prefix+filename)).hexdigest()==digest
    assert all(n.startswith(('vehicles/','documentation/','READ_ME_FIRST.txt')) for n in z.namelist())

(DIST/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in [mod,source]))
for p in [mod,source]:print(f'{p.name}: {p.stat().st_size:,} bytes; archive integrity checked')
