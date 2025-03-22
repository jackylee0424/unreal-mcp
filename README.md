# Unreal Engine MCP Server for Claude Desktop

This repository contains a Model Context Protocol (MCP) Python server that allows Claude Desktop to interact with Unreal Engine 5.3 (via Remote Control API), creating and manipulating 3D objects based on text prompts. This integration enables Claude to build and modify 3D scenes in Unreal Engine through natural language, representing an early step toward text-to-game-generation technology. 

Current Features:
- use Claude Desktop text prompts to arrange assets in Unreal Engine Editor
- create static meshes for assembling primitive shapes
- look up Unreal project folder for assets

![image](https://github.com/user-attachments/assets/f7d3d1e7-2057-41c1-bf5b-06734829a8aa)

![image](https://github.com/user-attachments/assets/394c3590-b54e-4824-a763-9df62b3d4cc1)


## Quick Start

### 1. Requirements
  - Python 3.10+
  - Unreal Engine 5.3 with Remote Control API (plugin) enabled
  - Claude Desktop (Windows)

### 2. Installation
Clone the repository and install required packages:

```bash
git clone https://github.com/runeape-sats/unreal-mcp.git
cd unreal-mcp
pip install uv mcp requests
```

### 3. Configure Claude Desktop
Go to Claude Desktop → File → Settings → Developer → Edit Config `claude_desktop_config.json` and add the following, adjusting the path to your local repository:

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "command": "uv",
      "args": ["--directory", "\\path\\to\\unreal-mcp", "run", "unreal_mcp_server.py"],
      "env": {}
    }
  }
}
```

If you already have other MCP servers configured (like `blender-mcp`), you may need to disable them to ensure they don't conflict.

### 4. Launch Unreal Engine
Open Unreal Engine with your project and ensure the Remote Control API plugin is enabled.

### 5. Launch Claude Desktop
Restart Claude Desktop (i.e., need a clean exit without Claude's icon in the system tray) to load the new configuration. You can verify if it's connected by asking Claude to create objects in Unreal Engine.

## Project Structure

The server is organized into several modules:

- `unreal_mcp_server.py` - Main entry point that registers MCP tools
- `unreal_connection.py` - Handles communication with Unreal Engine
- `unreal_actors.py` - Functions for creating and manipulating actors
- `unreal_assets.py` - Functions for working with assets and level info
- `unreal_utils.py` - Utility functions and constants

## Features

### Basic Object Creation

Create primitive shapes with a variety of parameters:
- Cubes, Spheres, Cylinders, Planes, Cones
- Custom position, rotation, scale
- Custom colors and materials

Example prompt: "Create a red cube at position 100, 200, 50"

### Blueprint Actor Creation

Spawn actors from Blueprint classes:
- Buildings, props, characters, etc.
- Custom parameters like in Basic Object Creation

Example prompt: "Spawn a bench from the blueprint at /Game/CustomAsset/Blueprints/BP_Bench01"

### Scene Manipulation

Modify existing objects:
- Change position, rotation, scale
- Adjust colors and materials
- Toggle visibility

Example prompt: "Move the cube to position 0, 0, 100 and rotate it 45 degrees"

### Asset Discovery

Search for and list available assets:
- Filter by asset type (blueprints, meshes, materials)
- Search in specific paths
- Find assets matching certain terms

Example prompt: "List all bench static meshes in the project"

## Example Prompts

Here are some example prompts you can use with Claude:

```
Create a blue sphere at position 0, 100, 50 with scale 2, 2, 2

Create a scene with a red cube at 0,0,0, a green sphere at 100,0,0, and a blue cylinder at 0,100,0

List all blueprint assets in the /Game/CustomAsset folder

Get information about the current level

Create a cylinder and then change its color to yellow
```

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

### Logging

The server logs detailed information to the console. If you're having issues, check the logs for error messages and tracebacks.

## Development

To run the server in development mode:

```bash
pip install mcp[cli]
mcp dev unreal_mcp_server.py
```

## Contributing

Contributions are welcome! This is an integration between Claude and Unreal Engine, and there's much that can be improved:

- Better natural language processing for scene descriptions
- More complex object creation capabilities
- Supporting more Unreal Engine features
- Improved error handling and feedback

## License

[MIT License](LICENSE)
