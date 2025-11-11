import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from math import radians
from mathutils import Euler, Vector

# ------------- CLI -------------

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    p = argparse.ArgumentParser(description="Generate kitchen render bundles")
    p.add_argument("--mode", choices=["preview", "batch"], default="preview")
    p.add_argument("--out", default=None, help="Absolute path to output directory (defaults to PX-blender/web_kitchen_bundles_png)")
    p.add_argument("--format", choices=["WEBP", "JPEG", "PNG"], default="PNG", help="Image format for output renders")
    p.add_argument("--quality", type=int, default=90, help="Output image quality (0-100)")
    p.add_argument("--webp_q", type=int, help="Deprecated alias for --quality")
    p.add_argument("--samples", type=int, default=None, help="Override Cycles samples")
    p.add_argument("--door_repeat", type=float, default=1.0, help="UV repeat for door textures")
    p.add_argument("--top_repeat", type=float, default=0.5, help="Base UV repeat for stone box projection")
    p.add_argument("--validate-load", dest="validate_load", action="store_true", default=True, help="Validate rendered files by re-loading them")
    p.add_argument("--no-validate-load", dest="validate_load", action="store_false")
    p.add_argument("--min-bytes", type=int, default=4096, help="Minimum expected size for rendered files")
    p.add_argument("--max-retries", type=int, default=1, help="Number of times to retry a failed render validation")
    return p.parse_args(argv)


args = parse_args()

if getattr(args, "webp_q", None) is not None:
    args.quality = args.webp_q

# ------------- Paths -------------

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "web_kitchen_bundles_png"
out_candidate = Path(os.path.expanduser(args.out)) if args.out else DEFAULT_OUTPUT
OUT_ROOT = out_candidate.resolve()

MODEL_CANDIDATES = [
    ROOT / "models" / "kitchen.glb",
    ROOT / "models" / "kitchen.gltf",
    ROOT / "models" / "Kitchen.obj",
]

MATERIAL_MANIFEST = ROOT / "materials" / "manifest.json"

if not MATERIAL_MANIFEST.is_file():
    raise FileNotFoundError(f"Missing material manifest at {MATERIAL_MANIFEST}")

with MATERIAL_MANIFEST.open("r", encoding="utf-8") as fh:
    MATERIAL_DATA = json.load(fh)

DOOR_INFO = MATERIAL_DATA["doors"]
TOP_INFO = MATERIAL_DATA["tops"]

# Build helper dicts keyed by token
DOORS = {v["token"]: str((ROOT / v["jpg"].lstrip("/")).resolve()) for v in DOOR_INFO.values()}
TOPS = {v["token"]: str((ROOT / v["jpg"].lstrip("/")).resolve()) for v in TOP_INFO.values()}

if not all(os.path.exists(p) for p in DOORS.values()):
    missing = [p for p in DOORS.values() if not os.path.exists(p)]
    raise FileNotFoundError(f"Door swatches missing: {missing}")
if not all(os.path.exists(p) for p in TOPS.values()):
    missing = [p for p in TOPS.values() if not os.path.exists(p)]
    raise FileNotFoundError(f"Countertop swatches missing: {missing}")

CARCASS_COLOR = (0.15, 0.15, 0.15, 1.0)
MIN_RENDER_BYTES = max(1024, args.min_bytes)
VALIDATE_LOAD = args.validate_load
MAX_RENDER_RETRIES = max(0, args.max_retries)

# ------------- Filesystem helpers -------------

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_image(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Render output missing at {path}")
    file_size = path.stat().st_size
    if file_size < MIN_RENDER_BYTES:
        raise ValueError(f"Render too small ({file_size} bytes) at {path}")
    if VALIDATE_LOAD:
        try:
            temp_image = bpy.data.images.load(str(path), check_existing=False)
        except RuntimeError as exc:
            raise ValueError(f"Blender failed to load rendered file {path}: {exc}") from exc
        else:
            bpy.data.images.remove(temp_image)


# ------------- Scene reset & import -------------

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

model_path = None
for candidate in MODEL_CANDIDATES:
    if candidate.exists():
        model_path = candidate
        break

if not model_path:
    raise FileNotFoundError("No kitchen model found in models/ directory")

model_ext = model_path.suffix.lower()
if model_ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=str(model_path))
elif model_ext == ".obj":
    bpy.ops.import_scene.obj(filepath=str(model_path))
else:
    raise RuntimeError(f"Unsupported model extension for {model_path}")

imported_objects = [obj for obj in bpy.context.scene.objects]
SCALE_FACTOR = 0.001
for obj in imported_objects:
    obj.scale = (
        obj.scale.x * SCALE_FACTOR,
        obj.scale.y * SCALE_FACTOR,
        obj.scale.z * SCALE_FACTOR,
    )

bpy.context.view_layer.update()

# ------------- Scene baseline -------------

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = False
scene.cycles.use_preview_denoising = False
scene.cycles.adaptive_threshold = 0.006
scene.cycles.adaptive_min_samples = 6
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 3
scene.cycles.glossy_bounces = 4
scene.cycles.transmission_bounces = 4
scene.cycles.volume_bounces = 2

samples = args.samples if args.samples is not None else (512 if args.mode == "batch" else 128)
scene.cycles.samples = samples

scene.view_settings.view_transform = "AgX" if "AgX" in scene.view_settings.bl_rna.properties["view_transform"].enum_items.keys() else "Filmic"
scene.view_settings.look = "Medium Contrast"
scene.view_settings.exposure = 0.0

fmt = args.format.upper()
image_quality = max(0, min(100, args.quality))
scene.render.image_settings.file_format = fmt
scene.render.image_settings.quality = image_quality
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.use_file_extension = True

scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0

if scene.world is None:
    scene.world = bpy.data.worlds.new("World")

scene.world.use_nodes = True
world_nodes = scene.world.node_tree.nodes
world_links = scene.world.node_tree.links
background = world_nodes.get("Background")
if background is None:
    background = world_nodes.new("ShaderNodeBackground")
    world_output = world_nodes.get("World Output") or world_nodes.new("ShaderNodeOutputWorld")
    world_links.new(background.outputs["Background"], world_output.inputs["Surface"])

background.inputs["Color"].default_value = (0.95, 0.95, 0.95, 1.0)
background.inputs["Strength"].default_value = 1.0

OUT_ROOT.mkdir(parents=True, exist_ok=True)

# ------------- Geometry helpers -------------

def mesh_objects():
    return [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.visible_get()]


def object_metrics(obj):
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    xs = [v.x for v in bbox]
    ys = [v.y for v in bbox]
    zs = [v.z for v in bbox]
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs) - min(zs)
    zmin = min(zs)
    zmax = max(zs)
    area_xy = dx * dy
    return dx, dy, dz, zmin, zmax, area_xy


def classify_parts():
    doors, tops, splashes, carcasses = [], [], [], []
    for obj in mesh_objects():
        dx, dy, dz, zmin, zmax, area_xy = object_metrics(obj)
        dims_sorted = sorted([dx, dy, dz])
        thickness = dims_sorted[0]
        max_dim = dims_sorted[2]

        if area_xy < 1e-4:
            carcasses.append(obj)
            continue

        # Countertops (horizontal slabs near 0.9m)
        if 0.02 <= dz <= 0.09 and zmin >= 0.82 and area_xy > 0.08:
            tops.append(obj)
            continue

        # Backsplash panels (vertical, medium height)
        if thickness <= 0.04 and 0.25 <= dz <= 0.6 and zmax <= 1.5:
            splashes.append(obj)
            continue

        # Doors & tall panels (vertical with thin thickness)
        if thickness <= 0.04 and dz >= 0.6:
            doors.append(obj)
            continue

        carcasses.append(obj)

    return doors, carcasses, tops, splashes


DOOR_SET, CARC_SET, TOP_SET, SPLASH_SET = classify_parts()

if not DOOR_SET:
    raise RuntimeError("Door set detection failed; please ensure collections are named or adjust heuristics")
if not TOP_SET:
    raise RuntimeError("Countertop detection failed; adjust heuristics")
if not SPLASH_SET:
    print("[WARN] No backsplash meshes detected by heuristics; falling back to countertop meshes")
    SPLASH_SET = TOP_SET.copy()

# ------------- Shading helpers -------------


def ensure_image_node(
    mat,
    path,
    colorspace="sRGB",
    box_project=False,
    box_blend=0.2,
    repeat=args.door_repeat,
    use_uv=True,
):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.interpolation = 'Smart'
    tex.extension = 'REPEAT'
    if tex.image:
        tex.image.colorspace_settings.name = colorspace

    if box_project:
        tex.projection = 'BOX'
        tex.projection_blend = box_blend
        tex.extension = 'CLIP'
        tex.interpolation = 'Smart'
        texcoord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (repeat, repeat, repeat)
        links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    else:
        texcoord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (repeat, repeat, 1.0)
        source = "UV" if use_uv and "UV" in texcoord.outputs else "Generated"
        links.new(texcoord.outputs[source], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    return tex


def set_input_value(node, names, value):
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def build_fenix(name, img_path, rough=0.92, metallic=0.0, anisotropic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    set_input_value(bsdf, ["Roughness"], rough)
    set_input_value(bsdf, ["Specular", "Specular IOR Level"], 0.5)
    set_input_value(bsdf, ["Metallic"], metallic)
    set_input_value(bsdf, ["Anisotropic"], anisotropic)

    tex = ensure_image_node(mat, img_path, colorspace="sRGB", box_project=False, repeat=args.door_repeat)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 120.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.35
    nm = nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.02
    links.new(noise.outputs["Color"], nm.inputs["Color"])
    links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def build_stone(name, img_path, rough=0.3, polished=False):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    set_input_value(bsdf, ["Specular", "Specular IOR Level"], 0.5)
    set_input_value(bsdf, ["Roughness"], 0.1 if polished else rough)

    tex = ensure_image_node(mat, img_path, colorspace="sRGB", box_project=True, box_blend=0.15, repeat=args.top_repeat)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    to_gray = nodes.new("ShaderNodeRGBToBW")
    links.new(tex.outputs["Color"], to_gray.inputs["Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.04 if polished else 0.08
    links.new(to_gray.outputs["Val"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    sheen_noise = nodes.new("ShaderNodeTexNoise")
    sheen_noise.inputs["Scale"].default_value = 6.0
    sheen_noise.inputs["Detail"].default_value = 2.0
    if "Sheen Tint" in bsdf.inputs:
        links.new(sheen_noise.outputs["Fac"], bsdf.inputs["Sheen Tint"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def build_carcass(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    set_input_value(bsdf, ["Base Color"], color)
    set_input_value(bsdf, ["Roughness"], 0.65)
    set_input_value(bsdf, ["Specular", "Specular IOR Level"], 0.4)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


MAT_DOORS = {
    token: build_fenix(
        name=f"Door_{token}",
        img_path=path,
        rough=0.93 if "Fenix" in info_name else 0.75,
        metallic=0.0 if "Hamilton" not in info_name else 0.6,
        anisotropic=0.0 if "Hamilton" not in info_name else 0.5,
    )
    for info_name, token in [(k, v["token"]) for k, v in DOOR_INFO.items()]
    for path in [DOORS[token]]
}

# Override Hamilton steel with brushed metal look
if "$DFHS" in MAT_DOORS:
    MAT_DOORS["$DFHS"].node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.75
    MAT_DOORS["$DFHS"].node_tree.nodes["Principled BSDF"].inputs["Anisotropic"].default_value = 0.65
    MAT_DOORS["$DFHS"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.32

MAT_TOPS = {}
for name, data in TOP_INFO.items():
    token = data["token"]
    polished = "Marble" in name
    rough = 0.28 if "Dekton" in name else 0.18
    if "Sirius" in name:
        rough = 0.35
    MAT_TOPS[token] = build_stone(f"Top_{token}", TOPS[token], rough=rough, polished=polished)

MAT_CARCASS = build_carcass("Carcass_Default", CARCASS_COLOR)


# ------------- Assignment helpers -------------

def assign_material(obj, material):
    if obj.type != "MESH":
        return
    data = obj.data
    if not data.materials:
        data.materials.append(material)
    else:
        for i in range(len(data.materials)):
            data.materials[i] = material


def add_edge_softening(obj, width=0.001):
    bevel = obj.modifiers.get("AutoBevel") or obj.modifiers.new("AutoBevel", "BEVEL")
    bevel.width = width
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = radians(30)
    bevel.profile = 0.7
    norm = obj.modifiers.get("WeightedNormal") or obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    obj.data.use_auto_smooth = True

for obj in DOOR_SET + TOP_SET + SPLASH_SET:
    add_edge_softening(obj, width=0.0012)
for obj in CARC_SET:
    add_edge_softening(obj, width=0.0008)


# ------------- Lighting rig -------------

def clear_lights():
    for obj in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(obj, do_unlink=True)


def create_area_light(name, location, rotation_deg, size_x, size_y, power):
    light = bpy.data.lights.new(name, type='AREA')
    light.shape = 'RECTANGLE'
    light.size = size_x
    light.size_y = size_y
    light.energy = power
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(location)
    obj.rotation_euler = Euler(tuple(radians(a) for a in rotation_deg), 'XYZ')
    return obj


def setup_lighting():
    clear_lights()
    center, size, _ = scene_bounds()
    diag = max(size.x, size.y, 1.0)

    key_dist = diag * 0.8
    fill_dist = diag * 0.9
    rim_dist = diag * 1.0

    create_area_light(
        "KEY",
        location=(center.x, center.y - key_dist, center.z + size.z * 0.6),
        rotation_deg=(60, 0, 0),
        size_x=diag * 0.8,
        size_y=diag * 0.25,
        power=2800,
    )
    create_area_light(
        "FILL",
        location=(center.x + diag * 0.4, center.y + fill_dist, center.z + size.z * 0.7),
        rotation_deg=(105, 0, -160),
        size_x=diag * 0.55,
        size_y=diag * 0.18,
        power=1200,
    )
    create_area_light(
        "RIM",
        location=(center.x - diag * 0.6, center.y + rim_dist * 0.6, center.z + size.z * 0.5),
        rotation_deg=(110, 0, 30),
        size_x=diag * 0.5,
        size_y=diag * 0.1,
        power=900,
    )


# ------------- Bounds & cameras -------------

def scene_bounds():
    meshes = mesh_objects()
    if not meshes:
        raise RuntimeError("Scene bounds calculation failed; no meshes present")
    xs, ys, zs = [], [], []
    for obj in meshes:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            xs.append(world.x)
            ys.append(world.y)
            zs.append(world.z)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    center = Vector(((xmax + xmin) / 2, (ymax + ymin) / 2, (zmax + zmin) / 2))
    size = Vector((xmax - xmin, ymax - ymin, zmax - zmin))
    return center, size, ((xmin, xmax), (ymin, ymax), (zmin, zmax))


def clear_cameras():
    for obj in [o for o in bpy.data.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(obj, do_unlink=True)


def ensure_camera(name, location, rotation_deg, lens=35.0, ortho=False, ortho_scale=8.0, fstop=8.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = 'PERSP'
    obj = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(location)
    obj.rotation_euler = Euler(tuple(radians(a) for a in rotation_deg), 'XYZ')
    if ortho:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = ortho_scale
    else:
        cam_data.lens = lens
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = fstop
        cam_data.dof.focus_distance = max(0.1, (obj.location - scene_bounds()[0]).length)
    return obj


def build_cameras():
    clear_cameras()
    center, size, bounds = scene_bounds()
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = bounds
    width, depth, height = size.x, size.y, size.z
    diag_base = max(width, depth, 1.0)
    margin = max(diag_base * 0.18, 0.12)

    wide_dist = (width/2 + margin) / math.tan(math.radians(54.4/2))
    cam1 = ensure_camera(
        "KITCHEN_WIDE",
        location=(center.x, ymin - wide_dist, zmin + 1.45),
        rotation_deg=(0, 0, 0),
        lens=35.0,
        ortho=False,
        fstop=8.0,
    )

    cam2 = ensure_camera(
        "KITCHEN_DEPTH",
        location=(center.x - width * 0.35, ymin - depth * 0.55 - margin * 0.2, zmin + 1.55),
        rotation_deg=(-6, 0, 32),
        lens=35.0,
        fstop=8.0,
    )

    cam3 = ensure_camera(
        "KITCHEN_LAYOUT",
        location=(center.x, center.y, zmax + 5.0),
        rotation_deg=(90, 0, 0),
        ortho=True,
        ortho_scale=max(width, depth) * 1.15,
    )

    cam4 = ensure_camera(
        "KITCHEN_AERIAL",
        location=(center.x - width * 0.32, center.y - depth * 0.65, zmax + 1.8),
        rotation_deg=(32, 0, 45),
        lens=35.0,
        fstop=8.0,
    )

    cam5 = ensure_camera(
        "KITCHEN_ISLAND",
        location=(center.x + width * 0.25, ymin - depth * 0.25, zmin + 1.05),
        rotation_deg=(-5, 0, -15),
        lens=50.0,
        fstop=5.6,
    )

    return [cam1, cam2, cam3, cam4, cam5]


# ------------- Variants & rendering -------------

def apply_variant(door_token, top_token):
    door_mat = MAT_DOORS[door_token]
    top_mat = MAT_TOPS[top_token]

    for obj in DOOR_SET:
        assign_material(obj, door_mat)
    for obj in TOP_SET:
        assign_material(obj, top_mat)
    for obj in SPLASH_SET:
        assign_material(obj, top_mat)
    for obj in CARC_SET:
        assign_material(obj, MAT_CARCASS)


def set_resolution(mode):
    if mode == "batch":
        scene.render.resolution_x = 3840
        scene.render.resolution_y = 2160
    else:
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100


def render_views(combo_id, out_dir: Path):
    cameras = build_cameras()
    setup_lighting()
    files = []
    ext_map = {"WEBP": "webp", "JPEG": "jpg", "PNG": "png"}
    ext = ext_map.get(fmt, "png")
    ensure_dir(out_dir)
    for cam in cameras:
        target_path = out_dir / f"{cam.name}.{ext}"
        for attempt in range(MAX_RENDER_RETRIES + 1):
            scene.camera = cam
            scene.render.filepath = str(target_path)
            bpy.ops.render.render(write_still=True)
            try:
                validate_image(target_path)
            except Exception as exc:
                if attempt >= MAX_RENDER_RETRIES:
                    raise RuntimeError(f"Validation failed for {target_path}: {exc}") from exc
                print(f"[WARN] Validation failed for {target_path}: {exc}; retrying...")
                try:
                    target_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            break
        rel = target_path.relative_to(OUT_ROOT).as_posix()
        files.append({"view": cam.name, "rel": rel})
    return files


# ------------- Manifest structure -------------

def door_entries():
    entries = []
    for name, info in DOOR_INFO.items():
        entries.append({
            "id": info["token"],
            "name": name,
            "hex": info.get("hex"),
            "jpg": info.get("jpg"),
        })
    return entries


def top_entries():
    entries = []
    for name, info in TOP_INFO.items():
        entries.append({
            "id": info["token"],
            "name": name,
            "hex": info.get("hex"),
            "jpg": info.get("jpg"),
            "repeatUV": info.get("repeatUV"),
        })
    return entries


MANIFEST = {
    "version": "1.0",
    "format": fmt,
    "views": [
        "KITCHEN_WIDE",
        "KITCHEN_DEPTH",
        "KITCHEN_LAYOUT",
        "KITCHEN_AERIAL",
        "KITCHEN_ISLAND",
    ],
    "options": {
        "doors": door_entries(),
        "countertops": top_entries(),
        "backsplash_rule": "countertop",
    },
    "bundles": [],
}

# ------------- Combo iteration -------------

DOOR_TOKENS = list(DOORS.keys())
TOP_TOKENS = list(TOPS.keys())
DOOR_TOKENS.sort()
TOP_TOKENS.sort()

COMBOS = [
    {
        "id": f"{door_token[1:]}_{top_token[1:]}",
        "door": door_token,
        "countertop": top_token,
        "backsplash": top_token,
    }
    for door_token in DOOR_TOKENS
    for top_token in TOP_TOKENS
]

set_resolution(args.mode)

if args.mode == "preview":
    preview_combo = COMBOS[0]
    combo_id = f"PREVIEW_{preview_combo['id']}"
    apply_variant(preview_combo["door"], preview_combo["countertop"])
    out_dir = OUT_ROOT / combo_id
    files = render_views(combo_id, out_dir)
    MANIFEST["bundles"].append({
        "id": combo_id,
        "materials": preview_combo,
        "files": files,
        "mode": "preview",
        "samples": samples,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    })
else:
    for combo in COMBOS:
        apply_variant(combo["door"], combo["countertop"])
        out_dir = OUT_ROOT / combo["id"]
        files = render_views(combo["id"], out_dir)
        MANIFEST["bundles"].append({
            "id": combo["id"],
            "materials": combo,
            "files": files,
            "samples": samples,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        })

manifest_path = OUT_ROOT / "web_kitchen_manifest.json"
with manifest_path.open("w", encoding="utf-8") as fh:
    json.dump(MANIFEST, fh, indent=2)

print("[OK] Output root:", OUT_ROOT)
print("[OK] Manifest:", manifest_path)
