#!/usr/bin/env python3
"""
Example script showing how to work with the viewer manifest.

This demonstrates loading and querying the generated kitchen renders.
"""

import json
from pathlib import Path


def load_manifest(manifest_path: str = "./renders/viewer_manifest.json"):
    """Load the viewer manifest JSON."""
    with open(manifest_path) as f:
        return json.load(f)


def list_all_bundles(manifest):
    """List all available kitchen bundles."""
    print("\n" + "=" * 60)
    print("AVAILABLE KITCHEN BUNDLES")
    print("=" * 60)
    
    for i, bundle in enumerate(manifest['bundles'], 1):
        print(f"\n{i}. {bundle['id']}")
        print(f"   Door: {bundle['door_style']}")
        print(f"   Countertop: {bundle['countertop_style']}")
        print(f"   Views: {len(bundle['views'])}")


def find_bundle(manifest, door_style: str, countertop_style: str):
    """Find a specific bundle by style names."""
    for bundle in manifest['bundles']:
        if (bundle['door_style'] == door_style and 
            bundle['countertop_style'] == countertop_style):
            return bundle
    return None


def get_view_for_bundle(bundle, view_name: str):
    """Get a specific view from a bundle."""
    for view in bundle['views']:
        if view['view'] == view_name:
            return view
    return None


def example_query_1(manifest):
    """Example: Find all bundles with a specific door style."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: All bundles with 'Shaker' doors")
    print("=" * 60)
    
    shaker_bundles = [b for b in manifest['bundles'] 
                      if b['door_style'] == 'Shaker']
    
    for bundle in shaker_bundles:
        print(f"\n- {bundle['countertop_style']}")
        for view in bundle['views']:
            print(f"  • {view['view']}: {view['filename']}")


def example_query_2(manifest):
    """Example: Get a specific render."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Get wide view of Modern Flat + Black Granite")
    print("=" * 60)
    
    bundle = find_bundle(manifest, "Modern Flat", "Black Granite")
    if bundle:
        view = get_view_for_bundle(bundle, "KITCHEN_WIDE")
        if view:
            print(f"\nBundle ID: {bundle['id']}")
            print(f"View: {view['view']}")
            print(f"File: {view['filename']}")
            print(f"Description: {view['description']}")
            print(f"\nFull path: ./renders/{view['filename']}")


def example_query_3(manifest):
    """Example: Generate an HTML gallery."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Generate HTML gallery")
    print("=" * 60)
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Kitchen Configurator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .bundle { margin: 30px 0; border: 1px solid #ccc; padding: 15px; }
        .bundle h2 { margin-top: 0; }
        .views { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
        .view img { width: 100%; height: auto; border: 1px solid #ddd; }
        .view p { margin: 5px 0; font-size: 12px; }
    </style>
</head>
<body>
    <h1>Kitchen Configuration Gallery</h1>
"""
    
    for bundle in manifest['bundles'][:2]:  # Show first 2 bundles as example
        html += f"""
    <div class="bundle">
        <h2>{bundle['door_style']} + {bundle['countertop_style']}</h2>
        <div class="views">
"""
        for view in bundle['views']:
            html += f"""
            <div class="view">
                <img src="{view['filename']}" alt="{view['description']}">
                <p><strong>{view['view']}</strong></p>
                <p>{view['description']}</p>
            </div>
"""
        html += """
        </div>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    # Save HTML
    html_path = Path("./renders/gallery_example.html")
    with open(html_path, 'w') as f:
        f.write(html)
    
    print(f"\nGenerated: {html_path}")
    print("Open this file in a browser to view the gallery")


def example_query_4(manifest):
    """Example: Export data for a mobile app."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Export simplified data for mobile app")
    print("=" * 60)
    
    mobile_data = {
        "styles": {
            "doors": manifest['door_styles'],
            "countertops": manifest['countertop_styles']
        },
        "thumbnails": []
    }
    
    # Use KITCHEN_WIDE as thumbnail for each bundle
    for bundle in manifest['bundles']:
        wide_view = get_view_for_bundle(bundle, "KITCHEN_WIDE")
        if wide_view:
            mobile_data["thumbnails"].append({
                "id": bundle['id'],
                "door": bundle['door_style'],
                "counter": bundle['countertop_style'],
                "thumbnail": wide_view['filename']
            })
    
    mobile_path = Path("./renders/mobile_data.json")
    with open(mobile_path, 'w') as f:
        json.dump(mobile_data, f, indent=2)
    
    print(f"\nGenerated: {mobile_path}")
    print("This file contains simplified data for mobile app integration")


def main():
    """Run all examples."""
    manifest_path = "./renders/viewer_manifest.json"
    
    # Check if manifest exists
    if not Path(manifest_path).exists():
        print(f"ERROR: Manifest not found at {manifest_path}")
        print("Please run kitchen_renderer.py first to generate the renders")
        return
    
    # Load manifest
    manifest = load_manifest(manifest_path)
    
    print("\n" + "=" * 60)
    print("KITCHEN RENDER MANIFEST EXAMPLES")
    print("=" * 60)
    print(f"\nManifest version: {manifest['version']}")
    print(f"Generated: {manifest['generated']}")
    print(f"Total bundles: {manifest['total_bundles']}")
    print(f"Total renders: {manifest['total_renders']}")
    
    # Run examples
    list_all_bundles(manifest)
    example_query_1(manifest)
    example_query_2(manifest)
    example_query_3(manifest)
    example_query_4(manifest)
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
