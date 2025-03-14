# unreal_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context, Image
import requests
import json
import logging
import asyncio
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional, Union
import traceback
import re

# Import modeling functions
import unreal_modeling

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UnrealMCPServer")

@dataclass
class UnrealConnection:
    """Class to manage connection to Unreal Engine Remote Control API"""
    host: str = "127.0.0.1"
    port: int = 30010
    base_url: str = None
    
    def __post_init__(self):
        self.base_url = f"http://{self.host}:{self.port}/remote/object/call"
    
    def test_connection(self) -> bool:
        """Test connection to Unreal Engine Remote Control API"""
        try:
            # Get all level actors as a simple test
            payload = {
                "objectPath": "/Script/UnrealEd.Default__EditorActorSubsystem",
                "functionName": "GetAllLevelActors"
            }
            
            response = requests.put(self.base_url, json=payload, timeout=5)
            response.raise_for_status()
            
            logger.info(f"Successfully connected to Unreal Engine at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Unreal Engine: {str(e)}")
            return False
    
    def send_command(self, 
                     object_path: str, 
                     function_name: str, 
                     parameters: Dict[str, Any] = None, 
                     generate_transaction: bool = True) -> Dict[str, Any]:
        """Send a command to Unreal Engine and return the response"""
        
        payload = {
            "objectPath": object_path,
            "functionName": function_name,
            "parameters": parameters or {},
            "generateTransaction": generate_transaction
        }
        
        try:
            # Log the command being sent
            logger.info(f"Sending UE command: {function_name} with params: {parameters}")
            
            # Send the command
            response = requests.put(self.base_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Command successful: {function_name}")
            
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending command to Unreal Engine: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response details: {e.response.text}")
            raise Exception(f"Communication error with Unreal Engine: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    
    try:
        # Just log that we're starting up
        logger.info("UnrealMCP server starting up")
        
        # Try to connect to Unreal Engine on startup to verify it's available
        try:
            # This will initialize the global connection if needed
            unreal = get_unreal_connection()
            connected = unreal.test_connection()
            if connected:
                logger.info("Successfully connected to Unreal Engine on startup")
            else:
                logger.warning("Could not connect to Unreal Engine on startup")
                logger.warning("Make sure Unreal Engine is running with the Remote Control API enabled")
        except Exception as e:
            logger.warning(f"Could not connect to Unreal Engine on startup: {str(e)}")
            logger.warning("Make sure Unreal Engine is running with Remote Control API enabled before using Unreal resources or tools")
        
        # Return an empty context - we're using the global connection
        yield {}
    finally:
        # Clean up the global connection on shutdown
        global _unreal_connection
        if _unreal_connection:
            logger.info("Shutting down UnrealMCP server")
            _unreal_connection = None
        logger.info("UnrealMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "UnrealMCP",
    description="Unreal Engine integration through the Model Context Protocol",
    lifespan=server_lifespan
)

# Global connection for resources
_unreal_connection = None

def get_unreal_connection():
    """Get or create a persistent Unreal connection"""
    global _unreal_connection
    
    # If we have an existing connection, check if it's still valid
    if _unreal_connection is not None:
        try:
            _unreal_connection.test_connection()
            return _unreal_connection
        except Exception as e:
            # Connection is dead, create a new one
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            _unreal_connection = None
    
    # Create a new connection if needed
    if _unreal_connection is None:
        _unreal_connection = UnrealConnection()
        if not _unreal_connection.test_connection():
            logger.error("Failed to connect to Unreal Engine")
            _unreal_connection = None
            raise Exception("Could not connect to Unreal Engine. Make sure Unreal Engine is running with Remote Control API enabled.")
        logger.info("Created new persistent connection to Unreal Engine")
    
    return _unreal_connection

# Register the connection getter with the unreal_modeling module
unreal_modeling.register_connection_getter(get_unreal_connection)

@mcp.tool()
def get_level_info(ctx: Context) -> str:
    """Get information about the current Unreal Engine level"""
    try:
        unreal = get_unreal_connection()
        
        # Get all level actors
        actors_result = unreal.send_command(
            "/Script/UnrealEd.Default__EditorActorSubsystem",
            "GetAllLevelActors"
        )
        
        actors = actors_result.get("ReturnValue", [])
        
        # Get details for each actor
        actors_info = []
        
        for actor_path in actors:
            try:
                # Store basic info
                actor_info = {
                    "path": actor_path
                }
                
                # Try to get actor label (should be safe for most actors)
                try:
                    label_result = unreal.send_command(
                        actor_path,
                        "GetActorLabel"
                    )
                    actor_info["label"] = label_result.get("ReturnValue", "Unknown")
                except Exception as e:
                    logger.warning(f"Could not get label for actor {actor_path}: {str(e)}")
                    # Extract name from path as fallback
                    try:
                        actor_info["label"] = actor_path.split('.')[-1]
                    except:
                        actor_info["label"] = "Unknown"
                
                # Try to get actor location
                try:
                    location_result = unreal.send_command(
                        actor_path,
                        "GetActorLocation"
                    )
                    actor_info["location"] = location_result.get("ReturnValue", {})
                except Exception as e:
                    logger.warning(f"Could not get location for actor {actor_path}: {str(e)}")
                    actor_info["location"] = "Unknown"
                
                # Instead of GetClass which seems problematic, try to infer type from the path
                actor_type = "Unknown"
                if "StaticMeshActor" in actor_path:
                    actor_type = "StaticMeshActor"
                elif "Light" in actor_path:
                    actor_type = "Light"
                elif "PlayerStart" in actor_path:
                    actor_type = "PlayerStart"
                elif "SkyAtmosphere" in actor_path:
                    actor_type = "SkyAtmosphere"
                elif "SkyLight" in actor_path:
                    actor_type = "SkyLight"
                elif "Fog" in actor_path:
                    actor_type = "Fog"
                elif "VolumetricCloud" in actor_path:
                    actor_type = "VolumetricCloud"
                
                actor_info["type"] = actor_type
                
                actors_info.append(actor_info)
            except Exception as e:
                logger.warning(f"Error getting details for actor {actor_path}: {str(e)}")
                actors_info.append({"path": actor_path, "error": str(e)})
        
        # Get current level info without using GetCurrentLevelName
        # Try to extract it from an actor path if possible
        level_name = "Unknown"
        if actors and len(actors) > 0:
            try:
                # Extract level name from the first actor's path
                path_parts = actors[0].split(':')
                if len(path_parts) > 0:
                    map_part = path_parts[0]
                    level_name = map_part.split('.')[-1]
            except Exception as e:
                logger.warning(f"Error extracting level name: {str(e)}")
        
        # Compile level info
        level_info = {
            "level_name": level_name,
            "actor_count": len(actors),
            "actors": actors_info
        }
        
        return json.dumps(level_info, indent=2)
    except Exception as e:
        logger.error(f"Error getting level info from Unreal Engine: {str(e)}")
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
    - scale: x,y,z scale factors
    - color: r,g,b color values (0.0-1.0)
    """
    try:
        unreal = get_unreal_connection()
        
        # Parse kwargs string into a dictionary
        params = {}
        if isinstance(kwargs, dict):
            params = kwargs
        elif kwargs.strip().startswith('{') and kwargs.strip().endswith('}'):
            # It's a JSON string
            params = json.loads(kwargs)
        else:
            # It's a key=value space-separated string
            for part in kwargs.split():
                if '=' in part:
                    key, value = part.split('=', 1)
                    # Parse location, rotation, scale if they're comma-separated values
                    if ',' in value and key in ['location', 'rotation', 'scale', 'color']:
                        params[key] = [float(x) for x in value.split(',')]
                    elif value.lower() == 'true':
                        params[key] = True
                    elif value.lower() == 'false':
                        params[key] = False
                    elif value.isdigit():
                        params[key] = int(value)
                    elif value.replace('.', '', 1).isdigit():  # Check if it's a float
                        params[key] = float(value)
                    else:
                        params[key] = value
        
        logger.info(f"Parsed parameters: {params}")
        
        # Map mesh_type to Unreal Engine asset paths
        mesh_map = {
            "CUBE": "/Engine/BasicShapes/Cube.Cube",
            "SPHERE": "/Engine/BasicShapes/Sphere.Sphere",
            "CYLINDER": "/Engine/BasicShapes/Cylinder.Cylinder",
            "PLANE": "/Engine/BasicShapes/Plane.Plane",
            "CONE": "/Engine/BasicShapes/Cone.Cone"
        }
        
        # Get mesh type, default to CUBE
        mesh_type = params.get('mesh_type', 'CUBE').upper()
        if mesh_type not in mesh_map:
            return f"Error: Unsupported mesh type '{mesh_type}'. Supported types are: {', '.join(mesh_map.keys())}"
        
        # Get actor name, default to mesh type
        name = params.get('actor_label') or params.get('name') or f"My{mesh_type.capitalize()}"
        
        # Get location, rotation, scale
        location = params.get('location', [0, 0, 0])
        rotation = params.get('rotation', [0, 0, 0])
        scale = params.get('scale', [1, 1, 1])
        color = params.get('color')
        
        # Convert to Unreal Engine format
        location_param = {}
        if isinstance(location, list) and len(location) >= 3:
            location_param = {"X": location[0], "Y": location[1], "Z": location[2]}
        else:
            location_param = {"X": 0, "Y": 0, "Z": 0}
            
        rotation_param = {}
        if isinstance(rotation, list) and len(rotation) >= 3:
            rotation_param = {"Pitch": rotation[0], "Yaw": rotation[1], "Roll": rotation[2]}
        else:
            rotation_param = {"Pitch": 0, "Yaw": 0, "Roll": 0}
        
        # Use a more direct approach similar to cubetest.py
        try:
            # Spawn the actor
            spawn_payload = {
                "objectPath": "/Script/EditorScriptingUtilities.Default__EditorLevelLibrary",
                "functionName": "SpawnActorFromClass",
                "parameters": {
                    "ActorClass": "/Script/Engine.StaticMeshActor",
                    "Location": location_param,
                    "Rotation": rotation_param
                }
            }
            spawn_result = unreal.send_command(
                spawn_payload["objectPath"],
                spawn_payload["functionName"],
                spawn_payload["parameters"]
            )
            
            actor_path = spawn_result.get("ReturnValue", "")
            if not actor_path:
                return "Error: Failed to spawn actor"
            
            # Get the StaticMeshComponent
            component_result = unreal.send_command(
                actor_path,
                "GetComponentByClass",
                {"ComponentClass": "/Script/Engine.StaticMeshComponent"}
            )
            
            component_path = component_result.get("ReturnValue", "")
            if not component_path:
                return "Error: Failed to get StaticMeshComponent"
            
            # Set the mesh
            mesh_path = mesh_map[mesh_type]
            unreal.send_command(
                component_path,
                "SetStaticMesh",
                {"NewMesh": mesh_path}
            )
            
            # Set the scale
            scale_param = {}
            if isinstance(scale, list) and len(scale) >= 3:
                scale_param = {"X": scale[0], "Y": scale[1], "Z": scale[2]}
            else:
                scale_param = {"X": 1, "Y": 1, "Z": 1}
                
            unreal.send_command(
                actor_path,
                "SetActorScale3D",
                {"NewScale3D": scale_param}
            )
            
            # Set the name
            unreal.send_command(
                actor_path,
                "SetActorLabel",
                {"NewActorLabel": name}
            )
            
            # Set color if provided
            if color and isinstance(color, list) and len(color) >= 3:
                # Create a dynamic material instance
                try:
                    create_mat_result = unreal.send_command(
                        component_path,
                        "CreateDynamicMaterialInstance",
                        {"ElementIndex": 0, "SourceMaterial": "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"}
                    )
                    
                    material_path = create_mat_result.get("ReturnValue", "")
                    
                    if material_path:
                        # Set the color parameter
                        unreal.send_command(
                            material_path,
                            "SetVectorParameterValue",
                            {
                                "ParameterName": "Color",
                                "Value": {
                                    "R": color[0],
                                    "G": color[1],
                                    "B": color[2],
                                    "A": 1.0
                                }
                            }
                        )
                except Exception as e:
                    logger.warning(f"Could not set material color: {str(e)}")
            
            return f"Successfully created {mesh_type.lower()} actor: {name}"
            
        except Exception as e:
            logger.error(f"Error in direct cube creation: {str(e)}")
            return f"Error creating {mesh_type.lower()}: {str(e)}"
            
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
        # Now properly pass the kwargs parameter to the implementation
        return unreal_modeling.modify_actor(ctx, kwargs)
    except Exception as e:
        logger.error(f"Error in modify_actor: {str(e)}")
        return f"Error modifying actor: {str(e)}"

@mcp.tool()
def create_composite_mesh(ctx: Context, kwargs: str) -> str:
    """
    Create a composite mesh (multiple actors arranged in a specific way) in the Unreal Engine level.
    
    Parameters:
    - kwargs: String containing parameters as key=value pairs or JSON object
      Example: "shape=tower location=0,0,0 size=1,1,1 label=MyTower"
      
    Supported parameters:
    - shape/composition_type: Type of composition (TOWER, WALL, STAIRS, TABLE_CHAIR, HOUSE)
    - label/name: Optional base name for the actors
    - location: Optional base x,y,z location coordinates
    - size/scale: Optional base x,y,z scale factors
    - color: Optional r,g,b color values (0.0-1.0)
    """
    try:
        # Now properly pass the kwargs parameter to the implementation
        return unreal_modeling.create_composite_mesh(ctx, kwargs)
    except Exception as e:
        logger.error(f"Error in create_composite_mesh: {str(e)}")
        return f"Error creating composite mesh: {str(e)}"

@mcp.tool()
def get_actor_info(ctx: Context, actor_label: str) -> str:
    """
    Get detailed information about a specific actor in the Unreal Engine level.
    
    Parameters:
    - actor_label: The label/name of the actor to get information about
    """
    try:
        unreal = get_unreal_connection()
        
        # First, get all actors to find the one with the matching label
        actors_result = unreal.send_command(
            "/Script/UnrealEd.Default__EditorActorSubsystem",
            "GetAllLevelActors"
        )
        
        actors = actors_result.get("ReturnValue", [])
        actor_path = None
        
        # Find the actor with the matching label
        for path in actors:
            try:
                label_result = unreal.send_command(
                    path,
                    "GetActorLabel"
                )
                label = label_result.get("ReturnValue", "")
                
                if label == actor_label:
                    actor_path = path
                    break
            except Exception:
                # If GetActorLabel fails, try to check if the actor name in the path matches
                if actor_label in path:
                    actor_path = path
                    break
        
        if not actor_path:
            return f"Actor '{actor_label}' not found in the current level."
        
        # Get detailed information about the actor
        info = {
            "path": actor_path,
            "label": actor_label
        }
        
        # Try to get actor location
        try:
            location_result = unreal.send_command(
                actor_path,
                "GetActorLocation"
            )
            info["location"] = location_result.get("ReturnValue", {})
        except Exception as e:
            logger.warning(f"Could not get location for actor {actor_path}: {str(e)}")
            info["location"] = "Not available"
        
        # Try to get actor rotation
        try:
            rotation_result = unreal.send_command(
                actor_path,
                "GetActorRotation"
            )
            info["rotation"] = rotation_result.get("ReturnValue", {})
        except Exception as e:
            logger.warning(f"Could not get rotation for actor {actor_path}: {str(e)}")
            info["rotation"] = "Not available"
        
        # Try to get actor scale
        try:
            scale_result = unreal.send_command(
                actor_path,
                "SetActorScale3D"
            )
            info["scale"] = scale_result.get("ReturnValue", {})
        except Exception as e:
            logger.warning(f"Could not get scale for actor {actor_path}: {str(e)}")
            info["scale"] = "Not available"
        
        # Infer the type from the path instead of using GetClass
        actor_type = "Unknown"
        if "StaticMeshActor" in actor_path:
            actor_type = "StaticMeshActor"
            
            # If it's a StaticMeshActor, try to get mesh info
            try:
                # Get the static mesh component
                component_result = unreal.send_command(
                    actor_path,
                    "GetComponentByClass",
                    {"ComponentClass": "/Script/Engine.StaticMeshComponent"}
                )
                
                component_path = component_result.get("ReturnValue", "")
                
                if component_path:
                    # Try to get static mesh info
                    try:
                        mesh_result = unreal.send_command(
                            component_path,
                            "GetStaticMesh"
                        )
                        
                        mesh_path = mesh_result.get("ReturnValue", "")
                        info["static_mesh"] = mesh_path
                    except Exception:
                        info["static_mesh"] = "Not available"
                    
                    # Try to get material info
                    try:
                        material_result = unreal.send_command(
                            component_path,
                            "GetMaterial",
                            {"ElementIndex": 0}
                        )
                        
                        material_path = material_result.get("ReturnValue", "")
                        info["material"] = material_path
                    except Exception:
                        info["material"] = "Not available"
            except Exception as e:
                logger.warning(f"Could not get component info for actor {actor_path}: {str(e)}")
        
        elif "Light" in actor_path:
            actor_type = "Light"
        elif "PlayerStart" in actor_path:
            actor_type = "PlayerStart"
        elif "SkyAtmosphere" in actor_path:
            actor_type = "SkyAtmosphere"
        elif "SkyLight" in actor_path:
            actor_type = "SkyLight"
        elif "Fog" in actor_path:
            actor_type = "Fog"
        elif "VolumetricCloud" in actor_path:
            actor_type = "VolumetricCloud"
        
        info["type"] = actor_type
        
        return json.dumps(info, indent=2)
    except Exception as e:
        logger.error(f"Error getting actor info from Unreal Engine: {str(e)}")
        return f"Error getting actor info: {str(e)}"
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