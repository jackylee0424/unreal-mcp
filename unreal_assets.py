# unreal_assets.py
# Functions for working with Unreal Engine assets

import logging
import json
from typing import Dict, Any, List, Optional

from unreal_connection import get_unreal_connection
from unreal_utils import (
    parse_kwargs, COMMON_SUBDIRS, ASSET_TYPE_IDENTIFIERS
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UnrealAssets")

def get_available_assets(kwargs_str) -> str:
    """
    Get a list of available assets of a specific type in the project
    
    Args:
        kwargs_str: String or dict with parameters:
            - asset_type: Type of assets to list
            - search_path: Optional path to search in
            - search_term: Optional term to filter by
            - max_results: Maximum number of results
            - recursive: Whether to search recursively
            
    Returns:
        JSON string with matching assets
    """
    try:
        unreal = get_unreal_connection()
        params = parse_kwargs(kwargs_str)
        
        # Get parameters
        asset_type = params.get('asset_type', 'All').lower()
        search_path = params.get('search_path', '/Game')
        search_term = params.get('search_term', '')
        max_results = params.get('max_results', 20)
        recursive = params.get('recursive', True)
        
        # Convert string boolean to actual boolean if needed
        if isinstance(recursive, str):
            recursive = recursive.lower() == 'true'
        
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
                if asset_type != 'all' and asset_type in ASSET_TYPE_IDENTIFIERS:
                    identifiers = ASSET_TYPE_IDENTIFIERS[asset_type]
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
                # Alternative approach
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
                
                # Filter assets as before
                filtered_assets = []
                for asset_path in assets:
                    if not asset_path:
                        continue
                    
                    asset_path_lower = asset_path.lower()
                    
                    # Check asset type
                    asset_type_match = True
                    if asset_type != 'all' and asset_type in ASSET_TYPE_IDENTIFIERS:
                        identifiers = ASSET_TYPE_IDENTIFIERS[asset_type]
                        if not any(identifier in asset_path_lower for identifier in identifiers):
                            asset_type_match = False
                    
                    # Check search term
                    search_term_match = True
                    if search_term and search_term.lower() not in asset_path_lower:
                        search_term_match = False
                    
                    # Add to filtered list if matching
                    if asset_type_match and search_term_match:
                        filtered_assets.append(asset_path)
                    
                    # Check max results
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

def search_assets_recursively(base_path: str, asset_type: str = None, search_term: str = None, max_results: int = 50) -> str:
    """
    Search for assets in all common subdirectories of a base path
    
    Args:
        base_path: Base path to search in
        asset_type: Optional type of assets to filter by
        search_term: Optional term to filter results
        max_results: Maximum number of results
        
    Returns:
        JSON string with matched assets
    """
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
    for subdir in COMMON_SUBDIRS:
        search_path = f"{base_path}{subdir}"
        kwargs_str = f"{asset_type_param}search_path={search_path} {search_term_param}{max_results_param}"
        
        try:
            # Get assets in this subdirectory
            result_str = get_available_assets(kwargs_str)
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

def get_level_info() -> str:
    """
    Get information about the current level
    
    Returns:
        JSON string with level information
    """
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
                
                # Try to get actor label
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
                
                # Infer type from the path
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
        
        # Get current level info
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
        logger.error(f"Error getting level info: {str(e)}")
        return f"Error getting level info: {str(e)}"