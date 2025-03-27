# unreal_mcp_server.py
# Main entry point for the Unreal Engine MCP server

import logging
import json
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any
import traceback

from mcp.server.fastmcp import FastMCP, Context

# Import our modules
from unreal_connection import get_unreal_connection

# Import the rest of the modules when needed to avoid circular references

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UnrealMCPServer")

# Global spatial context to track all actors
spatial_context: Dict[str, Dict[str, str]] = {}

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    global spatial_context
    try:
        logger.info("UnrealMCP server starting up")
        
        # Try to connect to Unreal Engine on startup
        try:
            unreal = get_unreal_connection()
            if unreal.test_connection():
                logger.info("Successfully connected to Unreal Engine on startup")
            else:
                logger.warning("Could not connect to Unreal Engine on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Unreal Engine on startup: {str(e)}")
        
        # Initialize spatial context (could load from Unreal if needed)
        spatial_context = {}
        yield {}
    finally:
        logger.info("UnrealMCP server shut down")
        spatial_context.clear()

# Create the MCP server with lifespan support
mcp = FastMCP(
    "UnrealMCP",
    description="Unreal Engine integration with spatial context tracking",
    lifespan=server_lifespan
)

# Tool to get the current spatial context
@mcp.tool()
def get_spatial_context(ctx: Context) -> str:
    """Return the current spatial context of all actors as a JSON string."""
    global spatial_context
    try:
        return json.dumps(spatial_context, indent=2)
    except Exception as e:
        logger.error(f"Error in get_spatial_context: {str(e)}")
        return f"Error retrieving spatial context: {str(e)}"

# Tool to reset the spatial context
@mcp.tool()
def reset_spatial_context(ctx: Context) -> str:
    """Reset the spatial context, clearing all tracked actors."""
    global spatial_context
    try:
        spatial_context.clear()
        return "Spatial context reset successfully."
    except Exception as e:
        logger.error(f"Error in reset_spatial_context: {str(e)}")
        return f"Error resetting spatial context: {str(e)}"

# Modified existing tools to update spatial context
@mcp.tool()
def delete_actor(ctx: Context, actor_label: str) -> str:
    """
    Delete a specific actor from the Unreal Engine level.
    
    Parameters:
    - actor_label: The label/name of the actor to delete
    """
    global spatial_context
    try:
        from unreal_actors import delete_actor as del_actor
        result = del_actor(actor_label)
        spatial_context.pop(actor_label, None)  # Remove from context
        return result
    except Exception as e:
        logger.error(f"Error in delete_actor: {str(e)}")
        return f"Error deleting actor: {str(e)}"

@mcp.tool()
def spawn_actor_from_blueprint(ctx: Context, kwargs: str) -> str:
    """
    Spawn a level actor based on an Unreal Blueprint class.
    
    Parameters:
    - kwargs: String containing parameters as key=value pairs or JSON object
      Example: "actor_class=/Game/AssetName/Blueprints/BP_House0.BP_House0_C location=100,100,0 name=MyHouse"
      
    Supported parameters:
    - actor_class: (required) Path to the blueprint class
    - actor_label/name: Name for the actor
    - location: x,y,z location coordinates
    - rotation: pitch,yaw,roll rotation in degrees
    - scale: x,y,z scale factors
    """
    global spatial_context
    try:
        from unreal_actors import spawn_actor_from_blueprint as spawn_bp
        result = spawn_bp(kwargs)
        # Parse kwargs to update spatial context
        params = dict(kv.split("=") for kv in kwargs.split() if "=" in kv)
        actor_label = params.get("actor_label", params.get("name", f"Actor_{len(spatial_context)}"))
        spatial_context[actor_label] = {
            "location": params.get("location", "0,0,0"),
            "rotation": params.get("rotation", "0,0,0"),
            "scale": params.get("scale", "1,1,1")
        }
        return result
    except Exception as e:
        logger.error(f"Error in spawn_actor_from_blueprint: {str(e)}")
        return f"Error spawning actor from blueprint: {str(e)}"

@mcp.tool()
def spawn_static_mesh(ctx: Context, kwargs: str) -> str:
    """
    Spawn a static mesh actor using an existing static mesh asset from the content browser.
    
    Parameters:
    - kwargs: String containing parameters as key=value pairs or JSON object
      Example: "static_mesh=/Game/AssetName/Meshes/Bench01 location=100,100,0 name=MyBench"
      
    Supported parameters:
    - static_mesh: (required) Path to the static mesh asset
    - actor_label/name: Name for the actor
    - location: x,y,z location coordinates
    - rotation: pitch,yaw,roll rotation in degrees
    - scale: x,y,z scale factors
    - material_override: Path to material to use
    - color: r,g,b color values (0.0-1.0)
    """
    global spatial_context
    try:
        from unreal_actors import spawn_static_mesh_actor_from_mesh
        result = spawn_static_mesh_actor_from_mesh(kwargs)
        params = dict(kv.split("=") for kv in kwargs.split() if "=" in kv)
        actor_label = params.get("actor_label", params.get("name", f"Mesh_{len(spatial_context)}"))
        spatial_context[actor_label] = {
            "location": params.get("location", "0,0,0"),
            "rotation": params.get("rotation", "0,0,0"),
            "scale": params.get("scale", "1,1,1")
        }
        return result
    except Exception as e:
        logger.error(f"Error in spawn_static_mesh: {str(e)}")
        return f"Error spawning static mesh actor: {str(e)}"

@mcp.tool()
def create_static_mesh_actor(ctx: Context, kwargs: str) -> str:
    """
    Create a new static mesh actor in the Unreal Engine level using a simpler approach.
    
    Parameters:
    - kwargs: String containing parameters as key=value pairs or JSON object
      Example: "actor_label=Cube mesh_type=CUBE location=0,0,0"
      
    Supported parameters:
    - actor_label/name: Name for the actor
    - mesh_type: One of CUBE, SPHERE, CYLINDER, PLANE, CONE
    - location: x,y,z location coordinates
    - rotation: pitch,yaw,roll rotation in degrees
    - scale: x,y,z scale factors. 1 means same scale (100%)
    - color: r,g,b color values (0.0-1.0)
    """
    global spatial_context
    try:
        from unreal_actors import create_static_mesh_actor as create_mesh
        result = create_mesh(kwargs)
        params = dict(kv.split("=") for kv in kwargs.split() if "=" in kv)
        actor_label = params.get("actor_label", params.get("name", f"Mesh_{len(spatial_context)}"))
        spatial_context[actor_label] = {
            "location": params.get("location", "0,0,0"),
            "rotation": params.get("rotation", "0,0,0"),
            "scale": params.get("scale", "1,1,1")
        }
        return result
    except Exception as e:
        logger.error(f"Error in create_static_mesh_actor: {str(e)}")
        return f"Error creating static mesh actor: {str(e)}"

@mcp.tool()
def modify_actor(ctx: Context, kwargs: str) -> str:
    """
    Modify an existing actor in the Unreal Engine level.
    
    Parameters:
    - kwargs: String containing parameters as key=value pairs or JSON object
      Example: "actor_label=Cube location=100,200,50 rotation=0,45,0"
      
    Supported parameters:
    - actor_label: Label/name of the actor to modify (required)
    - location: x,y,z location coordinates
    - rotation: pitch,yaw,roll rotation in degrees
    - scale: x,y,z scale factors
    - visible: true/false to set visibility
    - color: r,g,b color values (0.0-1.0)
    """
    global spatial_context
    try:
        from unreal_actors import modify_actor as mod_actor
        result = mod_actor(kwargs)
        params = dict(kv.split("=") for kv in kwargs.split() if "=" in kv)
        actor_label = params["actor_label"]
        if actor_label in spatial_context:
            spatial_context[actor_label].update({
                k: params[k] for k in ["location", "rotation", "scale"] if k in params
            })
        return result
    except Exception as e:
        logger.error(f"Error in modify_actor: {str(e)}")
        return f"Error modifying actor: {str(e)}"

@mcp.tool()
def get_level_info(ctx: Context) -> str:
    """Get information about the current Unreal Engine level and update spatial context."""
    global spatial_context
    try:
        from unreal_assets import get_level_info as get_level
        level_info = get_level()  # Get the level info from Unreal Engine
        
        # Assuming level_info is a JSON string or similar format with actor data
        # If it's not JSON, you'd need to adjust the parsing logic accordingly
        try:
            level_data = json.loads(level_info)  # Parse the level info if it's JSON
            if isinstance(level_data, dict) and "actors" in level_data:
                # Clear existing spatial context and update with new actor data
                spatial_context.clear()
                for actor in level_data["actors"]:
                    actor_label = actor.get("actor_label", actor.get("name", f"Actor_{len(spatial_context)}"))
                    spatial_context[actor_label] = {
                        "location": actor.get("location", "0,0,0"),
                        "rotation": actor.get("rotation", "0,0,0"),
                        "scale": actor.get("scale", "1,1,1")
                    }
        except json.JSONDecodeError:
            # If level_info isn't JSON or doesn't contain actor data, just return it as-is
            logger.info("Level info not in expected JSON format, spatial context unchanged")
        
        return level_info  # Return the original level info string
    except Exception as e:
        logger.error(f"Error in get_level_info: {str(e)}")
        return f"Error getting level info: {str(e)}"

@mcp.tool()
def list_available_assets(ctx: Context, kwargs: str) -> str:
    """
    List available assets of a specific type in the Unreal Engine project.
    
    Parameters:
    - kwargs: String containing parameters as key=value pairs or JSON object
      Example: "asset_type=StaticMesh search_path=/Game/AssetName search_term=House"
      
    Supported parameters:
    - asset_type: Type of assets to list (BlueprintClass, StaticMesh, Material, etc.)
    - search_path: Optional path to search for assets (default: /Game)
    - search_term: Optional term to filter results
    - max_results: Maximum number of results to return (default: 20)
    """
    try:
        from unreal_assets import get_available_assets
        return get_available_assets(kwargs)
    except Exception as e:
        logger.error(f"Error in list_available_assets: {str(e)}")
        return f"Error listing available assets: {str(e)}"

@mcp.tool()
def get_actor_info(ctx: Context, actor_label: str) -> str:
    """
    Get detailed information about a specific actor in the Unreal Engine level.
    
    Parameters:
    - actor_label: The label/name of the actor to get information about
    """
    try:
        from unreal_actors import get_actor_info as get_info
        return get_info(actor_label)
    except Exception as e:
        logger.error(f"Error in get_actor_info: {str(e)}")
        return f"Error getting actor info: {str(e)}"

@mcp.tool()
def search_assets_recursively(ctx: Context, base_path: str, asset_type: str = None, search_term: str = None, max_results: int = 50) -> str:
    """
    Search for assets recursively in all common subdirectories.
    
    Parameters:
    - base_path: The base path to search in (e.g., '/Game/KyotoAlley')
    - asset_type: Optional type of assets to filter by
    - search_term: Optional search term to filter results
    - max_results: Maximum number of results (default: 50)
    """
    try:
        from unreal_assets import search_assets_recursively as search_assets
        return search_assets(base_path, asset_type, search_term, max_results)
    except Exception as e:
        logger.error(f"Error in search_assets_recursively: {str(e)}")
        return f"Error searching assets recursively: {str(e)}"

if __name__ == "__main__":
    try:
        logger.info("Starting UnrealMCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running UnrealMCP server: {str(e)}")
        traceback.print_exc()