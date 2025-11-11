import bpy
import os
import sys
import json
import math
import argparse
from pathlib import Path
from math import radians
from mathutils import Vector, Euler


# --------------------------- CLI --------------------------- #

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Render web kitchen bundles.")
    parser.add_argument("--mode", choices=["preview", "batch"], default="preview")
    parser.add_argument("--out", default="//web_kitchen_bundles")
    parser.add_argument("--webp_q", type=int, default=90)
    parser.add_argument(
        "--model",
        default=None,
        help="Optional override for kitchen model path (defaults to models/kitchen.glb).",
    )
    parser.add_argument(
        "--carcass_color",
        default="#4C4E52",
        help="Hex color for carcass surfaces when no texture is provided.",
    )
    parser.add_argument(
        "--samples_preview",
        type=int,
        default=128,
        help="Cycles samples to use in preview mode.",
    )
    parser.add_argument(
        "--samples_batch",
        type=int,
        default=512,
        help="Cycles samples to use in batch mode.",
    )
    return parser.parse_args(argv)


ARGS = parse_args()


# --------------------------- Paths ------------------------- #

BASE_DIR = Path(os.environ.get("KITCHEN_ASSET_ROOT", "/workspace")).resolve()
MAT_DIR = BASE_DIR / "materials"
MODEL_DIR = BASE_DIR / "models"
MANIFEST_PATH = MAT_DIR / "manifest.json"


def normalize_rel(path_str: str) -> Path:
    if not path_str:
        raise ValueError("Empty path supplied.")
    cleaned = path_str.lstrip("/")
    return (BASE_DIR / cleaned).resolve()


DEFAULT_MODEL = MODEL_DIR / "kitchen.glb"
MODEL_PATH = Path(ARGS.model).resolve() if ARGS.model else DEFAULT_MODEL


if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Kitchen model not found at {MODEL_PATH}")

if not MANIFEST_PATH.exists():
    raise FileNotFoundError(f"Material manifest missing at {MANIFEST_PATH}")


with MANIFEST_PATH.open() as mf:
    MAT_MANIFEST = json.load(mf)


def resolve_material_entries(section: str):
    resolved = {}
    for name, data in MAT_MANIFEST.get(section, {}).items():
        token = data["token"]
        jpg = normalize_rel(data["jpg"])
        if not jpg.exists():
            raise FileNotFoundError(f"Texture for {name} not found at {jpg}")
        resolved[token] = {
            "name": name,
            "path": str(jpg),
            "hex": data.get("hex"),
            "multiplier": data.get("multiplier", 1.0),
            "repeatUV": data.get("repeatUV"),
        }
    return resolved


DOOR_LIB = resolve_material_entries("doors")
TOP_LIB = resolve_material_entries("tops")


# ----------------------- Scene Utilities ------------------- #


def mm(val):
    return val * 0.001


def clear_objects():
    bpy.ops.object.select_all(action="SELECT")
    if bpy.ops.object.delete.poll():
        bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(collection)
        except RuntimeError:
            pass


def import_model(filepath: Path):
    ext = filepath.suffix.lower()
    if ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(filepath))
    elif ext == ".obj":
        bpy.ops.import_scene.obj(filepath=str(filepath))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(filepath))
    elif ext == ".3ds":
        bpy.ops.import_scene.autodesk_3ds(filepath=str(filepath))
    else:
        raise ValueError(f"Unsupported model format: {ext}")


def ensure_model_loaded():
    clear_objects()
    import_model(MODEL_PATH)


def scene_bbox(objs):
    xs, ys, zs = [], [], []
    for obj in objs:
        if obj.type != "MESH" or not obj.visible_get():
            continue
        for corner in obj.bound_box:
            wp = obj.matrix_world @ Vector(corner)
            xs.append(wp.x)
            ys.append(wp.y)
            zs.append(wp.z)
    if not xs:
        return None
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def center_and_size():
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.visible_get()]
    bb = scene_bbox(meshes)
    if bb is None:
        raise RuntimeError("Unable to compute bounding box; no visible mesh objects found.")
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = bb
    size = Vector((xmax - xmin, ymax - ymin, zmax - zmin))
    center = Vector(((xmax + xmin) / 2, (ymax + ymin) / 2, (zmax + zmin) / 2))
    return center, size, bb


def add_bevel(obj, width=mm(1.0)):
    bev = obj.modifiers.get("AA_Bevel") or obj.modifiers.new("AA_Bevel", "BEVEL")
    bev.width = width
    bev.segments = 3
    bev.limit_method = "ANGLE"
    bev.angle_limit = radians(30.0)
    bev.profile = 0.70
    wn = obj.modifiers.get("AA_WeightedNormals") or obj.modifiers.new("AA_WeightedNormals", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    obj.data.use_auto_smooth = True


def assign_material(obj, material):
    if obj.type != "MESH":
        return
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


# ----------------------- Material Builders ----------------- #


def ensure_image_node(mat, texture_path, colorspace="sRGB", use_box=False, box_blend=0.2, uv_scale=None):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(texture_path, check_existing=True)
    tex.interpolation = "Smart"
    tex.extension = "REPEAT"
    if tex.image:
        tex.image.colorspace_settings.name = colorspace
    if use_box:
        tex.projection = "BOX"
        tex.projection_blend = box_blend
        tex_coord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (
            uv_scale[0] if uv_scale else 1.0,
            uv_scale[1] if uv_scale else 1.0,
            uv_scale[0] if uv_scale else 1.0,
        )
        links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    return tex


def build_fenix_material(token, entry):
    name = f"FENIX_{entry['name']}"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")

    tex = ensure_image_node(mat, entry["path"], colorspace="sRGB", use_box=False)

    principled.inputs["Specular IOR Level"].default_value = 0.45
    principled.inputs["Roughness"].default_value = 0.92
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Sheen Tint"].default_value = (0.1, 0.1, 0.1, 1.0)
    principled.inputs["IOR"].default_value = 1.45

    if "Hamilton-Steel" in entry["name"]:
        # FENIX NTA metallic
        principled.inputs["Metallic"].default_value = 0.75
        principled.inputs["Roughness"].default_value = 0.32
        principled.inputs["Anisotropic"].default_value = 0.65

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 140.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.035

    links.new(tex.outputs["Color"], principled.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    return mat


def build_stone_material(token, entry):
    name = f"TOP_{entry['name']}"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")

    polished = "Marble" in entry["name"]
    base_roughness = 0.08 if polished else 0.35
    bump_strength = 0.05 if polished else 0.12

    tex = ensure_image_node(
        mat,
        entry["path"],
        colorspace="sRGB",
        use_box=True,
        box_blend=0.20,
        uv_scale=entry.get("repeatUV"),
    )

    rgb_to_bw = nodes.new("ShaderNodeRGBToBW")
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength

    micro_noise = nodes.new("ShaderNodeTexNoise")
    micro_noise.inputs["Scale"].default_value = 6.0
    micro_noise.inputs["Roughness"].default_value = 0.55

    color_mix = nodes.new("ShaderNodeMixRGB")
    color_mix.blend_type = "MULTIPLY"
    color_mix.inputs["Fac"].default_value = 0.18
    links.new(micro_noise.outputs["Color"], color_mix.inputs["Color2"])
    links.new(tex.outputs["Color"], color_mix.inputs["Color1"])

    principled.inputs["Specular IOR Level"].default_value = 0.52
    principled.inputs["Roughness"].default_value = base_roughness
    principled.inputs["Sheen Tint"].default_value = (0.05, 0.05, 0.05, 1.0)
    principled.inputs["IOR"].default_value = 1.50

    links.new(color_mix.outputs["Color"], principled.inputs["Base Color"])
    links.new(tex.outputs["Color"], rgb_to_bw.inputs["Color"])
    links.new(rgb_to_bw.outputs["Val"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    return mat


def build_carcass_material(hex_color: str):
    name = "CARCASS_Base"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")

    color = tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Specular IOR Level"].default_value = 0.35
    principled.inputs["Roughness"].default_value = 0.65
    principled.inputs["IOR"].default_value = 1.45

    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return mat


MAT_DOORS = {token: build_fenix_material(token, entry) for token, entry in DOOR_LIB.items()}
MAT_TOPS = {token: build_stone_material(token, entry) for token, entry in TOP_LIB.items()}
MAT_CARCASS = {"$CARC": build_carcass_material(ARGS.carcass_color)}


# ----------------------- Object Detection ------------------ #


def detect_sets():
    doors, carcass, tops, splashes = [], [], [], []

    def from_collection(name):
        collection = bpy.data.collections.get(name)
        if not collection:
            return []
        return [obj for obj in collection.objects if obj.type == "MESH"]

    doors = from_collection("DOORS")
    carcass = from_collection("CARCASSES")
    tops = from_collection("COUNTERTOPS")
    splashes = from_collection("BACKSPLASH")

    if doors and carcass and tops:
        return list(set(doors)), list(set(carcass)), list(set(tops)), list(set(splashes))

    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.visible_get()]
    for obj in meshes:
        bb = scene_bbox([obj])
        if bb is None:
            continue
        (xmin, xmax), (ymin, ymax), (zmin, zmax) = bb
        dims = Vector((xmax - xmin, ymax - ymin, zmax - zmin))
        thickness = min(dims.x, dims.y, dims.z)
        if mm(10) <= thickness <= mm(40) and dims.z > mm(300) and zmax > mm(800):
            doors.append(obj)
            continue
        if thickness < mm(80) and mm(850) <= zmax <= mm(1050):
            tops.append(obj)
            continue
        if thickness < mm(80) and dims.z > mm(400) and zmax > mm(1100):
            splashes.append(obj)
            continue
        carcass.append(obj)

    return list(set(doors)), list(set(carcass)), list(set(tops)), list(set(splashes))


ensure_model_loaded()
DOOR_SET, CARCASS_SET, TOP_SET, SPLASH_SET = detect_sets()

for obj in DOOR_SET + TOP_SET + SPLASH_SET:
    add_bevel(obj, width=mm(1.1))
for obj in CARCASS_SET:
    add_bevel(obj, width=mm(0.8))


# ----------------------- Lighting Setup -------------------- #


def reset_lights():
    bpy.ops.object.select_all(action="DESELECT")
    lights = [o for o in bpy.data.objects if o.type == "LIGHT"]
    for obj in lights:
        obj.select_set(True)
    if lights and bpy.ops.object.delete.poll():
        bpy.ops.object.delete()

    def make_area(name, size_x, size_y, energy, location, rotation_deg):
        data = bpy.data.lights.new(name, "AREA")
        data.shape = "RECTANGLE"
        data.size = size_x
        data.size_y = size_y
        data.energy = energy
        light_obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light_obj)
        light_obj.location = Vector(location)
        light_obj.rotation_euler = Euler(tuple(radians(v) for v in rotation_deg), "XYZ")
        light_obj.select_set(False)
        return light_obj

    make_area("KEY", 6.0, 1.6, 2800, (0.0, -2.6, 2.4), (58.0, 0.0, 0.0))
    make_area("FILL", 4.8, 1.0, 1400, (2.4, 2.0, 2.2), (100.0, 0.0, -150.0))
    make_area("KICKER", 4.0, 0.4, 950, (-3.2, 1.6, 1.8), (105.0, 0.0, 32.0))


reset_lights()


# ----------------------- Camera Rig ------------------------ #


def clear_cameras():
    bpy.ops.object.select_all(action="DESELECT")
    cams = [o for o in bpy.data.objects if o.type == "CAMERA"]
    for obj in cams:
        obj.select_set(True)
    if cams and bpy.ops.object.delete.poll():
        bpy.ops.object.delete()


def ensure_camera(name, location, rotation_deg, lens=35.0, ortho=False, ortho_scale=5.0, fstop=8.0):
    cam = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, cam)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(location)
    obj.rotation_euler = Euler(tuple(radians(v) for v in rotation_deg), "XYZ")

    if ortho:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    else:
        cam.type = "PERSP"
        cam.lens = lens
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = fstop
    obj.select_set(False)

    return obj


def build_cameras():
    clear_cameras()
    center, size, bb = center_and_size()
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = bb
    width, depth, height = size.x, size.y, size.z
    eye = mm(1450)
    margin = max(width, depth) * 0.18

    d_front = (width / 2 + margin) / math.tan(math.radians(54.4 / 2))
    cam_wide = ensure_camera(
        "KITCHEN_WIDE",
        (center.x, ymin - d_front, eye),
        (0.0, 0.0, 0.0),
        lens=35.0,
        fstop=8.0,
    )

    cam_depth = ensure_camera(
        "KITCHEN_DEPTH",
        (center.x - (width * 0.35), ymin - (depth * 0.55) - margin * 0.4, eye + mm(100)),
        (-5.0, 0.0, 32.0),
        lens=35.0,
        fstop=8.0,
    )

    cam_layout = ensure_camera(
        "KITCHEN_LAYOUT",
        (center.x, center.y, zmax + mm(4800)),
        (90.0, 0.0, 0.0),
        ortho=True,
        ortho_scale=max(width, depth) * 1.2,
    )

    cam_aerial = ensure_camera(
        "KITCHEN_AERIAL",
        (center.x - (width * 0.32), center.y - (depth * 0.65), zmax + mm(1700)),
        (32.0, 0.0, 42.0),
        lens=35.0,
        fstop=8.0,
    )

    cam_island = ensure_camera(
        "KITCHEN_ISLAND",
        (center.x + (width * 0.28), ymin - (depth * 0.25), mm(1100)),
        (-6.0, 0.0, -14.0),
        lens=50.0,
        fstop=5.6,
    )

    return [cam_wide, cam_depth, cam_layout, cam_aerial, cam_island]


# ----------------------- Variant Handling ------------------ #


def apply_variant(door_token, top_token, carcass_token="$CARC"):
    door_mat = MAT_DOORS[door_token]
    top_mat = MAT_TOPS[top_token]
    carc_mat = MAT_CARCASS[carcass_token]

    for obj in DOOR_SET:
        assign_material(obj, door_mat)
    for obj in CARCASS_SET:
        assign_material(obj, carc_mat)
    for obj in TOP_SET + SPLASH_SET:
        assign_material(obj, top_mat)


def set_cycles_baseline():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.max_bounces = 8
    scene.cycles.use_preview_denoising = False
    scene.cycles.use_denoising = False
    scene.cycles.samples = (
        ARGS.samples_batch if ARGS.mode == "batch" else ARGS.samples_preview
    )

    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = max(50, min(100, ARGS.webp_q))
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_motion_blur = False
    scene.render.film_transparent = False

    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        scene.view_settings.view_transform = "Filmic"
        scene.view_settings.look = "Medium Contrast"
    scene.view_settings.exposure = 0.0

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Strength"].default_value = 1.0


def set_resolution():
    scene = bpy.context.scene
    if ARGS.mode == "batch":
        scene.render.resolution_x = 3840
        scene.render.resolution_y = 2160
    else:
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_views(combo_id: str, output_dir: Path):
    set_resolution()
    cameras = build_cameras()
    files = []
    scene = bpy.context.scene
    for cam in cameras:
        scene.camera = cam
        render_path = output_dir / f"{cam.name}.webp"
        scene.render.filepath = str(render_path)
        bpy.ops.render.render(write_still=True)
        files.append({"view": cam.name, "rel": os.path.relpath(render_path, OUT_ROOT)})
    return files


# ----------------------- Manifest -------------------------- #


DOOR_KEYS = sorted(MAT_DOORS.keys())
TOP_KEYS = sorted(MAT_TOPS.keys())

COMBOS = [
    {"door": d, "top": t, "carcass": "$CARC", "id": f"{d[1:]}_{t[1:]}"}
    for d in DOOR_KEYS
    for t in TOP_KEYS
]


def build_manifest():
    return {
        "version": "1.0",
        "views": [
            "KITCHEN_WIDE",
            "KITCHEN_DEPTH",
            "KITCHEN_LAYOUT",
            "KITCHEN_AERIAL",
            "KITCHEN_ISLAND",
        ],
        "options": {
            "doors": [
                {"id": token, "name": DOOR_LIB[token]["name"], "path": DOOR_LIB[token]["path"]}
                for token in DOOR_KEYS
            ],
            "countertops": [
                {"id": token, "name": TOP_LIB[token]["name"], "path": TOP_LIB[token]["path"]}
                for token in TOP_KEYS
            ],
            "carcass": [
                {"id": "$CARC", "name": "Slate Carcass", "color": ARGS.carcass_color}
            ],
        },
        "bundles": [],
    }


# ----------------------- Execution ------------------------- #


set_cycles_baseline()

OUT_ROOT = Path(bpy.path.abspath(ARGS.out)).resolve()
ensure_dir(OUT_ROOT)

manifest = build_manifest()


def run_preview():
    combo = COMBOS[0]
    combo["id"] = f"PREVIEW_{combo['id']}"
    apply_variant(combo["door"], combo["top"], combo["carcass"])
    out_dir = ensure_dir(OUT_ROOT / combo["id"])
    files = render_views(combo["id"], out_dir)
    manifest["bundles"].append({"id": combo["id"], "files": files, "materials": combo})


def run_batch():
    for combo in COMBOS:
        apply_variant(combo["door"], combo["top"], combo["carcass"])
        out_dir = ensure_dir(OUT_ROOT / combo["id"])
        files = render_views(combo["id"], out_dir)
        manifest["bundles"].append({"id": combo["id"], "files": files, "materials": combo})


if ARGS.mode == "preview":
    run_preview()
else:
    run_batch()


manifest_path = OUT_ROOT / "web_kitchen_manifest.json"
with manifest_path.open("w") as f:
    json.dump(manifest, f, indent=2)

print("[OK] Output folder:", OUT_ROOT)
