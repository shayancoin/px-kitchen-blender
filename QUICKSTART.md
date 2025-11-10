# Quick Start Guide

Get up and running with px-kitchen-blender in 5 minutes.

## Step 1: Install Blender-MCP

### Install Blender-MCP Server

```bash
# Install uv package manager (if not already installed)
# macOS
brew install uv

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install Blender Addon

1. Download `addon.py` from https://github.com/ahujasid/blender-mcp
2. Open Blender
3. Edit → Preferences → Add-ons → Install
4. Select `addon.py`
5. Enable "Interface: Blender MCP"

## Step 2: Start Blender-MCP

1. Open Blender
2. Press `N` to show sidebar
3. Click "BlenderMCP" tab
4. Click "Connect to Claude"

You should see: "Server running on localhost:9876"

## Step 3: Clone and Run

```bash
# Clone repository
git clone https://github.com/shayancoin/px-kitchen-blender.git
cd px-kitchen-blender

# Run the generator
python3 kitchen_renderer.py
```

## What Happens Next?

The script will:

1. **Connect to Blender** (takes ~1 second)
   ```
   Connected to Blender-MCP at localhost:9876
   ```

2. **Set up kitchen scene** (takes ~5 seconds)
   ```
   Kitchen scene setup complete
   ```

3. **Generate 80 renders** (takes ~6-13 hours)
   ```
   [1/80] Rendering KITCHEN_WIDE... ✓
   [2/80] Rendering KITCHEN_DEPTH... ✓
   ...
   ```

4. **Create manifest** (takes ~1 second)
   ```
   Viewer manifest saved to: ./renders/viewer_manifest.json
   ```

## Expected Output

```
renders/
├── shaker_granite_black_kitchen_wide.webp
├── shaker_granite_black_kitchen_depth.webp
├── shaker_granite_black_kitchen_layout.webp
├── shaker_granite_black_kitchen_aerial.webp
├── shaker_granite_black_kitchen_island.webp
├── shaker_marble_white_kitchen_wide.webp
├── ... (74 more renders)
├── glass_front_butcher_block_kitchen_island.webp
└── viewer_manifest.json
```

## Common Issues

### "Failed to connect to Blender-MCP"

**Fix**: Make sure Blender is running and the MCP server is started
- Check Blender's BlenderMCP panel shows "Connected"
- Verify no firewall is blocking port 9876

### "No camera found"

**Fix**: The scene setup may have failed
- Restart Blender
- Run the script again

### Renders are too dark

**Fix**: Increase lighting in the scene
- Edit `kitchen_renderer.py`
- Find `sun.data.energy = 2.0`
- Change to `sun.data.energy = 3.0`

### Renders take too long

**Fix**: Reduce render quality
- Edit `kitchen_renderer.py`
- Find `bpy.context.scene.cycles.samples = 128`
- Change to `bpy.context.scene.cycles.samples = 64`

Or use GPU rendering:
- Blender → Edit → Preferences → System
- Set "Cycles Render Devices" to "CUDA" or "OptiX" (NVIDIA) or "HIP" (AMD)

## Next Steps

1. **Customize styles**: Edit `config.json` to add your own door and countertop styles
2. **Adjust cameras**: Modify camera positions in `config.json`
3. **Integrate with web**: Use `viewer_manifest.json` with your web configurator
4. **Optimize renders**: Tweak lighting, materials, and render settings

## Need Help?

- Check the [README.md](README.md) for detailed documentation
- Review [VIEWER_MANIFEST.md](VIEWER_MANIFEST.md) for web integration
- Open an issue on GitHub

## Performance Tips

### For Faster Rendering:
- Use GPU instead of CPU
- Lower sample count (trade quality for speed)
- Reduce resolution (e.g., 1280x720)

### For Better Quality:
- Increase samples to 256 or 512
- Add more lights to the scene
- Use higher resolution (e.g., 2560x1440)
- Enable denoising in Blender

### For Batch Processing:
Run the script overnight or on a dedicated render machine. The script is designed to run unattended.

## Estimated Times

| Hardware | Time per Render | Total Time (80 renders) |
|----------|----------------|------------------------|
| CPU (Intel i7) | 8-10 min | ~11-13 hours |
| GPU (RTX 3060) | 4-6 min | ~5-8 hours |
| GPU (RTX 4090) | 2-3 min | ~2.5-4 hours |

*Times are approximate and depend on scene complexity and render settings*
