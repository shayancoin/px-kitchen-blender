# px-kitchen-blender

Kitchen render generator using Blender-MCP to create photorealistic kitchen visualizations for a Web Kitchen Viewer/Configurator.

## Overview

This project generates **80 WebP photorealistic kitchen renders** organized into **16 bundles**:
- **4 Door Styles**: Shaker, Modern Flat, Raised Panel, Glass Front
- **4 Countertop & Backsplash Styles**: Black Granite, White Marble, Gray Quartz, Butcher Block
- **5 Camera Views per Bundle**: 
  - `KITCHEN_WIDE` - Wide angle view of entire kitchen
  - `KITCHEN_DEPTH` - Depth view showing perspective
  - `KITCHEN_LAYOUT` - Top-down layout view
  - `KITCHEN_AERIAL` - Aerial 45-degree view
  - `KITCHEN_ISLAND` - Close-up of kitchen island

The generator also creates a `viewer_manifest.json` file that catalogs all renders for easy integration with web-based kitchen configurators.

## Prerequisites

1. **Blender 3.0+** installed
2. **Python 3.10+**
3. **Blender-MCP** installed and configured
   - Follow the installation guide at: https://github.com/ahujasid/blender-mcp

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/shayancoin/px-kitchen-blender.git
   cd px-kitchen-blender
   ```

2. Install Blender-MCP addon in Blender:
   - Download `addon.py` from https://github.com/ahujasid/blender-mcp
   - In Blender: Edit > Preferences > Add-ons > Install
   - Enable "Interface: Blender MCP"

3. Start Blender-MCP server in Blender:
   - Open Blender
   - Press `N` to show sidebar in 3D View
   - Navigate to "BlenderMCP" tab
   - Click "Connect to Claude"

## Usage

### Basic Usage

Run the kitchen renderer with default settings:

```bash
python3 kitchen_renderer.py
```

This will:
1. Connect to Blender-MCP (localhost:9876)
2. Set up a kitchen scene in Blender
3. Generate 80 renders (16 bundles × 5 views)
4. Save renders to `./renders/` directory
5. Create `viewer_manifest.json`

### Advanced Configuration

Configure via environment variables:

```bash
# Custom Blender-MCP connection
export BLENDER_HOST=localhost
export BLENDER_PORT=9876

# Custom output directory
export OUTPUT_DIR=./my_renders

python3 kitchen_renderer.py
```

## Output Structure

```
renders/
├── shaker_granite_black_kitchen_wide.webp
├── shaker_granite_black_kitchen_depth.webp
├── shaker_granite_black_kitchen_layout.webp
├── shaker_granite_black_kitchen_aerial.webp
├── shaker_granite_black_kitchen_island.webp
├── shaker_marble_white_kitchen_wide.webp
├── ... (75 more renders)
└── viewer_manifest.json
```

## Viewer Manifest Format

The `viewer_manifest.json` file contains:

```json
{
  "version": "1.0",
  "generated": "2025-11-10 22:00:00",
  "total_bundles": 16,
  "total_renders": 80,
  "bundles": [
    {
      "id": "shaker_granite_black",
      "door_style": "Shaker",
      "countertop_style": "Black Granite",
      "views": [
        {
          "view": "KITCHEN_WIDE",
          "filename": "shaker_granite_black_kitchen_wide.webp",
          "description": "Wide angle view of entire kitchen"
        },
        ...
      ]
    },
    ...
  ],
  "door_styles": ["Shaker", "Modern Flat", "Raised Panel", "Glass Front"],
  "countertop_styles": ["Black Granite", "White Marble", "Gray Quartz", "Butcher Block"],
  "camera_views": ["KITCHEN_WIDE", "KITCHEN_DEPTH", "KITCHEN_LAYOUT", "KITCHEN_AERIAL", "KITCHEN_ISLAND"]
}
```

## Customization

### Adding More Door Styles

Edit the `DOOR_STYLES` list in `kitchen_renderer.py`:

```python
DOOR_STYLES = [
    {"id": "my_style", "name": "My Style", "color": (R, G, B, 1.0)},
    ...
]
```

### Adding More Countertop Styles

Edit the `COUNTERTOP_STYLES` list in `kitchen_renderer.py`:

```python
COUNTERTOP_STYLES = [
    {"id": "my_counter", "name": "My Counter", "color": (R, G, B, 1.0), "roughness": 0.3},
    ...
]
```

### Modifying Camera Views

Edit the `CAMERA_VIEWS` dictionary in `kitchen_renderer.py`:

```python
CAMERA_VIEWS = {
    "MY_VIEW": {
        "location": (x, y, z),
        "rotation": (rx, ry, rz),
        "description": "My custom view"
    },
    ...
}
```

## Troubleshooting

### Cannot Connect to Blender-MCP

**Error**: `Failed to connect to Blender-MCP`

**Solutions**:
1. Ensure Blender is running
2. Verify Blender-MCP addon is installed and enabled
3. Click "Connect to Claude" in Blender's BlenderMCP panel
4. Check firewall settings (port 9876)

### Render Quality Issues

To improve render quality, edit the scene setup in `kitchen_renderer.py`:

```python
bpy.context.scene.cycles.samples = 256  # Increase from 128
```

### Slow Rendering

Each render takes time due to Cycles rendering. To speed up:
- Reduce samples (lower quality)
- Use GPU rendering (configure in Blender preferences)
- Render in batches

## Performance

- **Estimated Time**: ~5-10 minutes per render (depends on hardware)
- **Total Time**: 6-13 hours for all 80 renders
- **Disk Space**: ~100-200 MB for all renders (WebP compressed)

## Integration with Web Viewer

The `viewer_manifest.json` can be used with any web-based kitchen configurator:

```javascript
// Example: Load manifest in JavaScript
fetch('renders/viewer_manifest.json')
  .then(response => response.json())
  .then(manifest => {
    // Display bundles in UI
    manifest.bundles.forEach(bundle => {
      console.log(`${bundle.door_style} + ${bundle.countertop_style}`);
      bundle.views.forEach(view => {
        console.log(`  ${view.view}: ${view.filename}`);
      });
    });
  });
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [Blender-MCP](https://github.com/ahujasid/blender-mcp) by Siddharth Ahuja
- [Blender](https://www.blender.org/) - Open source 3D creation suite