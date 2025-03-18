# unreal_utils.py
# Utility functions for the Unreal MCP server

import json
import logging
from typing import Dict, Any, List, Union, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UnrealUtils")

def parse_kwargs(kwargs_str) -> Dict[str, Any]:
    """
    Parse kwargs from string, dict, or JSON format to a unified dictionary.
    
    Args:
        kwargs_str: String with key=value pairs, JSON string, or dictionary
        
    Returns:
        Dictionary of parsed parameters
    """
    if not kwargs_str:
        return {}
    
    # If it's already a dictionary, return it
    if isinstance(kwargs_str, dict):
        return kwargs_str
        
    # Check if it's a JSON string
    if isinstance(kwargs_str, str):
        if kwargs_str.strip().startswith('{') and kwargs_str.strip().endswith('}'):
            try:
                return json.loads(kwargs_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse as JSON: {kwargs_str}")
                # Continue with key=value parsing
    
    # Parse as space-separated key=value pairs
    kwargs = {}
    
    if isinstance(kwargs_str, str):
        parts = kwargs_str.split()
        
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                kwargs[key] = parse_value(key, value)
    
    return kwargs

def parse_value(key: str, value: str) -> Any:
    """
    Parse a string value into the appropriate type based on key and content.
    
    Args:
        key: Parameter key name
        value: String value to parse
        
    Returns:
        Parsed value in appropriate type
    """
    # Parse vectors (location, rotation, scale, color)
    if ',' in value and key in ['location', 'rotation', 'scale', 'color', 'material_color']:
        return [float(x) for x in value.split(',')]
    
    # Parse booleans
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    
    # Parse numbers
    if value.isdigit():
        return int(value)
    if value.replace('.', '', 1).isdigit():
        return float(value)
    
    # Default to string
    return value

def vector_to_ue_format(vector: List[float], keys: List[str] = None) -> Dict[str, float]:
    """
    Convert a vector list [x, y, z] to Unreal Engine format {"X": x, "Y": y, "Z": z}
    or with custom keys.
    
    Args:
        vector: List of float values
        keys: Optional list of custom keys (default: ["X", "Y", "Z"])
        
    Returns:
        Dictionary in Unreal Engine format
    """
    if not keys:
        keys = ["X", "Y", "Z"]
        
    if not isinstance(vector, list) or len(vector) < len(keys):
        # Return default values if vector is invalid
        return {k: 0.0 if k != "A" else 1.0 for k in keys}
    
    # Ensure all values are floats
    result = {}
    for i, k in enumerate(keys):
        if i < len(vector):
            result[k] = float(vector[i])
        elif k == "A":  # Default alpha to 1.0
            result[k] = 1.0
        else:
            result[k] = 0.0
            
    return result

def format_transform_params(params: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Format location, rotation, and scale parameters for Unreal Engine.
    
    Args:
        params: Dictionary of parameters
        
    Returns:
        Dictionary with formatted location, rotation, and scale
    """
    result = {}
    
    # Format location
    location = params.get('location')
    if location:
        result['location'] = vector_to_ue_format(location)
    
    # Format rotation
    rotation = params.get('rotation')
    if rotation:
        result['rotation'] = vector_to_ue_format(rotation, ["Pitch", "Yaw", "Roll"])
    
    # Format scale
    scale = params.get('scale')
    if scale:
        result['scale'] = vector_to_ue_format(scale)
    
    return result

def get_common_actor_name(params: Dict[str, Any], default_name: str = "NewActor") -> str:
    """
    Get actor name from parameters, checking common variations.
    
    Args:
        params: Dictionary of parameters
        default_name: Default name if none is specified
        
    Returns:
        Actor name to use
    """
    return params.get('actor_label') or params.get('name') or params.get('label') or default_name

def validate_required_params(params: Dict[str, Any], required_keys: List[str]) -> Tuple[bool, str]:
    """
    Validate that required parameters are present.
    
    Args:
        params: Dictionary of parameters
        required_keys: List of required parameter keys
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    missing = [key for key in required_keys if not params.get(key)]
    
    if missing:
        return False, f"Missing required parameters: {', '.join(missing)}"
    
    return True, ""

# Common subdirectories in Unreal Engine projects for asset searches
COMMON_SUBDIRS = [
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

# Map of basic shapes to their asset paths
BASIC_SHAPES = {
    "CUBE": "/Engine/BasicShapes/Cube.Cube",
    "SPHERE": "/Engine/BasicShapes/Sphere.Sphere",
    "CYLINDER": "/Engine/BasicShapes/Cylinder.Cylinder",
    "PLANE": "/Engine/BasicShapes/Plane.Plane",
    "CONE": "/Engine/BasicShapes/Cone.Cone"
}

# Asset type identifiers for searching
ASSET_TYPE_IDENTIFIERS = {
    'blueprint': ['/blueprint', '/blueprints', 'bp_', '_bp', '.bp'],
    'staticmesh': ['/mesh', '/meshes', '/staticmesh', '/staticmeshes', 'sm_', '_sm', '.sm'],
    'material': ['/material', '/materials', 'mat_', '_mat', '.mat', 'm_'],
    'texture': ['/texture', '/textures', 't_', '_t', '.t'],
    'sound': ['/sound', '/sounds', '/audio', 's_', '_s', '.s'],
    'particle': ['/fx', '/effect', '/effects', '/particle', '/particles', 'fx_', 'p_', '_p'],
    'animation': ['/anim', '/animation', '/animations', 'a_', '_a', '.a'],
}
