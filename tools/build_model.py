"""Run with Blender 4.2 LTS: blender -b -t 4 --python tools/build_model.py."""
import bpy
import bmesh
import json
import math
import sys
from mathutils import Vector
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'source/spec.json').read_text())
GEO=json.loads((ROOT/'source/geometry.json').read_text())
ID=SPEC['id']
OUT=ROOT/'build'/'vehicles'/ID
RENDERS=ROOT/'renders'
RENDERS.mkdir(exist_ok=True)
RENDER='--skip-render' not in sys.argv
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
parts={}
materials={}
beam_materials={}


def material(key,color,metal=0,rough=.4,alpha=1):
    name=ID+'_'+key
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*color,alpha)
    mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal
    p.inputs['Roughness'].default_value=rough
    p.inputs['Alpha'].default_value=alpha
    if key=='paint':
        p.inputs['Coat Weight'].default_value=.65
        p.inputs['Coat Roughness'].default_value=.15
    if key=='glass':
        # Use physical glass for the Blender render, alpha blending in BeamNG.
        p.inputs['Transmission Weight'].default_value=.9
        p.inputs['Alpha'].default_value=1
        p.inputs['IOR'].default_value=1.45
    materials[key]=mat
    stage={'baseColorFactor':[*color,alpha],'metallicFactor':metal,
           'roughnessFactor':rough,'useAnisotropic':True}
    bm={'name':name,'mapTo':name,'class':'Material','Stages':[stage,{}, {}, {}],
        'dynamicCubemap':True,'doubleSided':True,'materialTag0':'vehicle','version':1.5}
    if key=='paint':
        # A generated red palette texture makes the first vehicle color editable.
        stage.update(instanceDiffuse=True,baseColorFactor=[1,1,1,1],
                     colorPaletteMap=f'/vehicles/{ID}/paint_palette.color.png',
                     metallicFactor=.6,roughnessFactor=.22,
                     clearCoatFactor=1,clearCoatRoughnessFactor=.08)
    if alpha<1:
        bm.update(translucent=True,translucentBlendOp='LerpAlpha',
                  translucentZWrite=False,castShadows=False)
    beam_materials[name]=bm
    return mat


material('paint',(.025,.12,.085),.6,.22)
material('glass',(.16,.22,.24),.15,.12,.27)
material('black',(.012,.015,.018),.05,.48)
material('rubber',(.018,.021,.024),0,.78)
material('chrome',(.65,.69,.73),.95,.19)
material('alloy',(.43,.47,.5),.82,.28)
material('steel',(.16,.19,.21),.75,.37)
material('cloth',(.18,.19,.20),0,.88)
material('dash',(.045,.05,.055),0,.62)
material('gauge',(.005,.008,.009),0,.45)
material('white',(.83,.87,.83),.05,.32)
material('needle',(.85,.16,.035),.1,.3)
material('head',(.72,.78,.8),.35,.18)
material('tail',(.29,.004,.009),.2,.23)
material('reverse',(.7,.72,.7),.2,.25)
material('signal_L',(.8,.19,.01),.15,.22)
material('signal_R',(.8,.19,.01),.15,.22)
for key in ['head','tail','reverse','signal_L','signal_R']:
    base=beam_materials[ID+'_'+key]
    on=json.loads(json.dumps(base))
    on['name']=on['mapTo']=ID+'_'+key+'_on'
    on['Stages'][0].update(emissive=True,emissiveFactor=[2.5,2.5,2.5])
    beam_materials[on['name']]=on


def collect(obj,part):
    parts.setdefault(part,[]).append(obj)
    return obj


def mesh(name,verts,faces,mat,part,smooth=True):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(materials[mat])
    for p in data.polygons:p.use_smooth=smooth
    return collect(obj,part)


def grid(name,nu,nv,fn,mat,part,flip=False):
    verts=[fn(i/nu,j/nv) for i in range(nu+1) for j in range(nv+1)]
    faces=[]
    for i in range(nu):
        for j in range(nv):
            a=i*(nv+1)+j
            f=(a,a+nv+1,a+nv+2,a+1)
            faces.append(tuple(reversed(f)) if flip else f)
    return mesh(name,verts,faces,mat,part)


def box(name,loc,size,mat,part,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object
    obj.name=name
    obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(materials[mat])
    if bevel:
        mod=obj.modifiers.new('Edge radius','BEVEL')
        mod.width=bevel
        mod.segments=3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=obj.modifiers.new('Corner normals','WEIGHTED_NORMAL')
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return collect(obj,part)


def tube(name,points,r,mat,part,closed=False):
    curve=bpy.data.curves.new(name,'CURVE')
    curve.dimensions='3D'
    curve.resolution_u=1
    curve.bevel_depth=r
    curve.bevel_resolution=2
    sp=curve.splines.new('POLY')
    sp.points.add(len(points)-1)
    for p,v in zip(sp.points,points):p.co=(*v,1)
    sp.use_cyclic_u=closed
    obj=bpy.data.objects.new(name,curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(materials[mat])
    return collect(obj,part)


def cylinder(name,center,r,depth,mat,part,axis='X',segments=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=r,depth=depth,location=center)
    obj=bpy.context.object
    obj.name=name
    if axis=='X':obj.rotation_euler[1]=math.pi/2
    if axis=='Y':obj.rotation_euler[0]=math.pi/2
    obj.data.materials.append(materials[mat])
    for p in obj.data.polygons:p.use_smooth=len(p.vertices)==4
    return collect(obj,part)


def text_mesh(label,loc,size,mat,part,rotation=(math.pi/2,0,0)):
    curve=bpy.data.curves.new(label,'FONT')
    curve.body=label
    curve.align_x='CENTER'
    curve.size=size
    curve.extrude=.0003
    obj=bpy.data.objects.new(label,curve)
    bpy.context.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=rotation
    obj.data.materials.append(materials[mat])
    return collect(obj,part)


def lerp(a,b,t):return a+(b-a)*t


profile=[(-2.545,.71,.68),(-2.4,.84,.74),(-2.0,.90,.80),
         (-1.4,.923,.86),(-.68,.91,.92),(.4,.923,.91),
         (1.3,.91,.90),(1.8,.91,.86),(2.4,.86,.80),(2.545,.73,.72)]


def body_profile(y):
    for (ya,wa,za),(yb,wb,zb) in zip(profile,profile[1:]):
        if ya<=y<=yb:
            t=(y-ya)/(yb-ya)
            return lerp(wa,wb,t),lerp(za,zb,t)
    return profile[0][1:] if y<0 else profile[-1][1:]


def arch_bottom(y):
    z=.285
    for cy in [-SPEC['wheelbase_m']/2,SPEC['wheelbase_m']/2]:
        dy=abs(y-cy)
        if dy<.397:
            z=max(z,.351+math.sqrt(.397**2-dy**2))
    return z


# Quarter panels and door skins have real open wheel arches.
for s in [-1,1]:
    def side_surface(u,v):
        y=lerp(-2.545,2.545,u)
        w,top=body_profile(y)
        bottom=arch_bottom(y)
        z=lerp(bottom,top,v)
        x=w-.052*(1-v)**2+.009*math.sin(v*math.pi)
        return s*x,y,z
    grid('Door and quarter panel',200,8,side_surface,'paint','body',flip=s<0)
    # A soft raised lip surrounds each wheel opening.
    for cy in [-SPEC['wheelbase_m']/2,SPEC['wheelbase_m']/2]:
        pts=[]
        for k in range(49):
            a=math.pi*k/48
            y=cy+.397*math.cos(a)
            pts.append((s*(body_profile(y)[0]+.003),y,.351+.397*math.sin(a)))
        tube('Wheel arch edge',pts,.008,'paint','body')
    tube('Body side molding',[(s*(body_profile(y)[0]+.007),y,.51)
                              for y in [lerp(-1.01,1.01,k/35) for k in range(36)]],
         .018,'black','trim')
    tube('Rocker panel',[(s*.885,y,.31) for y in [-1.01,-.7,0,.7,1.01]],
         .026,'paint','body')
    # Door seam and flush handle.
    outline=[(-.66,.89),(-.60,.66),(-.52,.34),(.71,.34),(.78,.85),(.74,.91)]
    tube('Door cut line',[(s*(body_profile(y)[0]+.009),y,z) for y,z in outline],
         .0025,'black','trim')
    box('Door handle recess',(s*.928,.56,.808),(.008,.145,.042),'black','trim',.012)
    box('Flush door handle',(s*.935,.55,.817),(.009,.118,.018),'chrome','trim',.006)
    # Mirror housing and inset reflective face.
    box('Mirror pedestal',(s*.935,-.48,.93),(.095,.10,.045),'black','trim',.018)
    box('Side mirror',(s*1.006,-.44,.974),(.13,.20,.09),'paint','body',.035)
    box('Mirror glass',(s*1.006,-.335,.978),(.105,.005,.063),'chrome','trim',.015)
    box('Inner door card',(s*.858,.08,.66),(.035,1.15,.40),'dash','interior',.025)
    box('Door arm rest',(s*.81,.12,.67),(.10,.42,.065),'cloth','interior',.02)

# Hood and rear deck are curved across the car and taper with the fenders.
for name,ya,yb,mat,part in [('Hood',-2.545,-.68,'paint','body'),
                          ('Rear deck',1.33,2.545,'paint','body')]:
    def deck(u,v):
        t=2*v-1
        if name=='Hood':
            w=lerp(.84,.91,u)
            y=lerp(ya+.14*abs(t)**5,yb,u)
            z=lerp(.746,.92,u)
        else:
            w=lerp(.91,.84,u)
            y=lerp(ya,yb-.14*abs(t)**5,u)
            z=lerp(.90,.79,u)
        return t*w,y,z+.020*(1-t*t)
    grid(name,48,32,deck,mat,part,flip=True)
    # Fine shut lines along the edges.
    for s in [-1,1]:
        tube(name+' seam',[(s*(body_profile(y)[0]-.055),y,
                            body_profile(y)[1]+.004)
                           for y in [lerp(ya,yb,k/32) for k in range(33)]],
             .002,'black','trim')


def bumper(front):
    sign=-1 if front else 1
    def surf(u,v):
        x=lerp(-.84,.84,u)
        z=lerp(.29,.745 if front else .78,v)
        y=sign*(2.545-.14*(abs(x)/.84)**5-.012*(2*v-1)**2)
        return x,y,z
    grid('Front bumper' if front else 'Rear bumper',64,16,surf,'paint','body',flip=front)
    tube('Bumper rub strip',[(x,sign*(2.55-.14*(abs(x)/.84)**5),.46)
                             for x in [lerp(-.83,.83,k/60) for k in range(61)]],
         .014,'black','trim')
bumper(True)
bumper(False)

# Narrow grille, two shaped lamps, and the inset lower air opening.
box('Lower air opening',(0,-2.548,.385),(1.10,.012,.095),'black','trim',.035)
box('Oval grille',(0,-2.546,.652),(.48,.016,.092),'black','trim',.04)
for s in [-1,1]:
    def lamp(u,v):
        x=s*lerp(.29,.83,u)
        y=-2.558+.14*(abs(x)/.84)**5
        return x,y,lerp(.628+.014*u,.724+.028*u,v)
    grid('Headlamp lens',24,5,lamp,'head','trim',flip=s<0)
    verts=[lamp(0,0),lamp(1,0),lamp(1,1),lamp(0,1)]
    tube('Headlamp seal',verts,.006,'black','trim',True)
    # Lens fluting is original geometry, with no external photographs/textures.
    for k in range(1,16):
        t=k/16
        a=Vector(lamp(t,0))
        b=Vector(lamp(t,1))
        tube('Headlight lens flute',[a,b],.0011,'white','trim')
    grid('Corner marker',8,4,lambda u,v:lamp(.80+.20*u,v),
         'signal_L' if s>0 else 'signal_R','trim',flip=s<0)
    # Rear lamps wrap around the corners.
    def tail(u,v):
        x=s*lerp(0,.82,u)
        return x,2.56-.14*(abs(x)/.84)**5,lerp(.675,.795,v)
    grid('Tail lamp',24,4,tail,'tail','trim',flip=s<0)
    box('Reverse lens',(s*.24,2.568,.722),(.15,.008,.057),'reverse','trim',.007)
    box('Tail corner marker',(s*.873,2.35,.732),(.012,.17,.10),
        'tail','trim',.014)
box('Rear license recess',(0,2.55,.53),(.40,.012,.155),'black','trim',.015)
box('Rear license plate',(0,2.562,.535),(.305,.006,.15),'white','trim',.008)
box('Front license plate',(0,-2.56,.415),(.305,.005,.15),'white','trim',.008)
text_mesh('TB97',(0,-2.565,.395),.065,'black','trim')
text_mesh('TB97',(0,2.568,.515),.065,'black','trim',(-math.pi/2,0,math.pi))
text_mesh('THUNDERBIRD LX',(0,2.558,.817),.025,'chrome','trim',(-math.pi/2,0,math.pi))

# A stylized original bird emblem instead of an imported logo texture.
bird=[(-.15,0,.006),(-.042,0,-.01),(0,0,-.036),(.042,0,-.01),(.15,0,.006),
      (.055,0,-.035),(.012,0,-.028),(0,0,-.063),(-.012,0,-.028),(-.055,0,-.035)]
mesh('Bird emblem',[(x,y-2.563,z+.688) for x,y,z in bird],
     [tuple(range(len(bird)))],'chrome','trim',False)

# Windshield, crown, rear window and coupe side glass.
def windshield(u,v):
    x=lerp(-1,1,v)*lerp(.84,.66,u)
    return x,lerp(-.68,-.06,u)-.026*(1-(2*v-1)**2),lerp(.946,1.32,u)+.016*(1-(2*v-1)**2)
grid('Windshield',20,32,windshield,'glass','glass',True)
grid('Roof',30,32,lambda u,v:(lerp(-.66,.66,v),lerp(-.06,.65,u),
                             1.325+.010*u+.013*math.sin(math.pi*u)+.014*(1-(2*v-1)**2)),
     'paint','body',True)
grid('Rear glass',20,32,lambda u,v:(lerp(-1,1,v)*lerp(.67,.82,u),
                                  lerp(.65,1.33,u),lerp(1.335,.918,u)+.013*(1-(2*v-1)**2)),
     'glass','glass',True)
for s in [-1,1]:
    main=[(s*.843,-.63,.944),(s*.675,-.03,1.303),
          (s*.681,.61,1.317),(s*.882,.64,.926)]
    quarter=[(s*.695,.68,1.308),(s*.78,1.12,1.035),
             (s*.858,1.28,.923),(s*.885,.705,.926)]
    mesh('Door window',main,[(3,2,1,0) if s>0 else (0,1,2,3)],'glass','glass')
    mesh('Quarter window',quarter,[(3,2,1,0) if s>0 else (0,1,2,3)],'glass','glass')
    tube('Window rubber',main,.012,'black','trim',True)
    tube('Quarter window rubber',quarter,.013,'black','trim',True)
    tube('A pillar',[(s*.86,-.68,.93),(s*.665,-.06,1.325)],.025,'paint','body')
    tube('Roof side rail',[(s*.665,-.06,1.325),(s*.68,.65,1.335)],.021,'paint','body')
    mesh('C pillar',[(s*.68,.65,1.335),(s*.82,1.33,.918),
                     (s*.91,1.48,.90),(s*.755,.60,1.315)],
         [(0,1,2,3) if s>0 else (3,2,1,0)],'paint','body')
    tube('B pillar',[(s*.685,.645,1.317),(s*.89,.67,.925)],.023,'black','trim')
    tube('Belt line trim',[(s*body_profile(y)[0],y,body_profile(y)[1]+.01)
                           for y in [-.67,-.3,.1,.6,1.1,1.35]],.009,'black','trim')
    tube('Windshield wiper',[(s*.44,-.701,.953),(s*.29,-.5,1.052)],.007,'black','trim')

# Interior: separate front seats, a rear bench, dashboard and console.
box('Floor',(0,.3,.315),(1.58,2.65,.07),'dash','interior',.02)
box('Parcel shelf',(0,1.15,.79),(1.52,.50,.055),'cloth','interior',.02)
box('Rear bench cushion',(0,.88,.52),(1.4,.51,.15),'cloth','interior',.065)
seatback=box('Rear bench back',(0,1.08,.73),(1.4,.13,.41),'cloth','interior',.06)
seatback.rotation_euler[0]=math.radians(-14)
for x in [-.4,.4]:
    box('Seat base',(x,.21,.47),(.52,.55,.14),'cloth','interior',.055)
    back=box('Front seat back',(x,.47,.73),(.52,.15,.47),'cloth','interior',.055)
    back.rotation_euler[0]=math.radians(-12)
    box('Head restraint',(x,.51,1.01),(.27,.12,.16),'cloth','interior',.045)
    for dx in [-.205,.205]:
        box('Seat bolster',(x+dx,.2,.54),(.10,.48,.11),'cloth','interior',.04)
    for dx in [-.13,0,.13]:
        tube('Seat seam',[(x+dx,-.01,.548),(x+dx,.36,.548)],.002,'dash','interior')
box('Dashboard',(0,-.52,.83),(1.66,.32,.21),'dash','interior',.06)
box('Center console',(0,.02,.52),(.28,.92,.21),'dash','interior',.035)
box('Shifter surround',(0,-.16,.635),(.18,.26,.018),'black','interior',.014)
tube('Gear lever',[(.035,-.20,.64),(.035,-.20,.77)],.013,'black','interior')
box('Gear knob',(.035,-.20,.77),(.055,.065,.04),'black','interior',.017)
for x in [-.65,-.12,.20,.65]:
    box('Dash vent',(x,-.347,.872),(.17,.015,.065),'black','interior',.01)
    for k in range(4):
        box('Vent slat',(x,-.338,.852+k*.012),(.15,.005,.003),'steel','interior',0)
box('Radio',(0,-.337,.76),(.20,.02,.062),'black','interior',.008)
box('Radio display',(0,-.322,.77),(.115,.005,.024),'glass','interior',.002)
for x in [-.08,.08]:cylinder('Radio knob',(x,-.313,.755),.015,.018,'black','interior','Y',24)
# Static analog gauge artwork. Live needles can be added after in-game tuning.
for x,r in [(.28,.061),(.44,.061),(.58,.032)]:
    cylinder('Gauge dial',(x,-.338,.88),r,.009,'gauge','interior','Y',48)
    for k in range(13):
        a=math.radians(-220+260*k/12)
        p1=(x+math.cos(a)*r*.83,-.331,.88+math.sin(a)*r*.83)
        p2=(x+math.cos(a)*r*.95,-.331,.88+math.sin(a)*r*.95)
        tube('Gauge tick',[p1,p2],.0015,'white','interior')
    tube('Gauge needle',[(x,-.327,.88),(x-r*.72,-.327,.865)],.0018,'needle','interior')

# Steering wheel is a prop with a local origin at the column pivot.
wheel_center=Vector((.39,-.22,.89))
tilt=math.radians(18)
steer=[]
for k in range(65):
    a=2*math.pi*k/64
    steer.append((math.cos(a)*.166,math.sin(a)*.166*math.sin(tilt),math.sin(a)*.166*math.cos(tilt)))
tube('Steering rim',steer,.014,'black','steering')
box('Airbag hub',(0,0,0),(.17,.055,.09),'dash','steering',.025)
for s in [-1,1]:
    tube('Steering spoke',[(s*.07,0,-.015),(s*.15,0,-.035)],.014,'dash','steering')
tube('Steering lower spoke',[(0,0,-.035),(0,-.04,-.15)],.012,'dash','steering')
for obj in parts['steering']:obj.location+=wheel_center
tube('Steering column',[wheel_center,(.39,-.43,.78)],.025,'black','interior')

# Original rounded tire profiles and 15 inch five-spoke alloy wheels.
for w,center in GEO['wheel_centers'].items():
    cx,cy,cz=center
    s=1 if cx>0 else -1
    profile_tire=[(-.106,.207),(-.112,.265),(-.105,.316),(-.08,.337),
                  (-.052,.341),(.052,.341),(.08,.337),(.105,.316),(.112,.265),(.106,.207)]
    verts=[]
    for dx,r in profile_tire:
        for k in range(64):
            a=2*math.pi*k/64
            verts.append((cx+dx,cy+r*math.cos(a),cz+r*math.sin(a)))
    faces=[]
    for j in range(len(profile_tire)-1):
        for k in range(64):faces.append((j*64+k,j*64+(k+1)%64,(j+1)*64+(k+1)%64,(j+1)*64+k))
    mesh('Tire',verts,faces,'rubber','rubber_'+w)
    for dx in [-.052,0,.052]:
        pts=[(cx+dx,cy+.3415*math.cos(2*math.pi*k/64),cz+.3415*math.sin(2*math.pi*k/64)) for k in range(64)]
        tube('Tread groove',pts,.0018,'black','rubber_'+w,True)
    # The barrel and lip are rings with open centers, not solid disks.
    def ring(name,x,r0,r1,mat):
        vs=[]
        for r in [r0,r1]:
            vs.extend([(x,cy+r*math.cos(2*math.pi*k/64),cz+r*math.sin(2*math.pi*k/64)) for k in range(64)])
        fs=[(k,(k+1)%64,64+(k+1)%64,64+k) for k in range(64)]
        return mesh(name,vs,fs,mat,'rim_'+w)
    xface=cx+s*.105
    ring('Alloy rim lip',xface,.174,.196,'chrome')
    ring('Rim barrel inner',cx-s*.07,.171,.191,'alloy')
    for k in range(5):
        a=2*math.pi*k/5+.15
        # A swept, tapered spoke with depth.
        vs=[]
        for depth in [0,-s*.032]:
            for r,aa in [(.045,a-.28),(.179,a-.12),(.179,a+.19),(.045,a+.45)]:
                vs.append((xface+depth,cy+r*math.cos(aa),cz+r*math.sin(aa)))
        mesh('Swept alloy spoke',vs,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'alloy','rim_'+w)
        cylinder('Lug nut',(xface+s*.005,cy+.044*math.cos(a),cz+.044*math.sin(a)),.009,.015,'chrome','rim_'+w,segments=12)
    cylinder('Wheel center',(xface,cy,cz),.034,.022,'alloy','rim_'+w)
    cylinder('Brake rotor',(cx,cy,cz),.126,.016,'steel','hubmesh_'+w)
    box('Brake caliper',(cx+s*.02,cy+.11,cz),(.06,.06,.13),'steel','hubmesh_'+w,.018)
    # Suspension arms bind to their own upright and chassis groups later.
    sp=GEO['suspension'][w]
    for a,b in [('lf','lo'),('lr','lo'),('uf','up'),('ur','up')]:
        tube('Control arm',[sp[a],sp[b]],.017,'steel','susp_'+w)
    tube('Damper',[sp['lo'],sp['top']],.024,'steel','susp_'+w)
    p0,p1=Vector(sp['lo']),Vector(sp['top'])
    coil=[]
    for k in range(161):
        t=.18+.66*k/160
        p=p0.lerp(p1,t)
        a=2*math.pi*7*k/160
        p+=Vector((.055*math.cos(a),.055*math.sin(a),0))
        coil.append(p)
    tube('Coil spring',coil,.007,'black','susp_'+w)

# Underbody, exhaust and the selected engine's visible geometry.
box('Fuel tank',(0,1.30,.36),(.9,.55,.17),'black','trim',.05)
tube('Exhaust pipe',[(.28,-1.2,.29),(.26,-.5,.25),(.26,.8,.25),(.37,1.6,.25),(.37,2.4,.29)],
     .025,'steel','trim')
box('Muffler',(.37,1.91,.28),(.25,.45,.12),'steel','trim',.035)
cylinder('Exhaust tip',(.37,2.44,.29),.035,.20,'chrome','trim','Y')
for key in ['v6','v8']:
    part='engine_mesh_'+key
    box('Engine block',(0,-1.36,.56),(.50,.60 if key=='v6' else .70,.27),'steel',part,.035)
    for s in [-1,1]:
        cover=box('Valve cover',(s*.205,-1.35,.73),(.18,.56 if key=='v6' else .69,.14),'alloy',part,.03)
        cover.rotation_euler[1]=s*math.radians(24)
    box('Intake manifold',(0,-1.33,.79),(.28,.42,.12),'alloy',part,.025)
    box('Airbox',(-.48,-1.48,.63),(.27,.32,.18),'black',part,.025)
    tube('Intake duct',[(-.48,-1.32,.70),(-.35,-1.10,.78),(0,-1.1,.80)],.045,'black',part)

# Convert and join every visible object by its JBeam flexbody/prop name.
joined={}
for part,objects in parts.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    obj=bpy.context.object
    obj.name=ID+'_'+part
    obj.data.name=obj.name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # UVs are sufficient for uniform swatches and the paint palette texture.
    if not obj.data.uv_layers:obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            p=obj.data.vertices[obj.data.loops[li].vertex_index].co
            obj.data.uv_layers.active.data[li].uv=(p.x*.5+.5,p.y*.15+.5)
    joined[part]=obj

# Write PBR material definitions and a self-contained paint mask.
palette=bpy.data.images.new('Paint palette',width=4,height=4,alpha=True)
palette.pixels=[1,0,0,1]*16
palette.filepath_raw=str(OUT/'paint_palette.color.png')
palette.file_format='PNG'
palette.save()
(OUT/'main.materials.json').write_text(json.dumps(beam_materials,indent=2)+'\n')

# Add model bindings generated from the exact mesh names.
path=OUT/(ID+'.jbeam')
data=json.loads(path.read_text())
main=data[ID]
for w in GEO['wheel_centers']:
    main['flexbodies'].append([ID+'_susp_'+w,[ID+'_body',ID+'_hub_'+w]])
main['flexbodies'].append([ID+'_steering',[ID+'_body']])
path.write_text(json.dumps(data,indent=2)+'\n')

# Export only car objects; lights, cameras and the render floor stay out.
bpy.ops.object.select_all(action='DESELECT')
for o in joined.values():o.select_set(True)
bpy.ops.wm.collada_export(filepath=str(OUT/(ID+'.dae')),selected=True,
                          apply_modifiers=True,triangulate=True,use_texture_copies=False)

# A studio scene is saved alongside the editable model for inspection.
floor=box('Studio floor',(0,0,-.025),(200,200,.04),'dash','_studio',0)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.world.color=(.18,.18,.18)
world=scene.world
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.21,.25,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45
for loc,energy,size in [((2,-3,7),1500,5),((-4,-1,4),1200,5),((1,5,5),1800,4)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    light=bpy.context.object
    light.data.energy=energy
    light.data.shape='DISK'
    light.data.size=size
    light.rotation_euler=(Vector((0,0,.5))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(7.2,-8.5,4.1))
cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.65))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'
cam.data.ortho_scale=6.7
scene.camera=cam
scene.render.resolution_x=1400
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
joined['engine_mesh_v8'].hide_render=True
joined['engine_mesh_v8'].hide_viewport=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source'/'thunderbird_1997.blend'))
scene.render.filepath=str(RENDERS/'thunderbird_front.png')
if RENDER:bpy.ops.render.render(write_still=True)
# Per-configuration selector images have identical camera and lighting.
scene.render.resolution_x=800
scene.render.resolution_y=500
for key,e in SPEC['engines'].items():
    materials['paint'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=e['paint']
    joined['engine_mesh_v6'].hide_render=key!='v6'
    joined['engine_mesh_v8'].hide_render=key!='v8'
    scene.render.filepath=str(OUT/('lx_'+key+'.png'))
    if RENDER:bpy.ops.render.render(write_still=True)
cam.location=(7,8,3.5)
cam.rotation_euler=(Vector((0,.1,.65))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1400
scene.render.resolution_y=900
scene.render.filepath=str(RENDERS/'thunderbird_rear.png')
if RENDER:bpy.ops.render.render(write_still=True)
manifest={part:{'mesh':obj.name,'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons)}
          for part,obj in joined.items()}
(ROOT/'source'/'model_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('MODEL_BUILD_COMPLETE',len(joined),'meshes')
