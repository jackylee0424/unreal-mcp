# unreal_modeling.py
# Contains modeling-related functions for the Unreal MCP server

import logging
import json
from typing import Dict, Any, List, Optional, Union
from mcp.server.fastmcp import Context

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UnrealModeling")

# This will be imported from unreal_mcp_server.py
# Declared here to avoid circular imports
_get_unreal_connection = None

def register_connection_getter(getter_func):
    """Register the get_unreal_connection function from the main module"""
    global _get_unreal_connection
    _get_unreal_connection = getter_func
    logger.info("Connection getter registered successfully")

def get_unreal_connection():
    """Get the unreal connection using the registered getter function"""
    if _get_unreal_connection is None:
        raise Exception("Connection getter has not been registered")
    return _get_unreal_connection()

def parse_kwargs(kwargs_str):
    """Parse kwargs string into a dictionary"""
    if not kwargs_str:
        return {}
    
    # If it's already a dictionary, return it
    if isinstance(kwargs_str, dict):
        return kwargs_str
        
    # Check if it's a JSON string
    try:
        return json.loads(kwargs_str)
    except json.JSONDecodeError:
        pass
    
    # Otherwise parse as space-separated key=value pairs
    kwargs = {}
    parts = kwargs_str.split()
    
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            # Parse location, rotation, scale if they're comma-separated values
            if ',' in value and key in ['location', 'rotation', 'scale', 'material_color']:
                kwargs[key] = [float(x) for x in value.split(',')]
            elif value.lower() == 'true':
                kwargs[key] = True
            elif value.lower() == 'false':
                kwargs[key] = False
            elif value.isdigit():
                kwargs[key] = int(value)
            elif value.replace('.', '', 1).isdigit():  # Check if it's a float
                kwargs[key] = float(value)
            else:
                kwargs[key] = value
    
    return kwargs

def create_static_mesh_actor(ctx: Context, kwargs):
    """
    Create a new static mesh actor in the Unreal Engine level.
    
    Parameters passed through kwargs:
    - actor_label/name: Name for the actor 
    - static_mesh_asset_path: Path to the static mesh asset
    - location: [x, y, z] location coordinates
    - rotation: [pitch, yaw, roll] rotation in degrees
    - scale: [x, y, z] scale factors
    - material_override: Path to material to use
    - color: [r, g, b] color values (0.0-1.0)
    
    Alternatively:
    - mesh_type: One of CUBE, SPHERE, CYLINDER, PLANE, CONE
    """
    try:
        unreal = get_unreal_connection()
        
        # Parse kwargs string into a dictionary if it's a string
        params = parse_kwargs(kwargs)
        logger.info(f"Parsed parameters: {params}")
        
        # Map mesh_type to Unreal Engine asset paths if provided
        mesh_map = {
            "CUBE": "/Engine/BasicShapes/Cube.Cube",
            "SPHERE": "/Engine/BasicShapes/Sphere.Sphere",
            "CYLINDER": "/Engine/BasicShapes/Cylinder.Cylinder",
            "PLANE": "/Engine/BasicShapes/Plane.Plane",
            "CONE": "/Engine/BasicShapes/Cone.Cone"
        }
        
        # Get mesh path - either from direct path or mesh_type
        mesh_path = params.get('static_mesh_asset_path')
        mesh_type = params.get('mesh_type', '').upper()
        
        if not mesh_path and mesh_type in mesh_map:
            mesh_path = mesh_map[mesh_type]
        elif not mesh_path:
            # Default to cube if no mesh specified
            mesh_path = mesh_map["CUBE"]
        
        # Get actor name
        name = params.get('actor_label') or params.get('name') or "NewMesh"
        
        # Get location, rotation, scale
        location = params.get('location', [0, 0, 0])
        rotation = params.get('rotation', [0, 0, 0])
        scale = params.get('scale', [1, 1, 1])
        
        # Convert to Unreal Engine format
        if isinstance(location, list) and len(location) >= 3:
            location_param = {"X": location[0], "Y": location[1], "Z": location[2]}
        else:
            location_param = {"X": 0, "Y": 0, "Z": 0}
            
        if isinstance(rotation, list) and len(rotation) >= 3:
            rotation_param = {"Pitch": rotation[0], "Yaw": rotation[1], "Roll": rotation[2]}
        else:
            rotation_param = {"Pitch": 0, "Yaw": 0, "Roll": 0}
        
        # Step 1: Spawn the actor
        spawn_result = unreal.send_command(
            "/Script/EditorScriptingUtilities.Default__EditorLevelLibrary",
            "SpawnActorFromClass",
            {
                "ActorClass": "/Script/Engine.StaticMeshActor",
                "Location": location_param,
                "Rotation": rotation_param
            }
        )
        
        actor_path = spawn_result.get("ReturnValue", "")
        
        if not actor_path:
            return "Error: Failed to spawn actor"
        
        # Step 2: Get the StaticMeshComponent
        component_result = unreal.send_command(
            actor_path,
            "GetComponentByClass",
            {"ComponentClass": "/Script/Engine.StaticMeshComponent"}
        )
        
        component_path = component_result.get("ReturnValue", "")
        
        if not component_path:
            return "Error: Failed to get StaticMeshComponent"
        
        # Step 3: Set the StaticMesh
        unreal.send_command(
            component_path,
            "SetStaticMesh",
            {"NewMesh": mesh_path}
        )
        
        # Step 4: Set actor scale
        if isinstance(scale, list) and len(scale) >= 3:
            unreal.send_command(
                actor_path,
                "SetActorScale3D",
                {"NewScale3D": {"X": scale[0], "Y": scale[1], "Z": scale[2]}}
            )
        
        # Step 5: Set actor name/label
        unreal.send_command(
            actor_path,
            "SetActorLabel",
            {"NewActorLabel": name}
        )
        
        # Step 6: Set material if provided
        material_override = params.get('material_override')
        material_color = params.get('material_color') or params.get('color')
        
        if material_override:
            unreal.send_command(
                component_path,
                "SetMaterial",
                {"ElementIndex": 0, "Material": material_override}
            )
        elif material_color and isinstance(material_color, list) and len(material_color) >= 3:
            # Create a dynamic material instance
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
                            "R": material_color[0],
                            "G": material_color[1],
                            "B": material_color[2],
                            "A": 1.0
                        }
                    }
                )
        
        return f"Successfully created {name} actor at path {actor_path}"
    except Exception as e:
        logger.error(f"Error creating static mesh actor: {str(e)}")
        return f"Error creating static mesh actor: {str(e)}"

def modify_actor(ctx: Context, kwargs):
    
    """
    Modify an existing actor in the Unreal Engine level.
    
    Parameters passed through kwargs:
    - actor_label: Label/name of the actor to modify
    - location: [x, y, z] location coordinates
    - rotation: [pitch, yaw, roll] rotation in degrees
    - scale: [x, y, z] scale factors
    - visible: boolean to set visibility
    - material_color: [r, g, b] color values (0.0-1.0)
    """
    try:
        unreal = get_unreal_connection()
        
        # Parse kwargs string into a dictionary if it's a string
        params = parse_kwargs(kwargs)
        logger.info(f"Parsed parameters: {params}")
        
        # Get actor label
        actor_label = params.get('actor_label')
        if not actor_label:
            return "Error: actor_label parameter is required"
        
        # First, get all actors to find the one with the matching label
        actors_result = unreal.send_command(
            "/Script/UnrealEd.Default__EditorActorSubsystem",
            "GetAllLevelActors"
        )
        
        actors = actors_result.get("ReturnValue", [])
        actor_path = None
        
        # Find the actor with the matching label
        for path in actors:
            label_result = unreal.send_command(
                path,
                "GetActorLabel"
            )
            label = label_result.get("ReturnValue", "")
            
            if label == actor_label:
                actor_path = path
                break
        
        if not actor_path:
            return f"Actor '{actor_label}' not found in the current level."
        
        # Apply modifications
        location = params.get('location')
        if location and isinstance(location, list) and len(location) >= 3:
            unreal.send_command(
                actor_path,
                "SetActorLocation",
                {"NewLocation": {"X": location[0], "Y": location[1], "Z": location[2]}}
            )
        
        rotation = params.get('rotation')
        if rotation and isinstance(rotation, list) and len(rotation) >= 3:
            unreal.send_command(
                actor_path,
                "SetActorRotation",
                {"NewRotation": {"Pitch": rotation[0], "Yaw": rotation[1], "Roll": rotation[2]}}
            )
        
        scale = params.get('scale')
        if scale and isinstance(scale, list) and len(scale) >= 3:
            unreal.send_command(
                actor_path,
                "SetActorScale3D",
                {"NewScale3D": {"X": scale[0], "Y": scale[1], "Z": scale[2]}}
            )
        
        visible = params.get('visible')
        if visible is not None:
            unreal.send_command(
                actor_path,
                "SetActorHiddenInGame",
                {"bNewHidden": not visible}
            )
        
        material_color = params.get('material_color') or params.get('color')
        if material_color and isinstance(material_color, list) and len(material_color) >= 3:
            # Get the StaticMeshComponent if it's a StaticMeshActor
            class_result = unreal.send_command(
                actor_path,
                "GetClass"
            )
            
            class_name = class_result.get("ReturnValue", "")
            
            if "StaticMeshActor" in class_name:
                component_result = unreal.send_command(
                    actor_path,
                    "GetComponentByClass",
                    {"ComponentClass": "/Script/Engine.StaticMeshComponent"}
                )
                
                component_path = component_result.get("ReturnValue", "")
                
                if component_path:
                    # Create a dynamic material instance
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
                                    "R": material_color[0],
                                    "G": material_color[1],
                                    "B": material_color[2],
                                    "A": 1.0
                                }
                            }
                        )
        
        return f"Successfully modified actor: {actor_label}"
    except Exception as e:
        logger.error(f"Error modifying actor: {str(e)}")
        return f"Error modifying actor: {str(e)}"


    """
    Create a composite mesh (multiple actors arranged in a specific way) in the Unreal Engine level.
    
    Parameters passed through kwargs:
    - shape/composition_type: Type of composition (TOWER, WALL, STAIRS, TABLE_CHAIR, HOUSE)
    - label/name: Optional base name for the actors (will be appended with numbers)
    - location: Optional base [x, y, z] location coordinates for the composition
    - size/scale: Optional base [x, y, z] scale factor for all meshes
    - color/material_color: Optional [r, g, b] color values (0.0-1.0) for all meshes
    """
    try:
        # Parse kwargs string into a dictionary if it's a string
        params = parse_kwargs(kwargs)
        logger.info(f"Parsed parameters: {params}")
        
        # Get composition type
        composition_type = params.get('shape') or params.get('composition_type', 'TOWER').upper()
        
        # Get other parameters
        name = params.get('label') or params.get('name') or f"{composition_type.lower()}"
        
        # Parse location
        location = params.get('location')
        # Handle case where location might be a comma-separated string
        if isinstance(location, str) and ',' in location:
            location = [float(x) for x in location.split(',')]
        base_loc = location or [0, 0, 0]
        
        # Parse scale or size
        scale = params.get('scale') or params.get('size')
        # Handle case where scale might be a comma-separated string
        if isinstance(scale, str) and ',' in scale:
            scale = [float(x) for x in scale.split(',')]
        base_sc = scale or [1, 1, 1]
        
        # Parse color
        material_color = params.get('color') or params.get('material_color')
        
        # Create the appropriate composite based on type
        # For now we'll just call through to the existing implementation
        # but with properly parsed parameters
        
        # Create a Context object to pass to the original function
        from mcp.server.fastmcp import Context as MCPContext
        context = MCPContext()
        
        # Use the original function with parsed parameters
        from unreal_modeling import create_composite_mesh as original_create_composite_mesh
        result = original_create_composite_mesh(
            context,
            composition_type=composition_type,
            name=name,
            base_location=base_loc,
            base_scale=base_sc,
            material_color=material_color
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error creating composition: {str(e)}")
        return f"Error creating composition: {str(e)}"

def spawn_actor_from_class(ctx: Context, kwargs):
    """
    Spawn a level actor based on an Unreal Blueprint class.
    
    Parameters passed through kwargs:
    - actor_class: (required) path to the blueprint class (like '/Game/AssetName/Blueprints/BP_House0.BP_House0_C')
    - actor_label/name: Name for the actor
    - location: [x, y, z] location coordinates
    - rotation: [pitch, yaw, roll] rotation in degrees
    - scale: [x, y, z] scale factors
    """
    try:
        unreal = get_unreal_connection()
        
        # Parse kwargs string into a dictionary if it's a string
        params = parse_kwargs(kwargs)
        logger.info(f"Parsed parameters: {params}")
        
        # Required parameter check
        actor_class = params.get('actor_class') or params.get('ActorClass') or params.get('class')
        if not actor_class:
            return "Error: actor_class parameter is required. Provide the full path to the Blueprint class."
        
        # Get actor name
        name = params.get('actor_label') or params.get('name') or "NewBlueprintActor"
        
        # Get location, rotation, scale
        location = params.get('location', [0, 0, 0])
        rotation = params.get('rotation', [0, 0, 0])
        scale = params.get('scale', [1, 1, 1])
        
        # Convert to Unreal Engine format
        if isinstance(location, list) and len(location) >= 3:
            location_param = {"X": location[0], "Y": location[1], "Z": location[2]}
        else:
            location_param = {"X": 0, "Y": 0, "Z": 0}
            
        if isinstance(rotation, list) and len(rotation) >= 3:
            rotation_param = {"Pitch": rotation[0], "Yaw": rotation[1], "Roll": rotation[2]}
        else:
            rotation_param = {"Pitch": 0, "Yaw": 0, "Roll": 0}
        
        # Step 1: Spawn the actor from the Blueprint class
        spawn_result = unreal.send_command(
            "/Script/EditorScriptingUtilities.Default__EditorLevelLibrary",
            "SpawnActorFromClass",
            {
                "ActorClass": actor_class,
                "Location": location_param,
                "Rotation": rotation_param
            }
        )
        
        actor_path = spawn_result.get("ReturnValue", "")
        
        if not actor_path:
            return f"Error: Failed to spawn actor from class: {actor_class}"
        
        # Step 2: Set actor scale
        if isinstance(scale, list) and len(scale) >= 3:
            unreal.send_command(
                actor_path,
                "SetActorScale3D",
                {"NewScale3D": {"X": scale[0], "Y": scale[1], "Z": scale[2]}}
            )
        
        # Step 3: Set actor name/label
        unreal.send_command(
            actor_path,
            "SetActorLabel",
            {"NewActorLabel": name}
        )
        
        return f"Successfully created actor '{name}' from class '{actor_class}'"
    except Exception as e:
        logger.error(f"Error spawning actor from class: {str(e)}")
        return f"Error spawning actor from class: {str(e)}"

def spawn_static_mesh_actor_from_mesh(ctx: Context, kwargs):
    """
    Spawn a static mesh actor using an existing static mesh asset.
    
    Parameters passed through kwargs:
    - static_mesh: (required) path to the static mesh asset (like '/Game/AssetName/Meshes/SM_KYT_Bench01')
    - actor_label/name: Name for the actor
    - location: [x, y, z] location coordinates
    - rotation: [pitch, yaw, roll] rotation in degrees
    - scale: [x, y, z] scale factors
    - material_override: Path to material to use
    - color: [r, g, b] color values (0.0-1.0)
    """
    try:
        unreal = get_unreal_connection()
        
        # Parse kwargs string into a dictionary if it's a string
        params = parse_kwargs(kwargs)
        logger.info(f"Parsed parameters: {params}")
        
        # Required parameter check
        static_mesh = params.get('static_mesh') or params.get('StaticMesh') or params.get('mesh')
        if not static_mesh:
            return "Error: static_mesh parameter is required. Provide the full path to the static mesh asset."
        
        # Get actor name
        name = params.get('actor_label') or params.get('name') or "NewStaticMeshActor"
        
        # Get location, rotation, scale
        location = params.get('location', [0, 0, 0])
        rotation = params.get('rotation', [0, 0, 0])
        scale = params.get('scale', [1, 1, 1])
        
        # Convert to Unreal Engine format
        if isinstance(location, list) and len(location) >= 3:
            location_param = {"X": location[0], "Y": location[1], "Z": location[2]}
        else:
            location_param = {"X": 0, "Y": 0, "Z": 0}
            
        if isinstance(rotation, list) and len(rotation) >= 3:
            rotation_param = {"Pitch": rotation[0], "Yaw": rotation[1], "Roll": rotation[2]}
        else:
            rotation_param = {"Pitch": 0, "Yaw": 0, "Roll": 0}
        
        # Step 1: Spawn the static mesh actor
        spawn_result = unreal.send_command(
            "/Script/EditorScriptingUtilities.Default__EditorLevelLibrary",
            "SpawnActorFromClass",
            {
                "ActorClass": "/Script/Engine.StaticMeshActor",
                "Location": location_param,
                "Rotation": rotation_param
            }
        )
        
        actor_path = spawn_result.get("ReturnValue", "")
        
        if not actor_path:
            return "Error: Failed to spawn static mesh actor"
        
        # Step 2: Get the StaticMeshComponent
        component_result = unreal.send_command(
            actor_path,
            "GetComponentByClass",
            {"ComponentClass": "/Script/Engine.StaticMeshComponent"}
        )
        
        component_path = component_result.get("ReturnValue", "")
        
        if not component_path:
            return "Error: Failed to get StaticMeshComponent"
        
        # Step 3: Set the StaticMesh
        unreal.send_command(
            component_path,
            "SetStaticMesh",
            {"NewMesh": static_mesh}
        )
        
        # Step 4: Set actor scale
        if isinstance(scale, list) and len(scale) >= 3:
            unreal.send_command(
                actor_path,
                "SetActorScale3D",
                {"NewScale3D": {"X": scale[0], "Y": scale[1], "Z": scale[2]}}
            )
        
        # Step 5: Set actor name/label
        unreal.send_command(
            actor_path,
            "SetActorLabel",
            {"NewActorLabel": name}
        )
        
        # Step 6: Set material if provided
        material_override = params.get('material_override')
        material_color = params.get('material_color') or params.get('color')
        
        if material_override:
            unreal.send_command(
                component_path,
                "SetMaterial",
                {"ElementIndex": 0, "Material": material_override}
            )
        elif material_color and isinstance(material_color, list) and len(material_color) >= 3:
            # Create a dynamic material instance
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
                            "R": material_color[0],
                            "G": material_color[1],
                            "B": material_color[2],
                            "A": 1.0
                        }
                    }
                )
        
        return f"Successfully created static mesh actor '{name}' using mesh '{static_mesh}'"
    except Exception as e:
        logger.error(f"Error spawning static mesh actor: {str(e)}")
        return f"Error spawning static mesh actor: {str(e)}"

def get_available_assets(ctx: Context, kwargs):
    """
    Get a list of available assets of a specific type in the project.
    
    Parameters passed through kwargs:
    - asset_type: Type of assets to list (BlueprintClass, StaticMesh, Material, etc.)
    - search_path: Optional path to search for assets (e.g., '/Game/AssetName')
    - search_term: Optional term to filter results (e.g., 'House')
    - max_results: Maximum number of results to return (default: 20)
    - recursive: Whether to search recursively (default: True)
    """
    try:
        unreal = get_unreal_connection()
        
        # Parse kwargs string into a dictionary if it's a string
        params = parse_kwargs(kwargs)
        logger.info(f"Parsed parameters: {params}")
        
        # Get parameters
        asset_type = params.get('asset_type', 'All').lower()
        search_path = params.get('search_path', '/Game')
        search_term = params.get('search_term', '')
        max_results = params.get('max_results', 20)
        recursive = params.get('recursive', True)
        
        # Convert string boolean to actual boolean if needed
        if isinstance(recursive, str):
            recursive = recursive.lower() == 'true'
        
        # Map asset type strings to their common identifiers in paths and naming
        asset_type_identifiers = {
            'blueprint': ['/blueprint', '/blueprints', 'bp_', '_bp', '.bp'],
            'staticmesh': ['/mesh', '/meshes', '/staticmesh', '/staticmeshes', 'sm_', '_sm', '.sm'],
            'material': ['/material', '/materials', 'mat_', '_mat', '.mat', 'm_'],
            'texture': ['/texture', '/textures', 't_', '_t', '.t'],
            'sound': ['/sound', '/sounds', '/audio', 's_', '_s', '.s'],
            'particle': ['/fx', '/effect', '/effects', '/particle', '/particles', 'fx_', 'p_', '_p'],
            'animation': ['/anim', '/animation', '/animations', 'a_', '_a', '.a'],
        }
        
        # Use the EditorAssetLibrary to get available assets
        try:
            # Get assets in the specified path
            list_assets_result = unreal.send_command(
                "/Script/EditorScriptingUtilities.Default__EditorAssetLibrary",
                "ListAssets",
                {
                    "DirectoryPath": search_path,
                    "Recursive": recursive,
                    "IncludeFolder": True
                }
            )
            
            assets = list_assets_result.get("ReturnValue", [])
            logger.info(f"Found {len(assets)} total assets in {search_path}")
            
            # Filter assets by type and search term
            filtered_assets = []
            
            for asset_path in assets:
                # Skip if empty
                if not asset_path:
                    continue
                
                # Path lowercase for case-insensitive matching
                asset_path_lower = asset_path.lower()
                
                # Check asset type if specified
                asset_type_match = True
                if asset_type != 'all' and asset_type in asset_type_identifiers:
                    identifiers = asset_type_identifiers[asset_type]
                    # Check if any of the type identifiers exist in the path
                    if not any(identifier in asset_path_lower for identifier in identifiers):
                        asset_type_match = False
                
                # Check for search term match if specified
                search_term_match = True
                if search_term and search_term.lower() not in asset_path_lower:
                    search_term_match = False
                
                # Add asset to filtered list if it matches all criteria
                if asset_type_match and search_term_match:
                    filtered_assets.append(asset_path)
                
                # Stop if we've reached the max results
                if len(filtered_assets) >= max_results:
                    break
            
            # Prepare the response
            result = {
                "asset_type": asset_type.capitalize() if asset_type != 'all' else "All",
                "search_path": search_path,
                "search_term": search_term,
                "total_found": len(filtered_assets),
                "assets": filtered_assets
            }
            
            return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"Error using EditorAssetLibrary: {str(e)}")
            
            # Fall back to a different approach - try using GetAssetsByPath
            try:
                # This is an alternative approach that might work better
                get_assets_result = unreal.send_command(
                    "/Script/EditorScriptingUtilities.Default__EditorAssetLibrary",
                    "GetAssetsByPath",
                    {
                        "DirectoryPath": search_path,
                        "Recursive": recursive,
                        "IncludeFolder": True
                    }
                )
                
                assets = get_assets_result.get("ReturnValue", [])
                
                # Filter and process as before
                filtered_assets = []
                for asset_path in assets:
                    if not asset_path:
                        continue
                    
                    # Path lowercase for case-insensitive matching
                    asset_path_lower = asset_path.lower()
                    
                    # Check asset type if specified
                    asset_type_match = True
                    if asset_type != 'all' and asset_type in asset_type_identifiers:
                        identifiers = asset_type_identifiers[asset_type]
                        # Check if any of the type identifiers exist in the path
                        if not any(identifier in asset_path_lower for identifier in identifiers):
                            asset_type_match = False
                    
                    # Check for search term match if specified
                    search_term_match = True
                    if search_term and search_term.lower() not in asset_path_lower:
                        search_term_match = False
                    
                    # Add asset to filtered list if it matches all criteria
                    if asset_type_match and search_term_match:
                        filtered_assets.append(asset_path)
                    
                    # Stop if we've reached the max results
                    if len(filtered_assets) >= max_results:
                        break
                
                result = {
                    "asset_type": asset_type.capitalize() if asset_type != 'all' else "All",
                    "search_path": search_path,
                    "search_term": search_term,
                    "total_found": len(filtered_assets),
                    "assets": filtered_assets
                }
                
                return json.dumps(result, indent=2)
                
            except Exception as e2:
                logger.error(f"Alternative approach also failed: {str(e2)}")
                return f"Error listing assets: {str(e)}. Alternative approach also failed: {str(e2)}"
            
    except Exception as e:
        logger.error(f"Error getting available assets: {str(e)}")
        return f"Error getting available assets: {str(e)}"

def search_all_subdirs(ctx: Context, base_path, asset_type=None, search_term=None, max_results=50):
    """
    Search for assets in all known subdirectories of a base path.
    
    Parameters:
    - base_path: The base path to search in (e.g., '/Game/KyotoAlley')
    - asset_type: Optional type of assets to filter by
    - search_term: Optional search term to filter results
    - max_results: Maximum number of results per subdirectory
    
    Returns:
    A combined JSON string with all the assets found.
    """
    # Common subdirectories in Unreal Engine projects
    common_subdirs = [
        "",  # Base directory itself
        "/Blueprints",
        "/Meshes", 
        "/StaticMeshes",
        "/Materials",
        "/Textures",
        "/FX",
        "/Audio",
        "/Animations"
    ]
    
    # Prepare kwargs for each search
    if asset_type:
        asset_type_param = f"asset_type={asset_type} "
    else:
        asset_type_param = ""
        
    if search_term:
        search_term_param = f"search_term={search_term} "
    else:
        search_term_param = ""
        
    max_results_param = f"max_results={max_results}"
    
    # Combined assets from all subdirectories
    all_assets = []
    
    # Search in each subdirectory
    for subdir in common_subdirs:
        search_path = f"{base_path}{subdir}"
        kwargs_str = f"{asset_type_param}search_path={search_path} {search_term_param}{max_results_param}"
        
        try:
            # Get assets in this subdirectory
            result_str = get_available_assets(ctx, kwargs_str)  # Fixed: list_available_assets → get_available_assets
            result = json.loads(result_str)
            
            # Add assets to the combined list
            if result and "assets" in result:
                found_assets = result.get("assets", [])
                all_assets.extend(found_assets)
                logger.info(f"Found {len(found_assets)} assets in {search_path}")
        except Exception as e:
            logger.warning(f"Error searching in {search_path}: {str(e)}")
            continue
    
    # Remove duplicates while preserving order
    unique_assets = []
    for asset in all_assets:
        if asset not in unique_assets:
            unique_assets.append(asset)
    
    # Prepare the combined result
    combined_result = {
        "asset_type": asset_type.capitalize() if asset_type else "All",
        "search_path": base_path,
        "search_term": search_term or "",
        "total_found": len(unique_assets),
        "assets": unique_assets[:max_results]  # Limit to max_results
    }
    
    return json.dumps(combined_result, indent=2)

