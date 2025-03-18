# unreal_connection.py
# Handles connection and communication with Unreal Engine

import logging
import requests
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UnrealConnection")

class UnrealConnection:
    """Class to manage connection to Unreal Engine Remote Control API"""
    def __init__(self, host: str = "127.0.0.1", port: int = 30010):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/remote/object/call"
    
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
        """
        Send a command to Unreal Engine and return the response
        
        Args:
            object_path: Path to the UE object
            function_name: Name of the function to call
            parameters: Dictionary of parameters to pass
            generate_transaction: Whether to generate a transaction for undo
            
        Returns:
            Dictionary with the response from Unreal Engine
            
        Raises:
            Exception: If there's an error communicating with Unreal Engine
        """
        payload = {
            "objectPath": object_path,
            "functionName": function_name,
            "parameters": parameters or {},
            "generateTransaction": generate_transaction
        }
        
        try:
            # Log the command being sent
            if parameters:
                logger.info(f"Sending UE command: {function_name} with params: {parameters}")
            else:
                logger.info(f"Sending UE command: {function_name}")
            
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

    def find_actor_by_label(self, actor_label: str) -> Optional[str]:
        """
        Find an actor by its label and return its path
        
        Args:
            actor_label: The label of the actor to find
            
        Returns:
            The actor path if found, None otherwise
        """
        try:
            # Get all actors
            actors_result = self.send_command(
                "/Script/UnrealEd.Default__EditorActorSubsystem",
                "GetAllLevelActors"
            )
            
            actors = actors_result.get("ReturnValue", [])
            
            # Find the actor with the matching label
            for path in actors:
                try:
                    label_result = self.send_command(
                        path,
                        "GetActorLabel"
                    )
                    label = label_result.get("ReturnValue", "")
                    
                    if label == actor_label:
                        return path
                except Exception:
                    # If GetActorLabel fails, try to check if the actor name in the path matches
                    if actor_label in path:
                        return path
            
            return None
        except Exception as e:
            logger.error(f"Error finding actor by label: {str(e)}")
            return None

    def get_component_by_class(self, actor_path: str, component_class: str) -> Optional[str]:
        """
        Get a component by its class from an actor
        
        Args:
            actor_path: Path to the actor
            component_class: Class of the component to find
            
        Returns:
            The component path if found, None otherwise
        """
        try:
            result = self.send_command(
                actor_path,
                "GetComponentByClass",
                {"ComponentClass": component_class}
            )
            
            return result.get("ReturnValue")
        except Exception as e:
            logger.error(f"Error getting component: {str(e)}")
            return None

# Global connection instance
_unreal_connection = None

def get_unreal_connection():
    """Get or create a persistent Unreal connection"""
    global _unreal_connection
    
    # If we have an existing connection, check if it's still valid
    if _unreal_connection is not None:
        try:
            if _unreal_connection.test_connection():
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
