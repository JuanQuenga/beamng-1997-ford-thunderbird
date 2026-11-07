#!/usr/bin/env python3
"""Run RLS's own metadata and dealership filters against our generated files.

Only filter/shape code runs. This does not start a game or access any save.
RLS source is fetched into ignored references/ and is not shipped in the mod.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
ID='juan_tb97'
REF='v2.8.0'
PREFIX='lua/ge/extensions/'
paths=[
 'overhaul/career/market/vehicleShopping/catalog.lua',
 'overhaul/career/market/vehicleShopping/validation.lua',
 'overhaul/career/market/vehicleShopping/populationSelector.lua',
 'overhaul/lib/market/usedVehicleCondition.lua',
 'overhaul/lib/platform/jsonCatalog.lua',
 'levels/rls_west_coast/facilities/dealerships.facilities.json']
hashes={}
for path in paths:
    rel=path if path.startswith('levels/') else PREFIX+path
    dest=ROOT/'references'/'rls'/rel
    if not dest.exists():
        url=f'https://raw.githubusercontent.com/RLS-Modding/rls_career_overhaul/{REF}/{rel}'
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(urllib.request.urlopen(url,timeout=30).read())
    hashes[rel]=hashlib.sha256(dest.read_bytes()).hexdigest()


def lua(v):
    if v is None:return 'nil'
    if isinstance(v,bool):return 'true' if v else 'false'
    if isinstance(v,(int,float)):return repr(v)
    if isinstance(v,str):return json.dumps(v)
    if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
    return '{'+','.join('['+lua(k)+']='+lua(x) for k,x in v.items())+'}'


root_info=json.loads((ROOT/'build'/'vehicles'/ID/'info.json').read_text())
vehicles=[]
for key in ('v6','v8'):
    info={**root_info,**json.loads((ROOT/'build'/'vehicles'/ID/('info_lx_'+key+'.json')).read_text())}
    info.update(model_key=ID,key='lx_'+key,aggregates={})
    vehicles.append(info)
dealers=json.loads((ROOT/'references'/'rls'/'levels/rls_west_coast/facilities/dealerships.facilities.json').read_text())
code='''
package.path = ROOT .. '/references/rls/lua/ge/extensions/?.lua;' .. package.path
local used = require('overhaul/lib/market/usedVehicleCondition')
local validation = require('overhaul/career/market/vehicleShopping/validation').new({
  state={}, config={}, usedVehicleCondition=used
})
local catalog = require('overhaul/career/market/vehicleShopping/catalog').new({state={}})
catalog.bindServices({
  getOrgLevelData=function() return {} end,
  validation=setmetatable(validation,{__index=function() return function() end end})
})
local pop = require('overhaul/career/market/vehicleShopping/populationSelector')
for _, v in ipairs(VEHICLES) do
  local valid,reason=validation.isValidVehicleInfoShape(v)
  assert(valid,reason)
  assert(pop.populationWeight(v.Population)>0)
  local count=0
  for _,d in ipairs(DEALERS.dealerships) do
    if catalog.doesVehiclePassFilter(v,d.filter or {}) then
      local subs=d.subFilters or {{}}
      for _,f in ipairs(subs) do
        if catalog.doesVehiclePassFilter(v,f) then
          print(v.key..'|'..d.id..'|'..d.name)
          count=count+1
          break
        end
      end
    end
  end
  assert(count>0,'No eligible dealership for '..v.key)
end
'''
script=ROOT/'references'/'check_rls.lua'
script.write_text('local ROOT='+lua(str(ROOT))+'\nlocal VEHICLES='+lua(vehicles)+
                  '\nlocal DEALERS='+lua(dealers)+'\n'+code)
exe=shutil.which('luajit') or shutil.which('lua')
if not exe:raise SystemExit('Install LuaJIT or Lua to run the RLS source filter check.')
result=subprocess.run([exe,str(script)],capture_output=True,text=True,check=True)
matches={}
for line in result.stdout.splitlines():
    key,dealer_id,name=line.split('|')
    matches.setdefault(key,[]).append({'id':dealer_id,'name':name})
report={'rls_release':REF,'status':'Published RLS metadata/filter functions passed outside BeamNG',
        'limitations':'No VFS registration, stock generation, purchasing, repair, save/reload, or runtime test.',
        'eligible_dealer_filters':matches,'source_sha256':hashes,
        'metadata_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (ROOT/'build'/'vehicles'/ID).glob('info*.json')}}
(ROOT/'rls-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
