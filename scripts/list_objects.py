import bpy, os
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

path = os.path.abspath('models/kitchen.glb')
print('Importing', path)
bpy.ops.import_scene.gltf(filepath=path)

scale_factor=0.001
for obj in bpy.data.objects:
    obj.scale = (obj.scale.x * scale_factor, obj.scale.y * scale_factor, obj.scale.z * scale_factor)

bpy.context.view_layer.update()

print('\nObject metrics:')
for obj in bpy.data.objects:
    if obj.type!='MESH':
        continue
    bbox=[obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    xs=[v.x for v in bbox]; ys=[v.y for v in bbox]; zs=[v.z for v in bbox]
    dims=(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    zmin=min(zs); zmax=max(zs);
    print(f"{obj.name:>10s} dims={tuple(round(d,4) for d in dims)} zmin={zmin:.4f} zmax={zmax:.4f}")

print('Done')
