# Unreal Engine MCP Server for Claude Desktop

This repository contains a Model Context Protocol (MCP) Python server that allows Claude Desktop to interact with Unreal Engine 5.3 (via Remote Control API), creating and manipulating 3D objects based on text prompts. This is an early build with the help from Claude and inspired by the Blender MCP project at https://github.com/ahujasid/blender-mcp.

## Quick Start
### 1. Requirements
  - Python 3.10
  - Unreal Engine 5.3 with Remote Control API (plugin) enabled
  - Claude Desktop (Windows)

### 2. Git Clone & Install Required Packages
Clone the repo and pip install
```bash
pip install uv mcp requests
```

### 3. Configure Claude Desktop
Go to Claude Desktop -> File -> Settings -> Developer -> Edit Config `claude_desktop_config.json` and change the path to your local repo path
```
  {
    "mcpServers": {
      "unreal-mcp": {
        "command": "uv",
        "args": ["--directory", "C:\\code\\unreal-mcp", "run", "unreal_mcp_server.py"],
        "env": {}
      }
    }
  }
```
### 4. Launch Unreal Engine
Leave your UE project open

### 5. Launch Claude Desktop
Need to launch it clean. Claude Desktop may hide in the system tray. Quit Claude and re-launch.


## Features

### Basic Object Creation

The server supports creating these primitive objects:
- Cubes
- Spheres
- Cylinders
- Planes
- Cones

Example prompt: "Create a red cube at position 100, 200, 50"

### Composite Object Creation

The server can create more complex compositions:
- Towers (stacked cubes)
- Walls (grid of cubes)
- Stairs (ascending cubes)
- Table and chairs
- Houses (floor, walls, roof, door, window)

Example prompt: "Create a small house with blue walls"

### Scene Creation

Create entire scenes with multiple objects:
- "Create a scene with a house, three trees, and a mountain in the background"
- "Make a landscape with rolling hills, a lake, and a cottage"

### Object Manipulation

Modify existing objects in the scene:
- Change position, rotation, and scale
- Change materials and colors
- Toggle visibility

## Troubleshooting

### Connection Issues

- Make sure Unreal Engine is running before starting the MCP server
- Ensure the Remote Control API plugin is enabled in Unreal Engine
- Check if another process is using port 30010
- Verify your firewall is not blocking the connection

### Objects Not Appearing

- Check the output log in Unreal Engine for any errors
- Make sure objects are not being created too far from the origin (0,0,0)
- Try simplifying your requests to isolate issues

## Contributing

Contributions are welcome! This is an early integration between Claude and Unreal Engine, and there's much that can be improved:

- Better natural language processing for scene descriptions
- More complex object creation capabilities
- Supporting more Unreal Engine features
- Improved error handling and feedback

## License

[MIT License](LICENSE)
