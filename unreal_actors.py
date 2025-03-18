# unreal_actors.py
# Core functions for actor creation and manipulation

import logging
from typing import Dict, Any, List, Optional
import json

from unreal_connection import get_unreal_connection
from unreal_utils import (
    parse_kwargs, format_transform_params, get_common_actor_name,
    validate_required_params, vector_to_ue_format, BASIC_SHAPES
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UnrealActors")

def spawn_actor_base(actor_class: str, params: Dict[str, Any]) -> Optional[str]:
    """
    Base function to spawn an actor from any class
    
    Args:
        actor_class: Path to the actor class
        params: Dictionary of parameters
        
    Returns:
        The actor path if successful, None otherwise
    """
    try:
        unreal = get_unreal_connection()
        
        # Format transform parameters
        transform = format_transform_params(params)
        
        # Actor name
        name = get_common_actor_name(params)
        
        # Create spawn parameters
        spawn_params = {
            "ActorClass": actor_class,
        }
        
        # Add location if provided
        if 'location' in transform:
            spawn_params["Location"] = transform['location']
            
        # Add rotation if provided
        if 'rotation' in transform:
            spawn_params["Rotation"] = transform['rotation']
        
        # Spawn the actor
        spawn_result = unreal.send_command(
            "/Script/EditorScriptingUtilities.Default__EditorLevelLibrary",
            "SpawnActorFromClass",
            spawn_params
        )
        
        actor_path = spawn_result.get("ReturnValue", "")
        
        if not actor_path:
            logger.error(f"Failed to spawn actor of class {actor_class}")
            return None
            
        # Set actor name
        unreal.send_command(
            actor_path,
            "SetActorLabel",
            {"NewActorLabel": name}
        )
        
        # Set scale if provided
        if 'scale' in transform:
            unreal.send_command(
                actor_path,
                "SetActorScale3D",
                {"NewScale3D": transform['scale']}
            )
            
        return actor_path
    except Exception as e:
        logger.error(f"Error in spawn_actor_base: {str(e)}")
        return None

def create_static_mesh_actor(kwargs_str) -> str:
    """
    Create a new static mesh actor with a basic shape or custom mesh
    
    Args:
        kwargs_str: String or dict with parameters
        
    Returns:
        Success or error message
    """
    try:
        unreal = get_unreal_connection()
        params = parse_kwargs(kwargs_str)
        
        # Determine mesh type/path
        mesh_type = params.get('mesh_type', 'CUBE').upper()
        mesh_path = params.get('static_mesh_asset_path') or params.get('static_mesh')
        
        # If no explicit mesh path, use basic shape
        if not mesh_path:
            if mesh_type in BASIC_SHAPES:
                mesh_path = BASIC_SHAPES[mesh_type]
            else:
                return f"Error: Unsupported mesh type '{mesh_type}'. Supported types are: {', '.join(BASIC_SHAPES.keys())}"
        
        # Get actor name
        name = get_common_actor_name(params, f"My{mesh_type.capitalize()}")
        
        # Spawn the actor
        actor_path = spawn_actor_base("/Script/Engine.StaticMeshActor", params)
        
        if not actor_path:
            return "Error: Failed to spawn static mesh actor"
        
        # Get the StaticMeshComponent
        component_path = unreal.get_component_by_class(
            actor_path,
            "/Script/Engine.StaticMeshComponent"
        )
        
        if not component_path:
            return "Error: Failed to get StaticMeshComponent"
        
        # Set the mesh
        unreal.send_command(
            component_path,
            "SetStaticMesh",
            {"NewMesh": mesh_path}
        )
        
        # Set material/color if provided
        material_override = params.get('material_override')
        color = params.get('color') or params.get('material_color')
        
        if material_override:
            unreal.send_command(
                component_path,
                "SetMaterial",
                {"ElementIndex": 0, "Material": material_override}
            )
        elif color and isinstance(color, list) and len(color) >= 3:
            # Create a dynamic material instance
            create_mat_result = unreal.send_command(
                component_path,
                "CreateDynamicMaterialInstance",
                {"ElementIndex": 0, "SourceMaterial": "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"}
            )
            
            material_path = create_mat_result.get("ReturnValue", "")
            
            if material_path:
                # Set the color parameter - with proper RGBA format
                color_param = {"R": color[0], "G": color[1], "B": color[2], "A": 1.0}
                if len(color) >= 4:
                    color_param["A"] = color[3]
                    
                unreal.send_command(
                    material_path,
                    "SetVectorParameterValue",
                    {
                        "ParameterName": "Color",
                        "Value": color_param
                    }
                )
        
        return f"Successfully created {name} actor at position {params.get('location', [0, 0, 0])}"
    except Exception as e:
        logger.error(f"Error in create_static_mesh_actor: {str(e)}")
        return f"Error creating static mesh actor: {str(e)}"

def spawn_actor_from_blueprint(kwargs_str) -> str:
    """
    Spawn an actor from a blueprint class
    
    Args:
        kwargs_str: String or dict with parameters
        
    Returns:
        Success or error message
    """
    try:
        params = parse_kwargs(kwargs_str)
        
        # Get actor class
        actor_class = params.get('actor_class') or params.get('class')
        
        # Validate required parameters
        valid, error_msg = validate_required_params(params, ['actor_class'])
        if not valid:
            return error_msg
            
        # Spawn the actor
        actor_path = spawn_actor_base(actor_class, params)
        
        if not actor_path:
            return f"Error: Failed to spawn actor from blueprint class: {actor_class}"
            
        name = get_common_actor_name(params, "BlueprintActor")
        
        return f"Successfully created actor '{name}' from blueprint class '{actor_class}'"
    except Exception as e:
        logger.error(f"Error in spawn_actor_from_blueprint: {str(e)}")
        return f"Error spawning actor from blueprint: {str(e)}"

def spawn_static_mesh_actor_from_mesh(kwargs_str) -> str:
    """
    Spawn a static mesh actor using an existing static mesh asset
    
    Args:
        kwargs_str: String or dict with parameters
        
    Returns:
        Success or error message
    """
    try:
        params = parse_kwargs(kwargs_str)
        
        # Get static mesh path
        static_mesh = params.get('static_mesh') or params.get('mesh')
        
        # Validate required parameters
        valid, error_msg = validate_required_params(params, ['static_mesh'])
        if not valid:
            return error_msg
            
        # Add the static mesh path to the parameters
        params['static_mesh_asset_path'] = static_mesh
        
        # Use the common static mesh creation function
        return create_static_mesh_actor(params)
    except Exception as e:
        logger.error(f"Error in spawn_static_mesh_actor_from_mesh: {str(e)}")
        return f"Error spawning static mesh actor: {str(e)}"

def modify_actor(kwargs_str) -> str:
    """
    Modify an existing actor in the level
    
    Args:
        kwargs_str: String or dict with parameters
        
    Returns:
        Success or error message
    """
    try:
        unreal = get_unreal_connection()
        params = parse_kwargs(kwargs_str)
        
        # Get actor label
        actor_label = params.get('actor_label')
        
        # Validate required parameters
        valid, error_msg = validate_required_params(params, ['actor_label'])
        if not valid:
            return error_msg
            
        # Find the actor
        actor_path = unreal.find_actor_by_label(actor_label)
        
        if not actor_path:
            return f"Actor '{actor_label}' not found in the current level."
        
        # Get transform parameters
        transform = format_transform_params(params)
        
        # Apply location if provided
        if 'location' in transform:
            unreal.send_command(
                actor_path,
                "SetActorLocation",
                {"NewLocation": transform['location']}
            )
        
        # Apply rotation if provided
        if 'rotation' in transform:
            unreal.send_command(
                actor_path,
                "SetActorRotation",
                {"NewRotation": transform['rotation']}
            )
        
        # Apply scale if provided
        if 'scale' in transform:
            unreal.send_command(
                actor_path,
                "SetActorScale3D",
                {"NewScale3D": transform['scale']}
            )
        
        # Set visibility if provided
        visible = params.get('visible')
        if visible is not None:
            unreal.send_command(
                actor_path,
                "SetActorHiddenInGame",
                {"bNewHidden": not visible}
            )
        
        # Set material color if provided
        color = params.get('color') or params.get('material_color')
        if color and isinstance(color, list) and len(color) >= 3:
            # Get the static mesh component if it exists
            component_path = unreal.get_component_by_class(
                actor_path,
                "/Script/Engine.StaticMeshComponent"
            )
            
            if component_path:
                # Create a dynamic material instance
                create_mat_result = unreal.send_command(
                    component_path,
                    "CreateDynamicMaterialInstance",
                    {"ElementIndex": 0, "SourceMaterial": "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"}
                )
                
                material_path = create_mat_result.get("ReturnValue", "")
                
                if material_path:
                    # Set the color parameter - with proper RGBA format
                    color_param = {"R": color[0], "G": color[1], "B": color[2], "A": 1.0}
                    if len(color) >= 4:
                        color_param["A"] = color[3]
                        
                    unreal.send_command(
                        material_path,
                        "SetVectorParameterValue",
                        {
                            "ParameterName": "Color",
                            "Value": color_param
                        }
                    )
        
        return f"Successfully modified actor: {actor_label}"
    except Exception as e:
        logger.error(f"Error in modify_actor: {str(e)}")
        return f"Error modifying actor: {str(e)}"

def get_actor_info(actor_label: str) -> str:
    """
    Get detailed information about an actor
    
    Args:
        actor_label: Label of the actor
        
    Returns:
        JSON string with actor information
    """
    try:
        unreal = get_unreal_connection()
        
        # Find the actor
        actor_path = unreal.find_actor_by_label(actor_label)
        
        if not actor_path:
            return f"Actor '{actor_label}' not found in the current level."
        
        # Get basic info
        info = {
            "path": actor_path,
            "label": actor_label
        }
        
        # Get location
        try:
            location_result = unreal.send_command(
                actor_path,
                "GetActorLocation"
            )
            info["location"] = location_result.get("ReturnValue", {})
        except Exception as e:
            logger.warning(f"Could not get location for actor {actor_path}: {str(e)}")
            info["location"] = "Not available"
        
        # Get rotation
        try:
            rotation_result = unreal.send_command(
                actor_path,
                "GetActorRotation"
            )
            info["rotation"] = rotation_result.get("ReturnValue", {})
        except Exception as e:
            logger.warning(f"Could not get rotation for actor {actor_path}: {str(e)}")
            info["rotation"] = "Not available"
        
        # Get scale
        try:
            scale_result = unreal.send_command(
                actor_path,
                "GetActorScale3D"
            )
            info["scale"] = scale_result.get("ReturnValue", {})
        except Exception as e:
            logger.warning(f"Could not get scale for actor {actor_path}: {str(e)}")
            info["scale"] = "Not available"
            
        # Get bounding box
        try:
            # GetActorBounds returns Origin and BoxExtent
            bounds_result = unreal.send_command(
                actor_path,
                "GetActorBounds",
                {"bOnlyCollidingComponents": False}
            )
            
            if bounds_result:
                origin = bounds_result.get("Origin", {})
                box_extent = bounds_result.get("BoxExtent", {})
                
                # Calculate min and max points of the bounding box
                min_point = {
                    "X": origin.get("X", 0) - box_extent.get("X", 0),
                    "Y": origin.get("Y", 0) - box_extent.get("Y", 0),
                    "Z": origin.get("Z", 0) - box_extent.get("Z", 0)
                }
                
                max_point = {
                    "X": origin.get("X", 0) + box_extent.get("X", 0),
                    "Y": origin.get("Y", 0) + box_extent.get("Y", 0),
                    "Z": origin.get("Z", 0) + box_extent.get("Z", 0)
                }
                
                info["bounding_box"] = {
                    "origin": origin,
                    "extent": box_extent,
                    "min": min_point,
                    "max": max_point,
                    "size": {
                        "X": box_extent.get("X", 0) * 2,
                        "Y": box_extent.get("Y", 0) * 2,
                        "Z": box_extent.get("Z", 0) * 2
                    }
                }
            else:
                info["bounding_box"] = "Not available"
        except Exception as e:
            logger.warning(f"Could not get bounding box for actor {actor_path}: {str(e)}")
            info["bounding_box"] = "Not available"
        
        # Determine actor type from path
        actor_type = "Unknown"
        if "StaticMeshActor" in actor_path:
            actor_type = "StaticMeshActor"
            
            # If it's a static mesh actor, get mesh and material info
            component_path = unreal.get_component_by_class(
                actor_path,
                "/Script/Engine.StaticMeshComponent"
            )
            
            if component_path:
                # Get static mesh path
                try:
                    mesh_result = unreal.send_command(
                        component_path,
                        "GetStaticMesh"
                    )
                    info["static_mesh"] = mesh_result.get("ReturnValue", "")
                except Exception:
                    info["static_mesh"] = "Not available"
                
                # Get material
                try:
                    material_result = unreal.send_command(
                        component_path,
                        "GetMaterial",
                        {"ElementIndex": 0}
                    )
                    info["material"] = material_result.get("ReturnValue", "")
                except Exception:
                    info["material"] = "Not available"
                    
                # Get component bounds for more accurate mesh bounds
                try:
                    comp_bounds_result = unreal.send_command(
                        component_path,
                        "GetBounds"
                    )
                    if comp_bounds_result:
                        bounds = comp_bounds_result.get("ReturnValue", {})
                        info["component_bounds"] = bounds
                except Exception as e:
                    logger.warning(f"Could not get component bounds for {component_path}: {str(e)}")
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
        logger.error(f"Error in get_actor_info: {str(e)}")
        return f"Error getting actor info: {str(e)}"