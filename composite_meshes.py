# unreal_modeling.py
# Contains modeling-related functions for the Unreal MCP server

import logging
import json
from typing import Dict, Any, List, Optional, Union
from mcp.server.fastmcp import Context

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CompositeMeshes")

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


def create_composite_mesh(ctx: Context, kwargs):
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
        # Access the parse_kwargs function within this module
        # The error was occurring because parse_kwargs was not properly referenced
        
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
        
        # Now we need to implement the actual composite creation based on the type
        # For different composite types
        
        if composition_type == 'TOWER':
            return create_tower_composite(name, base_loc, base_sc, material_color)
        elif composition_type == 'WALL':
            return create_wall_composite(name, base_loc, base_sc, material_color)
        elif composition_type == 'STAIRS':
            return create_stairs_composite(name, base_loc, base_sc, material_color)
        elif composition_type == 'TABLE_CHAIR':
            return create_table_chair_composite(name, base_loc, base_sc, material_color)
        elif composition_type == 'HOUSE':
            return create_house_composite(name, base_loc, base_sc, material_color)
        else:
            return f"Unknown composition type: {composition_type}"
    
    except Exception as e:
        logger.error(f"Error creating composition: {str(e)}")
        return f"Error creating composition: {str(e)}"

# Helper functions to create specific composite types
def create_tower_composite(name, base_loc, base_sc, material_color):
    """Create a tower composite with base, body, and top"""
    try:
        unreal = get_unreal_connection()
        
        # Create tower base (cube)
        base_params = {
            'actor_label': f"{name}_Base",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1], base_loc[2]],
            'scale': [base_sc[0] * 1.5, base_sc[1] * 1.5, base_sc[2] * 0.2],
            'material_color': material_color
        }
        create_static_mesh_actor(None, base_params)
        
        # Create tower body (cylinder)
        body_params = {
            'actor_label': f"{name}_Body",
            'mesh_type': 'CYLINDER', 
            'location': [base_loc[0], base_loc[1], base_loc[2] + base_sc[2] * 1.0],
            'scale': [base_sc[0], base_sc[1], base_sc[2] * 2.0],
            'material_color': material_color
        }
        create_static_mesh_actor(None, body_params)
        
        # Create tower top (cone)
        top_params = {
            'actor_label': f"{name}_Top",
            'mesh_type': 'CONE', 
            'location': [base_loc[0], base_loc[1], base_loc[2] + base_sc[2] * 3.0],
            'scale': [base_sc[0] * 1.2, base_sc[1] * 1.2, base_sc[2] * 1.0],
            'material_color': material_color
        }
        create_static_mesh_actor(None, top_params)
        
        return f"Successfully created Tower composite: {name}"
    except Exception as e:
        logger.error(f"Error creating tower composite: {str(e)}")
        return f"Error creating tower composite: {str(e)}"

def create_wall_composite(name, base_loc, base_sc, material_color):
    """Create a wall composite with base and segments"""
    try:
        unreal = get_unreal_connection()
        
        # Create wall base
        base_params = {
            'actor_label': f"{name}_Base",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1], base_loc[2]],
            'scale': [base_sc[0] * 8.0, base_sc[1] * 0.5, base_sc[2] * 0.2],
            'material_color': material_color
        }
        create_static_mesh_actor(None, base_params)
        
        # Create wall body
        wall_params = {
            'actor_label': f"{name}_Wall",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1], base_loc[2] + base_sc[2] * 1.0],
            'scale': [base_sc[0] * 8.0, base_sc[1] * 0.5, base_sc[2] * 2.0],
            'material_color': material_color
        }
        create_static_mesh_actor(None, wall_params)
        
        # Create wall battlements (multiple cubes along the top)
        spacing = base_sc[0] * 0.8
        start_x = base_loc[0] - (base_sc[0] * 3.5)
        
        for i in range(10):
            battlement_params = {
                'actor_label': f"{name}_Battlement_{i}",
                'mesh_type': 'CUBE', 
                'location': [start_x + (i * spacing), base_loc[1], base_loc[2] + base_sc[2] * 3.0],
                'scale': [base_sc[0] * 0.4, base_sc[1] * 0.5, base_sc[2] * 0.5],
                'material_color': material_color
            }
            create_static_mesh_actor(None, battlement_params)
        
        return f"Successfully created Wall composite: {name}"
    except Exception as e:
        logger.error(f"Error creating wall composite: {str(e)}")
        return f"Error creating wall composite: {str(e)}"

def create_stairs_composite(name, base_loc, base_sc, material_color):
    """Create a staircase composite with multiple steps"""
    try:
        unreal = get_unreal_connection()
        
        # Number of steps
        num_steps = 10
        
        # Create each step as a cube
        for i in range(num_steps):
            step_params = {
                'actor_label': f"{name}_Step_{i}",
                'mesh_type': 'CUBE', 
                'location': [
                    base_loc[0] + (i * base_sc[0] * 0.5), 
                    base_loc[1], 
                    base_loc[2] + (i * base_sc[2] * 0.5)
                ],
                'scale': [
                    base_sc[0] * 1.0, 
                    base_sc[1] * 2.0, 
                    base_sc[2] * 0.25
                ],
                'material_color': material_color
            }
            create_static_mesh_actor(None, step_params)
        
        return f"Successfully created Stairs composite: {name}"
    except Exception as e:
        logger.error(f"Error creating stairs composite: {str(e)}")
        return f"Error creating stairs composite: {str(e)}"

def create_table_chair_composite(name, base_loc, base_sc, material_color):
    """Create a table and chairs composite"""
    try:
        unreal = get_unreal_connection()
        
        # Create table top
        table_top_params = {
            'actor_label': f"{name}_Table_Top",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1], base_loc[2] + base_sc[2] * 1.0],
            'scale': [base_sc[0] * 2.0, base_sc[1] * 3.0, base_sc[2] * 0.2],
            'material_color': material_color
        }
        create_static_mesh_actor(None, table_top_params)
        
        # Create table legs
        leg_positions = [
            [base_sc[0] * 1.5, base_sc[1] * 2.5, 0],  # Front right
            [base_sc[0] * 1.5, -base_sc[1] * 2.5, 0], # Back right
            [-base_sc[0] * 1.5, base_sc[1] * 2.5, 0], # Front left
            [-base_sc[0] * 1.5, -base_sc[1] * 2.5, 0] # Back left
        ]
        
        for i, pos in enumerate(leg_positions):
            leg_params = {
                'actor_label': f"{name}_Table_Leg_{i}",
                'mesh_type': 'CYLINDER', 
                'location': [
                    base_loc[0] + pos[0], 
                    base_loc[1] + pos[1], 
                    base_loc[2] + base_sc[2] * 0.5
                ],
                'scale': [base_sc[0] * 0.2, base_sc[1] * 0.2, base_sc[2] * 1.0],
                'material_color': material_color
            }
            create_static_mesh_actor(None, leg_params)
        
        # Create chairs
        chair_positions = [
            [0, base_sc[1] * 4.5, 0],  # Front
            [0, -base_sc[1] * 4.5, 0], # Back
            [base_sc[0] * 3.0, 0, 0],  # Right
            [-base_sc[0] * 3.0, 0, 0]  # Left
        ]
        
        for i, pos in enumerate(chair_positions):
            chair_seat_params = {
                'actor_label': f"{name}_Chair_Seat_{i}",
                'mesh_type': 'CUBE', 
                'location': [
                    base_loc[0] + pos[0], 
                    base_loc[1] + pos[1], 
                    base_loc[2] + base_sc[2] * 0.6
                ],
                'scale': [base_sc[0] * 1.0, base_sc[1] * 1.0, base_sc[2] * 0.1],
                'material_color': material_color
            }
            create_static_mesh_actor(None, chair_seat_params)
            
            chair_back_params = {
                'actor_label': f"{name}_Chair_Back_{i}",
                'mesh_type': 'CUBE', 
                'location': [
                    base_loc[0] + pos[0], 
                    base_loc[1] + pos[1] - base_sc[1] * 0.5, 
                    base_loc[2] + base_sc[2] * 1.3
                ],
                'scale': [base_sc[0] * 1.0, base_sc[1] * 0.1, base_sc[2] * 0.8],
                'material_color': material_color
            }
            create_static_mesh_actor(None, chair_back_params)
            
            # Chair legs
            for j in range(4):
                x_offset = 0.4 if j % 2 == 0 else -0.4
                y_offset = 0.4 if j < 2 else -0.4
                
                leg_params = {
                    'actor_label': f"{name}_Chair_Leg_{i}_{j}",
                    'mesh_type': 'CYLINDER', 
                    'location': [
                        base_loc[0] + pos[0] + (x_offset * base_sc[0]), 
                        base_loc[1] + pos[1] + (y_offset * base_sc[1]), 
                        base_loc[2] + base_sc[2] * 0.3
                    ],
                    'scale': [base_sc[0] * 0.1, base_sc[1] * 0.1, base_sc[2] * 0.6],
                    'material_color': material_color
                }
                create_static_mesh_actor(None, leg_params)
        
        return f"Successfully created Table and Chairs composite: {name}"
    except Exception as e:
        logger.error(f"Error creating table and chairs composite: {str(e)}")
        return f"Error creating table and chairs composite: {str(e)}"

def create_house_composite(name, base_loc, base_sc, material_color):
    """Create a simple house composite"""
    try:
        unreal = get_unreal_connection()
        
        # Create house foundation
        foundation_params = {
            'actor_label': f"{name}_Foundation",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1], base_loc[2]],
            'scale': [base_sc[0] * 5.0, base_sc[1] * 6.0, base_sc[2] * 0.2],
            'material_color': material_color
        }
        create_static_mesh_actor(None, foundation_params)
        
        # Create house main body
        house_body_params = {
            'actor_label': f"{name}_MainBody",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1], base_loc[2] + base_sc[2] * 2.0],
            'scale': [base_sc[0] * 4.5, base_sc[1] * 5.5, base_sc[2] * 2.0],
            'material_color': material_color
        }
        create_static_mesh_actor(None, house_body_params)
        
        # Create roof (triangular prism-like shape using scaled cube)
        roof_params = {
            'actor_label': f"{name}_Roof",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1], base_loc[2] + base_sc[2] * 4.5],
            'rotation': [0, 0, 0],
            'scale': [base_sc[0] * 5.0, base_sc[1] * 6.0, base_sc[2] * 1.5],
            'material_color': [0.8, 0.4, 0.2]  # Different color for roof
        }
        create_static_mesh_actor(None, roof_params)
        
        # Create door
        door_params = {
            'actor_label': f"{name}_Door",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0], base_loc[1] + base_sc[1] * 5.5, base_loc[2] + base_sc[2] * 1.25],
            'scale': [base_sc[0] * 0.8, base_sc[1] * 0.1, base_sc[2] * 1.25],
            'material_color': [0.4, 0.2, 0.1]  # Door color
        }
        create_static_mesh_actor(None, door_params)
        
        # Create windows
        window_positions = [
            [base_sc[0] * 2.0, base_sc[1] * 3.0, base_sc[2] * 2.5],   # Right front
            [base_sc[0] * -2.0, base_sc[1] * 3.0, base_sc[2] * 2.5],  # Left front
            [base_sc[0] * 2.0, base_sc[1] * -3.0, base_sc[2] * 2.5],  # Right back
            [base_sc[0] * -2.0, base_sc[1] * -3.0, base_sc[2] * 2.5]  # Left back
        ]
        
        for i, pos in enumerate(window_positions):
            window_params = {
                'actor_label': f"{name}_Window_{i}",
                'mesh_type': 'CUBE', 
                'location': [
                    base_loc[0] + pos[0], 
                    base_loc[1] + pos[1], 
                    base_loc[2] + pos[2]
                ],
                'scale': [base_sc[0] * 0.6, base_sc[1] * 0.1, base_sc[2] * 0.6],
                'material_color': [0.1, 0.6, 0.9]  # Window glass color
            }
            create_static_mesh_actor(None, window_params)
        
        # Create chimney
        chimney_params = {
            'actor_label': f"{name}_Chimney",
            'mesh_type': 'CUBE', 
            'location': [base_loc[0] + base_sc[0] * 2.5, base_loc[1] + base_sc[1] * 2.0, base_loc[2] + base_sc[2] * 6.0],
            'scale': [base_sc[0] * 0.5, base_sc[1] * 0.5, base_sc[2] * 2.0],
            'material_color': [0.5, 0.3, 0.2]  # Chimney color
        }
        create_static_mesh_actor(None, chimney_params)
        
        return f"Successfully created House composite: {name}"
    except Exception as e:
        logger.error(f"Error creating house composite: {str(e)}")
        return f"Error creating house composite: {str(e)}"

