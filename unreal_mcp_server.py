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

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    
    try:
        logger.info("UnrealMCP server starting up")
        
        # Try to connect to Unreal Engine on startup to verify it's available
        try:
            unreal = get_unreal_connection()
            if unreal.test_connection():
                logger.info("Successfully connected to Unreal Engine on startup")
            else:
                logger.warning("Could not connect to Unreal Engine on startup")
                logger.warning("Make sure Unreal Engine is running with the Remote Control API enabled")
        except Exception as e:
            logger.warning(f"Could not connect to Unreal Engine on startup: {str(e)}")
            logger.warning("Make sure Unreal Engine is running with Remote Control API enabled before using Unreal resources or tools")
        
        # Return an empty context
        yield {}
    finally:
        # Shutdown logging
        logger.info("UnrealMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "UnrealMCP",
    description="Unreal Engine integration through the Model Context Protocol",
    lifespan=server_lifespan
)

# Register all tools
@mcp.tool()
def delete_actor(ctx: Context, actor_label: str) -> str:
    """
    Delete a specific actor from the Unreal Engine level.
    
    Parameters:
    - actor_label: The label/name of the actor to delete
    """
    try:
        from unreal_actors import delete_actor as del_actor
        return del_actor(actor_label)
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
    try:
        from unreal_actors import spawn_actor_from_blueprint as spawn_bp
        return spawn_bp(kwargs)
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
    try:
        from unreal_actors import spawn_static_mesh_actor_from_mesh
        return spawn_static_mesh_actor_from_mesh(kwargs)
    except Exception as e:
        logger.error(f"Error in spawn_static_mesh: {str(e)}")
        return f"Error spawning static mesh actor: {str(e)}"

@mcp.tool()
def get_level_info(ctx: Context) -> str:
    """Get information about the current Unreal Engine level. Unreal Engine units are in centimeter."""
    try:
        from unreal_assets import get_level_info as get_level
        return get_level()
    except Exception as e:
        logger.error(f"Error in get_level_info: {str(e)}")
        return f"Error getting level info: {str(e)}"

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
    try:
        from unreal_actors import create_static_mesh_actor as create_mesh
        return create_mesh(kwargs)
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
    try:
        from unreal_actors import modify_actor as mod_actor
        return mod_actor(kwargs)
    except Exception as e:
        logger.error(f"Error in modify_actor: {str(e)}")
        return f"Error modifying actor: {str(e)}"

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

# If this module is run directly, start the server
if __name__ == "__main__":
    try:
        logger.info("Starting UnrealMCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running UnrealMCP server: {str(e)}")
        traceback.print_exc()
