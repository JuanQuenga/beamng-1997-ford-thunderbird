"""Round-trip the shipped DAE in Blender and check the structural constraint rank."""
import bpy
import json
import hashlib
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
ID='juan_tb97'
OUT=ROOT/'build'/'vehicles'/ID
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.wm.collada_import(filepath=str(OUT/(ID+'.dae')))
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
manifest=json.loads((ROOT/'source/model_manifest.json').read_text())
assert {o.name for o in objs}=={m['mesh'] for m in manifest.values()}
assert all(len(o.data.vertices)>0 and len(o.data.polygons)>0 for o in objs)
assert all(all(np.isfinite(v.co)) for o in objs for v in o.data.vertices)
world_points=np.array([tuple(o.matrix_world@v.co) for o in objs for v in o.data.vertices])
extents=world_points.max(axis=0)-world_points.min(axis=0)
assert 5.04<extents[1]<5.20,extents
assert 1.30<extents[2]<1.42,extents

parts={}
for p in OUT.glob('*.jbeam'):parts.update(json.loads(p.read_text()))
main=parts[ID]
engine=parts[ID+'_engine_v6']
node_rows=main['nodes'][1:]+engine['nodes'][1:]
nodes={r[0]:np.array(r[1:4],dtype=float) for r in node_rows}
indices={n:i for i,n in enumerate(nodes)}
constraints=[]
constraint_count_without_springs=0
for section in ('beams','hydros'):
    for row in main[section][1:]:
        if not isinstance(row,list):continue
        a,b,opts=row
        if opts['beamSpring']<100000:continue
        direction=nodes[b]-nodes[a]
        direction/=np.linalg.norm(direction)
        r=np.zeros(len(nodes)*3)
        r[indices[a]*3:indices[a]*3+3]=-direction
        r[indices[b]*3:indices[b]*3+3]=direction
        constraints.append(r)
mat=np.array(constraints)
rank=int(np.linalg.matrix_rank(mat,tol=1e-7))
free_dof=3*len(nodes)-rank
# Six global motions plus one jounce degree of freedom per independent wheel.
assert free_dof==10,{'free_dof':free_dof,'expected':10}
report={'status':'DAE round-trip and linear suspension constraint checks passed',
        'dae_sha256':hashlib.sha256((OUT/(ID+'.dae')).read_bytes()).hexdigest(),
        'mesh_count':len(objs),'vertices':len(world_points),
        'model_extents_xyz_m':[round(float(v),4) for v in extents],
        'structure_nodes':len(nodes),'constraint_rank':rank,
        'free_dof_without_springs':free_dof,
        'limitations':'Linear constraints do not prove numerical stability, collision behavior, or correct driving in BeamNG.'}
(ROOT/'model-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
