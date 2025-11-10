#!/usr/bin/env python3
"""
Kitchen Render Generator using Blender-MCP

Generates photorealistic kitchen renders with different configurations:
- 4 Door styles
- 4 Countertop & Backsplash combinations
- 5 Camera views per configuration
- Total: 16 bundles × 5 views = 80 WebP renders
"""

import json
import os
import socket
import time
from pathlib import Path
from typing import Dict, List, Any


class BlenderMCPClient:
    """Client for communicating with Blender-MCP server."""
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self) -> bool:
        """Connect to Blender-MCP server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to Blender-MCP at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to Blender-MCP: {e}")
            return False
    
    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Blender and receive response."""
        if not self.socket:
            raise RuntimeError("Not connected to Blender-MCP")
        
        command = {"type": command_type}
        if params:
            command["params"] = params
        
        # Send command
        message = json.dumps(command) + "\n"
        self.socket.sendall(message.encode('utf-8'))
        
        # Receive response
        response_data = b""
        while True:
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b"\n" in response_data:
                break
        
        response = json.loads(response_data.decode('utf-8').strip())
        return response
    
    def execute_python(self, code: str) -> Dict[str, Any]:
        """Execute Python code in Blender."""
        return self.send_command("execute", {"code": code})
    
    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
            self.socket = None


class KitchenRenderer:
    """Renders kitchen configurations using Blender-MCP."""
    
    # Define kitchen configurations
    DOOR_STYLES = [
        {"id": "shaker", "name": "Shaker", "color": (0.9, 0.9, 0.85, 1.0)},
        {"id": "modern_flat", "name": "Modern Flat", "color": (0.2, 0.2, 0.2, 1.0)},
        {"id": "raised_panel", "name": "Raised Panel", "color": (0.6, 0.4, 0.3, 1.0)},
        {"id": "glass_front", "name": "Glass Front", "color": (0.95, 0.95, 0.95, 1.0)}
    ]
    
    COUNTERTOP_STYLES = [
        {"id": "granite_black", "name": "Black Granite", "color": (0.1, 0.1, 0.1, 1.0), "roughness": 0.2},
        {"id": "marble_white", "name": "White Marble", "color": (0.95, 0.95, 0.95, 1.0), "roughness": 0.15},
        {"id": "quartz_gray", "name": "Gray Quartz", "color": (0.5, 0.5, 0.5, 1.0), "roughness": 0.25},
        {"id": "butcher_block", "name": "Butcher Block", "color": (0.7, 0.5, 0.3, 1.0), "roughness": 0.4}
    ]
    
    CAMERA_VIEWS = {
        "KITCHEN_WIDE": {
            "location": (-8, -8, 4),
            "rotation": (1.1, 0, -0.785),
            "description": "Wide angle view of entire kitchen"
        },
        "KITCHEN_DEPTH": {
            "location": (0, -10, 3),
            "rotation": (1.2, 0, 0),
            "description": "Depth view showing perspective"
        },
        "KITCHEN_LAYOUT": {
            "location": (0, 0, 12),
            "rotation": (0, 0, 0),
            "description": "Top-down layout view"
        },
        "KITCHEN_AERIAL": {
            "location": (-5, -5, 8),
            "rotation": (0.8, 0, -0.785),
            "description": "Aerial 45-degree view"
        },
        "KITCHEN_ISLAND": {
            "location": (3, -6, 2),
            "rotation": (1.3, 0, 0.5),
            "description": "Close-up of kitchen island"
        }
    }
    
    def __init__(self, client: BlenderMCPClient, output_dir: str = "./renders"):
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_scene(self):
        """Set up the basic kitchen scene in Blender."""
        setup_code = """
import bpy
import math

# Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Add lighting
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
sun = bpy.context.active_object
sun.data.energy = 2.0

# Add area lights for realistic kitchen lighting
bpy.ops.object.light_add(type='AREA', location=(0, 0, 4))
area_light = bpy.context.active_object
area_light.data.energy = 150
area_light.data.size = 3

# Set up render settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 128
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.image_settings.file_format = 'WEBP'
bpy.context.scene.render.image_settings.quality = 90

# Add camera
bpy.ops.object.camera_add(location=(0, -10, 5))
camera = bpy.context.active_object
bpy.context.scene.camera = camera

# Create floor
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Floor"

# Create basic kitchen layout
# Base cabinets
def create_cabinet(location, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    cabinet = bpy.context.active_object
    cabinet.name = name
    cabinet.scale = (0.6, 0.6, 0.9)
    return cabinet

# Create cabinet row
for i in range(5):
    create_cabinet((i * 1.3 - 2.6, -3, 0.45), f"Cabinet_Base_{i}")

# Upper cabinets
for i in range(5):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(i * 1.3 - 2.6, -3, 2.0))
    cabinet = bpy.context.active_object
    cabinet.name = f"Cabinet_Upper_{i}"
    cabinet.scale = (0.6, 0.4, 0.6)

# Countertop
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -3, 0.9))
countertop = bpy.context.active_object
countertop.name = "Countertop"
countertop.scale = (3.5, 0.65, 0.05)

# Backsplash
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -3.3, 1.3))
backsplash = bpy.context.active_object
backsplash.name = "Backsplash"
backsplash.scale = (3.5, 0.02, 0.35)

# Kitchen island
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.45))
island = bpy.context.active_object
island.name = "Island"
island.scale = (1.5, 1.0, 0.9)

# Island countertop
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.9))
island_counter = bpy.context.active_object
island_counter.name = "IslandCountertop"
island_counter.scale = (1.6, 1.1, 0.05)

print("Kitchen scene setup complete")
"""
        result = self.client.execute_python(setup_code)
        print(f"Scene setup: {result}")
        return result.get("status") == "success"
    
    def apply_door_style(self, door_style: Dict[str, Any]):
        """Apply door style to kitchen cabinets."""
        color = door_style["color"]
        apply_code = f"""
import bpy

# Apply material to all cabinets
for obj in bpy.data.objects:
    if "Cabinet" in obj.name:
        # Create or get material
        mat_name = "DoorMaterial"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
        
        # Set material properties
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = {color}
            bsdf.inputs['Roughness'].default_value = 0.3
            bsdf.inputs['Specular IOR Level'].default_value = 0.5
        
        # Apply material to object
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

print("Door style applied: {door_style['name']}")
"""
        result = self.client.execute_python(apply_code)
        return result.get("status") == "success"
    
    def apply_countertop_style(self, countertop_style: Dict[str, Any]):
        """Apply countertop and backsplash style."""
        color = countertop_style["color"]
        roughness = countertop_style["roughness"]
        apply_code = f"""
import bpy

# Apply material to countertops and backsplash
for obj in bpy.data.objects:
    if "Countertop" in obj.name or "Backsplash" in obj.name or "Island" in obj.name:
        # Create or get material
        mat_name = "CountertopMaterial"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
        
        # Set material properties
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = {color}
            bsdf.inputs['Roughness'].default_value = {roughness}
            bsdf.inputs['Specular IOR Level'].default_value = 0.8
            bsdf.inputs['Metallic'].default_value = 0.1
        
        # Apply material to object
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

print("Countertop style applied: {countertop_style['name']}")
"""
        result = self.client.execute_python(apply_code)
        return result.get("status") == "success"
    
    def set_camera_view(self, view_name: str, view_config: Dict[str, Any]):
        """Set camera position and rotation for a specific view."""
        location = view_config["location"]
        rotation = view_config["rotation"]
        
        camera_code = f"""
import bpy
import math

camera = bpy.context.scene.camera
if camera:
    camera.location = {location}
    camera.rotation_euler = {rotation}
    print("Camera set to {view_name}")
else:
    print("No camera found")
"""
        result = self.client.execute_python(camera_code)
        return result.get("status") == "success"
    
    def render_scene(self, output_path: str):
        """Render the current scene to a file."""
        render_code = f"""
import bpy

output_path = r"{output_path}"
bpy.context.scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)
print(f"Rendered to {{output_path}}")
"""
        result = self.client.execute_python(render_code)
        return result.get("status") == "success"
    
    def generate_all_renders(self) -> List[Dict[str, Any]]:
        """Generate all 80 renders for the kitchen configurations."""
        renders = []
        total_renders = len(self.DOOR_STYLES) * len(self.COUNTERTOP_STYLES) * len(self.CAMERA_VIEWS)
        current = 0
        
        print(f"\nGenerating {total_renders} renders...")
        print("=" * 60)
        
        # Set up the scene once
        if not self.setup_scene():
            print("Failed to set up scene")
            return renders
        
        # Generate renders for each combination
        for door_style in self.DOOR_STYLES:
            for countertop_style in self.COUNTERTOP_STYLES:
                bundle_id = f"{door_style['id']}_{countertop_style['id']}"
                
                print(f"\nBundle: {door_style['name']} + {countertop_style['name']}")
                print("-" * 60)
                
                # Apply styles
                self.apply_door_style(door_style)
                self.apply_countertop_style(countertop_style)
                
                # Render each view
                for view_name, view_config in self.CAMERA_VIEWS.items():
                    current += 1
                    print(f"[{current}/{total_renders}] Rendering {view_name}...", end=" ")
                    
                    # Set camera
                    self.set_camera_view(view_name, view_config)
                    
                    # Render
                    output_filename = f"{bundle_id}_{view_name.lower()}.webp"
                    output_path = self.output_dir / output_filename
                    
                    if self.render_scene(str(output_path)):
                        renders.append({
                            "bundle_id": bundle_id,
                            "door_style": door_style["name"],
                            "countertop_style": countertop_style["name"],
                            "view": view_name,
                            "filename": output_filename,
                            "path": str(output_path),
                            "description": view_config["description"]
                        })
                        print("✓")
                    else:
                        print("✗")
                    
                    # Small delay between renders
                    time.sleep(0.5)
        
        print("\n" + "=" * 60)
        print(f"Completed: {len(renders)}/{total_renders} renders")
        return renders
    
    def generate_viewer_manifest(self, renders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a viewer manifest JSON for the Web Kitchen Viewer."""
        # Group renders by bundle
        bundles = {}
        for render in renders:
            bundle_id = render["bundle_id"]
            if bundle_id not in bundles:
                bundles[bundle_id] = {
                    "id": bundle_id,
                    "door_style": render["door_style"],
                    "countertop_style": render["countertop_style"],
                    "views": []
                }
            bundles[bundle_id]["views"].append({
                "view": render["view"],
                "filename": render["filename"],
                "description": render["description"]
            })
        
        manifest = {
            "version": "1.0",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_bundles": len(bundles),
            "total_renders": len(renders),
            "bundles": list(bundles.values()),
            "door_styles": [style["name"] for style in self.DOOR_STYLES],
            "countertop_styles": [style["name"] for style in self.COUNTERTOP_STYLES],
            "camera_views": list(self.CAMERA_VIEWS.keys())
        }
        
        return manifest


def main():
    """Main execution function."""
    # Configuration
    BLENDER_HOST = os.getenv("BLENDER_HOST", "localhost")
    BLENDER_PORT = int(os.getenv("BLENDER_PORT", "9876"))
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./renders")
    
    print("Kitchen Render Generator")
    print("=" * 60)
    print(f"Blender-MCP: {BLENDER_HOST}:{BLENDER_PORT}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    # Connect to Blender-MCP
    client = BlenderMCPClient(host=BLENDER_HOST, port=BLENDER_PORT)
    if not client.connect():
        print("\nERROR: Could not connect to Blender-MCP")
        print("Please ensure:")
        print("1. Blender is running")
        print("2. Blender-MCP addon is installed and enabled")
        print("3. The MCP server is started in Blender")
        return 1
    
    try:
        # Create renderer
        renderer = KitchenRenderer(client, OUTPUT_DIR)
        
        # Generate all renders
        renders = renderer.generate_all_renders()
        
        if not renders:
            print("\nERROR: No renders were generated")
            return 1
        
        # Generate viewer manifest
        manifest = renderer.generate_viewer_manifest(renders)
        manifest_path = Path(OUTPUT_DIR) / "viewer_manifest.json"
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"\nViewer manifest saved to: {manifest_path}")
        print("\n" + "=" * 60)
        print("SUCCESS! All renders and manifest generated.")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        client.close()


if __name__ == "__main__":
    exit(main())
