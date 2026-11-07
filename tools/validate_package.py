#!/usr/bin/env python3
"""Static validation of the actual files shipped to BeamNG. No game required."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'source/spec.json').read_text())
ID=SPEC['id']
OUT=ROOT/'build'/'vehicles'/ID
checks=[]


def check(condition,message):
    if not condition:raise AssertionError(message)
    checks.append(message)


def rows(part,section):
    return [x for x in part.get(section,[])[1:] if isinstance(x,list)]


parts={}
for path in sorted(OUT.iterdir()):
    if path.suffix in ('.json','.jbeam','.pc'):
        data=json.loads(path.read_text())
        check(True,f'Valid JSON: {path.name}')
        if path.suffix=='.jbeam':
            for name,part in data.items():
                check(name not in parts,f'Unique part: {name}')
                check(name.startswith(ID),'Namespaced part: '+name)
                check(part['information']['value']>0,'Priced career part: '+name)
                parts[name]=part

dae=ET.parse(OUT/(ID+'.dae'))
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
check(dae.find('.//c:up_axis',ns).text=='Z_UP','DAE uses Z up')
check(float(dae.find('.//c:unit',ns).get('meter'))==1,'DAE uses meters')
meshes={x.get('name') for x in dae.findall('.//c:library_visual_scenes/c:visual_scene/c:node',ns)}
geometry_names={x.get('name') for x in dae.findall('.//c:library_geometries/c:geometry',ns)}
material_defs=json.loads((OUT/'main.materials.json').read_text())
exported_materials={x.get('name') for x in dae.findall('.//c:library_materials/c:material',ns)}
check(exported_materials<=set(material_defs),'All exported materials have BeamNG definitions')
for mat in material_defs.values():
    for stage in mat['Stages']:
        for key,value in stage.items():
            if key.endswith('Map') and isinstance(value,str) and value.startswith('/vehicles/'+ID+'/'):
                check((OUT/value.rsplit('/',1)[-1]).is_file(),'Packaged texture: '+value)

reports={}
for variant,eng in SPEC['engines'].items():
    config=json.loads((OUT/('lx_'+variant+'.pc')).read_text())
    check(config['parts']['main']==ID,'Main part configured: '+variant)
    selected=[]
    def visit(name):
        if name in selected:return
        check(name in parts,'Part resolves: '+name)
        selected.append(name)
        part=parts[name]
        for slot,default,*_ in rows(part,'slots'):
            chosen=config['parts'].get(slot,default)
            if chosen:
                check(chosen in parts and parts[chosen]['slotType']==slot,'Slot matches: '+slot)
                visit(chosen)
    visit(ID)
    selected_parts=[parts[n] for n in selected]
    all_nodes={}
    all_groups=set()
    for p in selected_parts:
        for n,x,y,z,opts in rows(p,'nodes'):
            check(n not in all_nodes,'Unique node: '+variant+'/'+n)
            check(all(math.isfinite(v) for v in (x,y,z,opts['nodeWeight'])) and opts['nodeWeight']>0,
                  'Finite position and positive mass: '+variant+'/'+n)
            all_nodes[n]=(x,y,z,opts)
            group=opts['group']
            all_groups.update([group] if isinstance(group,str) else group)
    wheel_data={}
    wheel_mass=0
    for p in selected_parts:
        defaults={}
        for row in p.get('pressureWheels',[])[1:]:
            if isinstance(row,dict):defaults.update(row);continue
            w,hub,group,n1,n2,stabilizer,arm,direction,opts=row
            settings={**defaults,**opts}
            check(w not in wheel_data,'Unique wheel: '+variant+'/'+w)
            check(all(n in all_nodes for n in (n1,n2,arm)),'Wheel axle nodes resolve: '+w)
            center=tuple((all_nodes[n1][k]+all_nodes[n2][k])/2 for k in range(3))
            check(direction==(-1 if center[0]>0 else 1),'Forward wheel direction: '+w)
            wheel_data[w]=(center,settings)
            all_groups.update([hub,group])
            wheel_mass+=2*settings['numRays']*(settings['hubNodeWeight']+settings['nodeWeight'])
    check(set(wheel_data)=={'FL','FR','RL','RR'},'Four pressure wheels: '+variant)
    check(abs(wheel_data['RL'][0][1]-wheel_data['FL'][0][1]-SPEC['wheelbase_m'])<1e-6,
          'Correct wheelbase: '+variant)
    check(abs(wheel_data['FL'][0][0]-wheel_data['FR'][0][0]-SPEC['track_m'])<1e-6,
          'Correct track: '+variant)
    devices={}
    for p in selected_parts:
        for section,cols in [('beams',2),('hydros',2),('triangles',3),('torsionbars',4),('refNodes',4)]:
            for row in rows(p,section):
                check(all(n in all_nodes for n in row[:cols]),'Node references resolve: '+section)
                check(len(set(row[:cols]))==cols,'Distinct nodes: '+section)
                if section in ('beams','hydros'):
                    check(math.dist(all_nodes[row[0]][:3],all_nodes[row[1]][:3])>.005,
                          'Nonzero structural element: '+section)
                if section=='triangles':
                    a,b,c=[all_nodes[n][:3] for n in row[:3]]
                    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
                    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                    check(sum(x*x for x in cross)>1e-10,'Nonzero collision triangle')
        for row in rows(p,'powertrain'):
            check(row[1] not in devices,'Unique powertrain device: '+row[1])
            devices[row[1]]=row
        for mesh,groups,*_ in rows(p,'flexbodies'):
            check(mesh in meshes and mesh in geometry_names,'Exported mesh resolves: '+mesh)
            check(set(groups)<=all_groups,'Flexbody groups resolve: '+mesh)
        for key,g in p.get('glowMap',{}).items():
            check(key in material_defs and all(g[k] in material_defs for k in ('off','on')),
                  'Glow materials resolve: '+key)
        engine=p.get('mainEngine')
        if engine:
            check(all(n in all_nodes for n in engine['torqueReactionNodes:']),'Engine reaction nodes resolve')
    check('mainEngine' in devices,'Engine device is installed: '+variant)
    for name,row in devices.items():
        check(row[2]=='dummy' or row[2] in devices,'Powertrain input resolves: '+name)
        # Following every parent must terminate at the engine, never a cycle.
        path=set();cursor=name
        while cursor!='dummy':
            check(cursor not in path,'Acyclic powertrain: '+name)
            path.add(cursor);cursor=devices[cursor][2]
    for w in ('RL','RR'):
        shaft=devices['wheelaxle'+w]
        check(shaft[4]['connectedWheel']==w,'Rear wheel driven by shaft: '+w)
    check(not any('wheelaxle'+w in devices for w in ('FL','FR')),'Front wheels unpowered: '+variant)
    engine=parts[ID+'_engine_'+variant]['mainEngine']
    net=[]
    for rpm,gross in engine['torque'][1:]:
        torque=max(0,gross-engine['friction']-engine['dynamicFriction']*rpm*math.pi/30)
        net.append((rpm,torque,torque*rpm*math.pi/30/745.699872))
    hp=max(x[2] for x in net if x[0]<=engine['maxRPM'])
    tq=max(x[1] for x in net)
    check(abs(hp-eng['target_hp'])<.15,'Estimated peak power matches target: '+variant)
    check(abs(tq-eng['target_torque_nm'])<.1,'Estimated peak torque matches target: '+variant)
    mass=sum(n[3]['nodeWeight'] for n in all_nodes.values())+wheel_mass+40*.745
    check(abs(mass-eng['target_mass_kg'])<.02,'Structural mass budget matches target: '+variant)
    info=json.loads((OUT/('info_lx_'+variant+'.json')).read_text())
    for attr in ('Value','Population','Power','Torque','Weight'):
        check(isinstance(info[attr],(int,float)) and info[attr]>0,'Positive career metadata: '+attr)
    check(info['Config Type']=='Factory' and info['Type']=='Car','Career vehicle categories: '+variant)
    check((OUT/('lx_'+variant+'.png')).is_file(),'Selector thumbnail exists: '+variant)
    reports[variant]={'selected_parts':selected,'nodes':len(all_nodes),
                      'estimated_peak_hp':round(hp,3),'estimated_peak_torque_nm':round(tq,3),
                      'nominal_mass_kg_excluding_camera_nodes':round(mass,3),
                      'parts_retail_value':sum(parts[n]['information']['value'] for n in selected)}

report={'status':'Static checks passed; BeamNG execution NOT tested',
        'check_count':len(checks),'mesh_count':len(meshes),
        'configurations':reports,
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(OUT.iterdir()) if p.is_file()}}
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
