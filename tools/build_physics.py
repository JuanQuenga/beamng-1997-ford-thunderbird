#!/usr/bin/env python3
"""Generate an original, standalone BeamNG vehicle from source/spec.json."""
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'source/spec.json').read_text())
ID = SPEC['id']
OUT = ROOT / 'build' / 'vehicles' / ID
OUT.mkdir(parents=True, exist_ok=True)


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n')


def table(*headers):
    return [list(headers)]


nodes = table('id', 'posX', 'posY', 'posZ')
beams = table('id1:', 'id2:')
triangles = table('id1:', 'id2:', 'id3:')
hydros = table('id1:', 'id2:')
positions = {}
node_options = {}
beam_pairs = set()


def node(name, p, weight, group, **options):
    assert name not in positions
    positions[name] = p
    opts = dict(nodeWeight=weight, group=group, selfCollision=False,
                collision=True, nodeMaterial='|NM_METAL', frictionCoef=0.5)
    opts.update(options)
    node_options[name] = opts
    nodes.append([name, *[round(v, 5) for v in p], opts])
    return name


def beam(a, b, **options):
    key = tuple(sorted((a, b)))
    if key in beam_pairs:
        return
    beam_pairs.add(key)
    opts = dict(beamSpring=3200000, beamDamp=90, beamDeform=42000,
                beamStrength=180000, beamType='|NORMAL', beamPrecompression=1)
    opts.update(options)
    beams.append([a, b, opts])


def rigid(names, **options):
    for a, b in itertools.combinations(names, 2):
        beam(a, b, **options)


def tri(a, b, c, **opts):
    triangles.append([a, b, c, dict(dragCoef=0.3, **opts)])


def quad(a, b, c, d):
    tri(a, b, c)
    tri(a, c, d)


# A deformable space frame following the sills, firewall and upper belt line.
stations = [(-2.48, .78, .70), (-1.85, .91, .84), (-1.0, .923, .90),
            (-.25, .923, .91), (.55, .923, .91), (1.2, .91, .89),
            (1.95, .90, .85), (2.48, .81, .77)]
rings = []
for i, (y, w, z) in enumerate(stations):
    ring = []
    for s, x in [('l', w), ('r', -w)]:
        for h, height in [('b', .29), ('t', z)]:
            ring.append(node(f'c{i}{s}{h}', (x, y, height), 1, ID+'_body'))
    ring.append(node(f'c{i}c', (0, y, .32), 1, ID+'_body'))
    rigid(ring)
    if i:
        for a in rings[-1]:
            for b in ring:
                beam(a, b, beamDeform=30000 if i in (1, 7) else 62000)
        old = rings[-1]
        # Clockwise when viewed from outside. No floor faces over the tires.
        quad(old[0], old[4], ring[4], ring[0])
        quad(old[4], old[2], ring[2], ring[4])
        # Side collision panels stop above wheel openings.
        if i in (3, 4):
            quad(old[0], ring[0], ring[1], old[1])
            quad(old[2], old[3], ring[3], ring[2])
    rings.append(ring)
quad('c0lb', 'c0lt', 'c0rt', 'c0rb')
quad('c7lb', 'c7rb', 'c7rt', 'c7lt')

roof_rings = []
for i, (y, w, z) in enumerate([(-.68,.84,.94), (-.06,.66,1.32),
                               (.65,.67,1.349), (1.33,.82,.91)]):
    rr = [node(f'r{i}{s}', (x, y, z + (.015 if s == 'c' and i in (1,2) else 0)),
               4, ID+'_body') for s, x in [('l',w),('c',0),('r',-w)]]
    rigid(rr, beamSpring=1200000, beamDeform=22000)
    nearest = sorted(range(8), key=lambda k: abs(stations[k][0]-y))[:2]
    for a in rr:
        for k in nearest:
            for b in rings[k]:
                beam(a,b,beamSpring=1000000,beamDeform=18000)
    if i:
        for a in roof_rings[-1]:
            for b in rr:
                beam(a,b,beamSpring=1000000,beamDeform=18000)
        # Roof, windshield and rear glass collision surfaces.
        quad(roof_rings[-1][0],rr[0],rr[1],roof_rings[-1][1])
        quad(roof_rings[-1][1],rr[1],rr[2],roof_rings[-1][2])
    roof_rings.append(rr)
node('refup',(0, stations[3][0],.91),2,ID+'_body',collision=False)
node('refleft',(.5, stations[3][0],.32),2,ID+'_body',collision=False)
for row in nodes[1:]:
    if row[0] in ('c5c','c6c'):
        row[4]['engineGroup'] = 'fuel'
for a in rings[3]+rings[4]:
    beam('refup', a)
    beam('refleft', a)

wheel_rows = table('name','hubGroup','group','node1:','node2:','nodeS','nodeArm:','wheelDir')
wheelbase = SPEC['wheelbase_m']
wheel_centers = {}
suspension = {}
for axle, y in [('F',-wheelbase/2),('R',wheelbase/2)]:
    for side, s in [('L',1),('R',-1)]:
        w = axle+side
        z = SPEC['wheel_center_z']
        # Two wishbones, an upright and a steering/toe link provide two initial
        # degrees of freedom. The toe link constrains one, leaving wheel travel.
        points = {
            'lf':(.39,y-.23,.28), 'lr':(.39,y+.23,.28),
            'uf':(.43,y-.18,.55), 'ur':(.43,y+.18,.55),
            'top':(.51,y,.86), 'rack':(.31,y+.16,.37),
            'lo':(.70,y,.27), 'up':(.68,y-.018,.54),
            'arm':(.70,y+.16,.37), 'br':(.70,y-.13,.37),
            'in':(.71,y,z), 'out':(.855,y,z)}
        mount_keys = ['lf','lr','uf','ur','top','rack']
        hub_keys = ['lo','up','arm','br','in','out']
        for k, p in points.items():
            group = ID+'_body' if k in mount_keys else ID+'_hub_'+w
            node(w+k,(s*p[0],p[1],p[2]),3 if k in mount_keys else 2.6,group,
                 collision=False)
        mount_names = [w+k for k in mount_keys]
        rigid(mount_names,beamSpring=5000000,beamDeform=85000)
        near = sorted(range(8),key=lambda k:abs(stations[k][0]-y))[:2]
        for a in mount_names:
            for k in near:
                for b in rings[k]:
                    beam(a,b,beamSpring=4000000,beamDeform=75000)
        rigid([w+k for k in hub_keys],beamSpring=6500000,beamDamp=60,
              beamDeform=80000,beamStrength=200000)
        for a,b in [('lf','lo'),('lr','lo'),('uf','up'),('ur','up')]:
            beam(w+a,w+b,beamSpring=5500000,beamDamp=70,beamDeform=65000)
        if axle == 'F':
            hydros.append([w+'rack',w+'arm',{
                'beamSpring':4500000,'beamDamp':90,'beamDeform':60000,
                'beamStrength':180000,'factor':s*.205,
                'steeringWheelLock':540,'inputSource':'steering_input',
                'inRate':1.8,'outRate':1.8}])
        else:
            beam(w+'rack',w+'arm',beamSpring=4500000,beamDamp=90)
        beam(w+'top',w+'lo',beamSpring=37000 if axle=='F' else 32000,
             beamDamp=2600 if axle=='F' else 2200,beamPrecompression=1.12,
             beamPrecompressionTime=1.0,beamDeform=90000,beamStrength=180000,
             beamType='|BOUNDED',beamShortBound=.20,beamLongBound=.12,
             beamLimitSpring=600000,beamLimitDamp=3000)
        # Wheel axle endpoints always point outward to inward; wheelDir handles
        # which side has the positive driving direction.
        wheel_rows.append([w, ID+'_wheel_'+w, ID+'_tire_'+w,
                           w+'out',w+'in',9999,w+'br',-s,{
                               'torqueCoupling:':w+'lo','torqueArm:':w+'br',
                               'steerAxisUp:':w+'up','steerAxisDown:':w+'lo',
                               'brakeTorque':1700 if axle=='F' else 1100,
                               'parkingTorque':0 if axle=='F' else 1700,
                               'propulsed':0,
                               'enableABS':True}])
        wheel_centers[w] = [s*SPEC['track_m']/2,y,z]
        suspension[w] = {k:positions[w+k] for k in points}

# Anti-roll bars connect the two lower arms through their chassis pivots.
torsionbars = table('id1:','id2:','id3:','id4:')
for ax, rate in [('F',21000),('R',11000)]:
    torsionbars.append([ax+'Llo',ax+'Llr',ax+'Rlr',ax+'Rlo',{
        'spring':rate,'damp':180,'deform':30000,'strength':100000}])

# The common engine block has eight nodes. The selected part supplies its mass.
engine_nodes = []
for i,(x,y,z) in enumerate(itertools.product([-.26,.26],[-1.67,-1.03],[.43,.78])):
    engine_nodes.append(node(f'e{i}',(x,y,z),0,ID+'_engine',collision=False))
rigid(engine_nodes,beamSpring=4500000,beamDamp=100,beamDeform=120000)
for en in engine_nodes:
    near = sorted([n for rr in rings[1:4] for n in rr],
                  key=lambda n:math.dist(positions[en],positions[n]))[:6]
    for b in near:
        beam(en,b,beamSpring=1800000,beamDamp=180,beamDeform=85000)

# Fuel mass is assigned by the tank system. Structural masses plus generated
# pressure-wheel mass and 40 L of fuel equal the two nominal curb mass targets.
wheel_mass = 4*2*16*(.42+.14)
fixed_mass = sum(o['nodeWeight'] for n,o in node_options.items()
                 if not n.startswith('c') and not n.startswith('e'))
chassis_names = [n for n in positions if n.startswith('c')]
body_mass = SPEC['engines']['v6']['target_mass_kg'] - 190 - wheel_mass - 40*.745 - fixed_mass
for row in nodes[1:]:
    if row[0] in chassis_names:
        row[4]['nodeWeight'] = round(body_mass/len(chassis_names),6)
    if row[0].startswith('e'):
        # Overridden with selected engine part below; do not define twice.
        row[4]['nodeWeight'] = 190/8

wheel_defaults = dict(
    selfCollision=False,collision=True,hasTire=True,
    radius=SPEC['tire_radius_m'],tireWidth=SPEC['tire_width_m'],
    hubRadius=SPEC['rim_radius_m'],hubWidth=.16,wheelOffset=0,numRays=16,
    hubNodeWeight=.42,nodeWeight=.14,nodeMaterial='|NM_RUBBER',
    hubNodeMaterial='|NM_METAL',hubFrictionCoef=.5,
    hubBeamSpring=1000000,hubBeamDamp=12,hubBeamDeform=35000,hubBeamStrength=100000,
    pressurePSI=30,frictionCoef=1.0,slidingFrictionCoef=1.0,
    noLoadCoef=1.20,loadSensitivitySlope=.00016,fullLoadCoef=.45,
    softnessCoef=.7,treadCoef=.8,triangleCollision=False,
    enableTireLbeams=True,enableTireReinfBeams=False,enableTireSideReinfBeams=False,
    enableTreadReinfBeams=True,enableTirePeripheryReinfBeams=True,
    wheelSideBeamSpring=22000,wheelSideBeamDamp=35,
    wheelSideBeamSpringExpansion=350000,wheelSideBeamDampExpansion=50,
    wheelSideTransitionZone=.10,wheelSideBeamPrecompression=1,
    wheelTreadBeamSpring=90000,wheelTreadBeamDamp=55,
    wheelTreadReinfBeamSpring=180000,wheelTreadReinfBeamDamp=40,
    wheelPeripheryBeamSpring=60000,wheelPeripheryBeamDamp=35,
    wheelPeripheryReinfBeamSpring=140000,wheelPeripheryReinfBeamDamp=40,
    wheelSideBeamDeform=18000,wheelSideBeamStrength=25000,
    wheelTreadBeamDeform=20000,wheelTreadBeamStrength=30000,
    wheelPeripheryBeamDeform=45000,wheelPeripheryBeamStrength=50000,
    brakeSpring=180,enableBrakeThermals=True,brakeDiameter=.26,
    brakeMass=6,brakeType='vented-disc',rotorMaterial='steel')
wheel_rows.insert(1,wheel_defaults)

main = {
    'information':{'authors':'Juan / Codex','name':'1997 Ford Thunderbird LX prototype','value':9000},
    'slotType':'main',
    'slots':[['type','default','description'],
             [ID+'_engine',ID+'_engine_v6','Engine',{'coreSlot':True}]],
    'controller':[['fileName'],['vehicleController',{}]],
    'refNodes':[['ref:','back:','left:','up:'],['c3c','c4c','refleft','refup']],
    'cameraExternal':{'distance':6,'distanceMin':2,'offset':{'x':0,'y':0,'z':.5},'fov':60},
    'cameraChase':{'distance':6,'distanceMin':2,'offset':{'x':0,'y':0,'z':.6},'fov':60},
    'camerasInternal':[
        ['type','x','y','z','fov','id1:','id2:','id3:','id4:','id5:','id6:'],
        {'nodeWeight':1,'selfCollision':False,'collision':False,
         'beamSpring':10000,'beamDamp':200},
        ['driver',.38,.14,1.12,65,'c3lt','c3rt','c4lt','c4rt','r1l','r2r'],
        ['hood',0,-.83,1.04,65,'c1lt','c1rt','c2lt','c2rt','c3lt','c3rt']],
    'nodes':nodes,'beams':beams,'triangles':triangles,'hydros':hydros,
    'torsionbars':torsionbars,'pressureWheels':wheel_rows,
    'energyStorage':[['type','name'],['fuelTank','mainTank']],
    'mainTank':{'energyType':'gasoline','fuelCapacity':SPEC['fuel_capacity_l'],
                'startingFuelCapacity':40,'fuel':{'[engineGroup]:':['fuel']}},
    'powertrain':[
        ['type','name','inputName','inputIndex'],
        ['torqueConverter','torqueConverter','mainEngine',1],
        ['automaticGearbox','gearbox','torqueConverter',1],
        ['shaft','driveshaft','gearbox',1,{'friction':.4,'uiName':'Driveshaft'}],
        ['differential','differential_R','driveshaft',1,{'diffType':'open',
         'gearRatio':1,'friction':2,'uiName':'Rear differential'}],
        ['shaft','wheelaxleRL','differential_R',1,{'connectedWheel':'RL','friction':.4}],
        ['shaft','wheelaxleRR','differential_R',2,{'connectedWheel':'RR','friction':.4}]],
    'torqueConverter':{'converterDiameter':.29,'converterStiffness':12,
                      'couplingAVRatio':.88,'stallTorqueRatio':2.0,
                      'lockupClutchTorque':550,'additionalEngineInertia':.12},
    'gearbox':{'gearRatios':SPEC['gear_ratios'],'friction':3,
               'dynamicFriction':.002,'torqueLossCoef':.015,
               'parkLockTorque':20000,'oneWayViscousCoef':5,
               'gearChangeTime':.35,'gearboxNode:':['e3']},
    'vehicleController':{'automaticModes':'PRND21','useSmartAggressionCalculation':True,
                         'calculateOptimalLoadShiftPoints':False,
                         'lowShiftDownRPM':1100,'lowShiftUpRPM':2100,
                         'highShiftDownRPM':2200,'highShiftUpRPM':4500,
                         'torqueConverterLockupRPM':1400,'torqueConverterLockupMinGear':3},
    'flexbodies':[['mesh','[group]:','nonFlexMaterials'],
                  [ID+'_body',[ID+'_body']], [ID+'_glass',[ID+'_body']],
                  [ID+'_interior',[ID+'_body']], [ID+'_trim',[ID+'_body']]],
    'glowMap':{}
}

for w in wheel_centers:
    main['flexbodies'] += [[ID+'_rim_'+w,[ID+'_wheel_'+w]],
                          [ID+'_rubber_'+w,[ID+'_tire_'+w,ID+'_wheel_'+w]],
                          [ID+'_hubmesh_'+w,[ID+'_hub_'+w]]]

# Separate lamp materials permit independently operated signals and brakes.
for mat, func in [('head','lowhighbeam'),('tail','brake'),('reverse','reverse'),
                  ('signal_L','signal_L'),('signal_R','signal_R')]:
    name=ID+'_'+mat
    fn={'lowhighbeam':.25,'brake':1} if mat=='tail' else func
    main['glowMap'][name]={'simpleFunction':fn,'off':name,'on':name+'_on',
                          'on_intense':name+'_on'}

# The selected engine part owns its nodes; references resolve after slot assembly.
main['nodes'] = [row for row in nodes if not (isinstance(row,list) and
                  isinstance(row[0],str) and row[0].startswith('e'))]

# Price and expose each wheel as an independent career-replaceable assembly.
wheel_parts={}
for row in wheel_rows[2:]:
    w=row[0]
    slot=ID+'_wheel_'+w
    main['slots'].append([slot,slot,'Wheel '+w,{'coreSlot':True}])
    wheel_parts[slot]={
        'information':{'authors':'Juan / Codex','name':'15 inch alloy with P215/70R15 tire '+w,'value':250},
        'slotType':slot,'pressureWheels':[wheel_rows[0],wheel_defaults,row],
        'flexbodies':[['mesh','[group]:','nonFlexMaterials'],
                     [ID+'_rim_'+w,[ID+'_wheel_'+w]],
                     [ID+'_rubber_'+w,[ID+'_tire_'+w,ID+'_wheel_'+w]]]}
main.pop('pressureWheels')
main['flexbodies']=[r for r in main['flexbodies'] if not
                   (r[0].startswith(ID+'_rim_') or r[0].startswith(ID+'_rubber_'))]
write(ID+'_wheels.jbeam',wheel_parts)

# Keep transmission pricing and removal independent of the engine swap.
transmission={
    'information':{'authors':'Juan / Codex','name':'4R70W four-speed automatic','value':1400},
    'slotType':ID+'_transmission','gearbox':main.pop('gearbox'),
    'torqueConverter':main.pop('torqueConverter'),
    'powertrain':[main['powertrain'][0],*main['powertrain'][1:3]]}
main['powertrain']=[main['powertrain'][0],*main['powertrain'][3:]]
main['slots'].append([ID+'_transmission',ID+'_transmission','Transmission',{'coreSlot':True}])
write(ID+'_transmission.jbeam',{ID+'_transmission':transmission})
write(ID+'.jbeam',{ID:main})
engines={}
for key,e in SPEC['engines'].items():
    # BeamNG subtracts friction from its gross torque curve. Add that friction
    # here so the net curve matches the specified output.
    torque=[['rpm','torque']]+[[rpm,round(t+e['friction']+
              e['dynamic_friction']*rpm*math.pi/30,4)] if rpm else [0,0]
              for rpm,t in e['net_torque_nm']]
    engines[ID+'_engine_'+key]={
        'information':{'authors':'Juan / Codex','name':e['name']+' estimated stock output','value':1800 if key=='v6' else 2500},
        'slotType':ID+'_engine',
        'powertrain':[['type','name','inputName','inputIndex'],
                      ['combustionEngine','mainEngine','dummy',0]],
        'mainEngine':{'torque':torque,'idleRPM':e['idle_rpm'],'maxRPM':e['max_rpm'],
                      'hasRevLimiter':True,'revLimiterRPM':e['max_rpm'],
                      'inertia':.22 if key=='v6' else .27,
                      'friction':e['friction'],'dynamicFriction':e['dynamic_friction'],
                      'engineBrakeTorque':30,'burnEfficiency':.28,
                      'energyStorage':'mainTank','requiredEnergyType':'gasoline',
                      'thermalsEnabled':False,'torqueReactionNodes:':['e0','e4','e3'],
                      'uiName':e['name'],'soundConfig':'soundConfig',
                      'soundConfigExhaust':'soundConfigExhaust',
                      'starterMaxRPM':900,'starterTorque':140,'maxIdleThrottle':.15},
        'soundConfig':{'sampleName':'V6_engine' if key=='v6' else 'V8_2_engine',
                       'mainGain':-12,'onLoadGain':1,'offLoadGain':.7,
                       'fundamentalFrequencyCylinderCount':e['cylinders']},
        'soundConfigExhaust':{'sampleName':'V6_exhaust' if key=='v6' else 'V8_2_exhaust',
                              'mainGain':-5,'onLoadGain':1,'offLoadGain':.6,
                              'fundamentalFrequencyCylinderCount':e['cylinders']},
        'driveshaft':{'gearRatio':e['final_drive']},
        'vehicleController':{'highShiftUpRPM':4400 if key=='v6' else 5100},
        'nodes':[['id','posX','posY','posZ']]+[
            [n,*positions[n],{'nodeWeight':e['engine_mass_kg']/8,
                             'group':ID+'_engine','collision':False,'selfCollision':False}]
            for n in engine_nodes],
        'flexbodies':[['mesh','[group]:','nonFlexMaterials'],
                     [ID+'_engine_mesh_'+key,[ID+'_engine']]]}
    pc={'format':2,'model':ID,'mainPartName':ID,
        'parts':{'main':ID,ID+'_engine':ID+'_engine_'+key},
        'vars':{}}
    pc['parts'].update({ID+'_wheel_'+w:ID+'_wheel_'+w for w in wheel_centers})
    pc['parts'][ID+'_transmission']=ID+'_transmission'
    write('lx_'+key+'.pc',pc)
    write('info_lx_'+key+'.json',{
        'Configuration':e['name']+' 4-speed automatic [prototype]',
        'Description':'Original experimental Thunderbird model. Estimated stock power; untested handling and damage.',
        'Transmission':'Automatic','Drivetrain':'RWD','Fuel Type':'Gasoline',
        'Body Style':'Coupe','Config Type':'Factory','Value':20000 if key=='v6' else 22000,
        'Type':'Car','Brand':'Ford','Country':'United States',
        'Power':round(e['target_hp']*.745699872,2),
        'Torque':e['target_torque_nm'],'Weight':e['target_mass_kg'],
        'Weight/Power':round(e['target_mass_kg']/(e['target_hp']*.745699872),3),
        'PowerPeakRPM':e['peak_power_rpm'],
        'TorquePeakRPM':2750 if key=='v6' else 3000,
        'Propulsion':'ICE','Induction Type':'NA',
        'Population':4000 if key=='v6' else 6000,
        'defaultPaintName1':'Alpine green' if key=='v6' else 'Burgundy',
        'Years':{'min':1997,'max':1997}})
write(ID+'_engines.jbeam',engines)
write('info.json',{'Name':'Thunderbird LX [experimental]','Brand':'Ford',
                   'Author':'Juan / Codex','Country':'United States','Type':'Car',
                   'Body Style':'Coupe','default_pc':'lx_v6',
                   'Years':{'min':1997,'max':1997},
                   'paints':{'Alpine green':{'baseColor':SPEC['engines']['v6']['paint'],
                              'metallic':.6,'roughness':.22,'clearcoat':1,'clearcoatRoughness':.08},
                             'Burgundy':{'baseColor':SPEC['engines']['v8']['paint'],
                              'metallic':.6,'roughness':.22,'clearcoat':1,'clearcoatRoughness':.08},
                             'Silver':{'baseColor':[.55,.58,.6,1],
                              'metallic':.8,'roughness':.25,'clearcoat':1,'clearcoatRoughness':.08}}})

# Shared geometry contract used by Blender and the independent validator.
(ROOT/'source'/'geometry.json').write_text(json.dumps({
    'wheel_centers':wheel_centers,'suspension':suspension,
    'nodes':positions,'generated_wheel_mass_kg':wheel_mass,
    'chassis_mass_kg':body_mass},indent=2)+'\n')
print(f'Generated {len(positions)} nodes, {len(beams)-1} beams and four pressure wheels.')
