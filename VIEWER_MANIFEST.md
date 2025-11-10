# Viewer Manifest Schema

## Overview

The `viewer_manifest.json` file provides a structured catalog of all kitchen renders for integration with web-based kitchen configurators.

## Schema Definition

### Root Object

```json
{
  "version": "string",           // Schema version (e.g., "1.0")
  "generated": "string",          // ISO timestamp of generation
  "total_bundles": number,        // Total number of kitchen configuration bundles
  "total_renders": number,        // Total number of individual renders
  "bundles": [Bundle],            // Array of bundle objects
  "door_styles": [string],        // List of available door styles
  "countertop_styles": [string],  // List of available countertop styles
  "camera_views": [string]        // List of camera view identifiers
}
```

### Bundle Object

```json
{
  "id": "string",                 // Unique bundle identifier (e.g., "shaker_granite_black")
  "door_style": "string",         // Human-readable door style name
  "countertop_style": "string",   // Human-readable countertop style name
  "views": [View]                 // Array of view objects for this bundle
}
```

### View Object

```json
{
  "view": "string",               // View identifier (KITCHEN_WIDE, KITCHEN_DEPTH, etc.)
  "filename": "string",           // WebP image filename
  "description": "string"         // Human-readable view description
}
```

## Example

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
        {
          "view": "KITCHEN_DEPTH",
          "filename": "shaker_granite_black_kitchen_depth.webp",
          "description": "Depth view showing perspective"
        },
        {
          "view": "KITCHEN_LAYOUT",
          "filename": "shaker_granite_black_kitchen_layout.webp",
          "description": "Top-down layout view"
        },
        {
          "view": "KITCHEN_AERIAL",
          "filename": "shaker_granite_black_kitchen_aerial.webp",
          "description": "Aerial 45-degree view"
        },
        {
          "view": "KITCHEN_ISLAND",
          "filename": "shaker_granite_black_kitchen_island.webp",
          "description": "Close-up of kitchen island"
        }
      ]
    }
  ],
  "door_styles": [
    "Shaker",
    "Modern Flat",
    "Raised Panel",
    "Glass Front"
  ],
  "countertop_styles": [
    "Black Granite",
    "White Marble",
    "Gray Quartz",
    "Butcher Block"
  ],
  "camera_views": [
    "KITCHEN_WIDE",
    "KITCHEN_DEPTH",
    "KITCHEN_LAYOUT",
    "KITCHEN_AERIAL",
    "KITCHEN_ISLAND"
  ]
}
```

## Usage in Web Applications

### React Example

```jsx
import React, { useState, useEffect } from 'react';

function KitchenConfigurator() {
  const [manifest, setManifest] = useState(null);
  const [selectedBundle, setSelectedBundle] = useState(null);
  const [currentView, setCurrentView] = useState('KITCHEN_WIDE');

  useEffect(() => {
    fetch('/renders/viewer_manifest.json')
      .then(res => res.json())
      .then(data => {
        setManifest(data);
        setSelectedBundle(data.bundles[0]);
      });
  }, []);

  if (!manifest || !selectedBundle) return <div>Loading...</div>;

  const currentViewData = selectedBundle.views.find(v => v.view === currentView);

  return (
    <div>
      <h1>Kitchen Configurator</h1>
      
      {/* Door Style Selector */}
      <select onChange={(e) => {
        const bundle = manifest.bundles.find(b => b.door_style === e.target.value);
        setSelectedBundle(bundle);
      }}>
        {manifest.door_styles.map(style => (
          <option key={style} value={style}>{style}</option>
        ))}
      </select>

      {/* Countertop Style Selector */}
      <select onChange={(e) => {
        const bundle = manifest.bundles.find(b => 
          b.door_style === selectedBundle.door_style &&
          b.countertop_style === e.target.value
        );
        setSelectedBundle(bundle);
      }}>
        {manifest.countertop_styles.map(style => (
          <option key={style} value={style}>{style}</option>
        ))}
      </select>

      {/* View Selector */}
      <div>
        {manifest.camera_views.map(view => (
          <button
            key={view}
            onClick={() => setCurrentView(view)}
            className={view === currentView ? 'active' : ''}
          >
            {view.replace('KITCHEN_', '')}
          </button>
        ))}
      </div>

      {/* Render Display */}
      <img
        src={`/renders/${currentViewData.filename}`}
        alt={currentViewData.description}
      />
      <p>{currentViewData.description}</p>
    </div>
  );
}
```

### Vue.js Example

```vue
<template>
  <div class="kitchen-configurator">
    <h1>Kitchen Configurator</h1>
    
    <select v-model="selectedDoorStyle">
      <option v-for="style in manifest.door_styles" :key="style" :value="style">
        {{ style }}
      </option>
    </select>

    <select v-model="selectedCountertopStyle">
      <option v-for="style in manifest.countertop_styles" :key="style" :value="style">
        {{ style }}
      </option>
    </select>

    <div class="view-buttons">
      <button
        v-for="view in manifest.camera_views"
        :key="view"
        @click="currentView = view"
        :class="{ active: view === currentView }"
      >
        {{ view.replace('KITCHEN_', '') }}
      </button>
    </div>

    <img :src="currentImageUrl" :alt="currentViewDescription" />
  </div>
</template>

<script>
export default {
  data() {
    return {
      manifest: null,
      selectedDoorStyle: null,
      selectedCountertopStyle: null,
      currentView: 'KITCHEN_WIDE'
    };
  },
  computed: {
    currentBundle() {
      return this.manifest?.bundles.find(b =>
        b.door_style === this.selectedDoorStyle &&
        b.countertop_style === this.selectedCountertopStyle
      );
    },
    currentViewData() {
      return this.currentBundle?.views.find(v => v.view === this.currentView);
    },
    currentImageUrl() {
      return `/renders/${this.currentViewData?.filename}`;
    },
    currentViewDescription() {
      return this.currentViewData?.description;
    }
  },
  async mounted() {
    const response = await fetch('/renders/viewer_manifest.json');
    this.manifest = await response.json();
    this.selectedDoorStyle = this.manifest.door_styles[0];
    this.selectedCountertopStyle = this.manifest.countertop_styles[0];
  }
};
</script>
```

### Vanilla JavaScript Example

```javascript
// Load and parse manifest
async function loadKitchenConfigurator() {
  const response = await fetch('/renders/viewer_manifest.json');
  const manifest = await response.json();

  let currentDoorStyle = manifest.door_styles[0];
  let currentCountertopStyle = manifest.countertop_styles[0];
  let currentView = 'KITCHEN_WIDE';

  // Populate door style dropdown
  const doorSelect = document.getElementById('door-style-select');
  manifest.door_styles.forEach(style => {
    const option = document.createElement('option');
    option.value = style;
    option.textContent = style;
    doorSelect.appendChild(option);
  });

  // Populate countertop style dropdown
  const counterSelect = document.getElementById('countertop-style-select');
  manifest.countertop_styles.forEach(style => {
    const option = document.createElement('option');
    option.value = style;
    option.textContent = style;
    counterSelect.appendChild(option);
  });

  // Create view buttons
  const viewContainer = document.getElementById('view-buttons');
  manifest.camera_views.forEach(view => {
    const button = document.createElement('button');
    button.textContent = view.replace('KITCHEN_', '');
    button.onclick = () => {
      currentView = view;
      updateDisplay();
    };
    viewContainer.appendChild(button);
  });

  // Update display function
  function updateDisplay() {
    const bundle = manifest.bundles.find(b =>
      b.door_style === currentDoorStyle &&
      b.countertop_style === currentCountertopStyle
    );

    if (bundle) {
      const viewData = bundle.views.find(v => v.view === currentView);
      if (viewData) {
        const img = document.getElementById('kitchen-image');
        img.src = `/renders/${viewData.filename}`;
        img.alt = viewData.description;
      }
    }
  }

  // Event listeners
  doorSelect.addEventListener('change', (e) => {
    currentDoorStyle = e.target.value;
    updateDisplay();
  });

  counterSelect.addEventListener('change', (e) => {
    currentCountertopStyle = e.target.value;
    updateDisplay();
  });

  // Initial display
  updateDisplay();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', loadKitchenConfigurator);
```

## API Integration

For backend integration, you can serve the manifest via REST API:

```python
# Flask example
from flask import Flask, jsonify, send_file
import json

app = Flask(__name__)

@app.route('/api/kitchen/manifest')
def get_manifest():
    with open('renders/viewer_manifest.json') as f:
        return jsonify(json.load(f))

@app.route('/api/kitchen/render/<filename>')
def get_render(filename):
    return send_file(f'renders/{filename}', mimetype='image/webp')

@app.route('/api/kitchen/bundles')
def get_bundles():
    with open('renders/viewer_manifest.json') as f:
        manifest = json.load(f)
        return jsonify(manifest['bundles'])
```

## Performance Optimization

### Image Loading

```javascript
// Preload all images for smoother transitions
function preloadImages(manifest) {
  manifest.bundles.forEach(bundle => {
    bundle.views.forEach(view => {
      const img = new Image();
      img.src = `/renders/${view.filename}`;
    });
  });
}
```

### Lazy Loading

```javascript
// Lazy load images as needed
function lazyLoadImage(filename) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = `/renders/${filename}`;
  });
}
```

## Notes

- All image filenames follow the pattern: `{door_id}_{countertop_id}_{view_id}.webp`
- Bundle IDs use snake_case: `{door_id}_{countertop_id}`
- Camera view names use UPPER_SNAKE_CASE: `KITCHEN_WIDE`, `KITCHEN_DEPTH`, etc.
- WebP format provides excellent compression while maintaining quality
- Manifest version can be used for backward compatibility in future updates
