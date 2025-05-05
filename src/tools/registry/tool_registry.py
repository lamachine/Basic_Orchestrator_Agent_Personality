"""Tool registry that manages tool discovery and persistence."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import yaml
import json
import importlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Tool registry that scans sub_graphs for tools and manages approvals."""
    
    def __init__(self, data_dir: str = "src/data/tool_registry"):
        """
        Initialize the tool registry.
        
        Args:
            data_dir: Directory for persistent storage
        """
        self.tools: Dict[str, Any] = {}
        self.tool_configs: Dict[str, dict] = {}
        self.approved_tools: Set[str] = set()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load approvals immediately
        self._load_approvals()
        
    async def discover_tools(self, auto_approve: bool = False):
        """
        Find and register all tools in sub_graphs.
        
        Args:
            auto_approve: Whether to automatically approve newly discovered tools
        """
        # Load any persisted state first
        self._load_persisted_state()
        
        sub_graphs = Path("src/sub_graphs")
        if not sub_graphs.exists():
            logger.warning("sub_graphs directory not found")
            return
        
        # Track newly discovered tools
        discovered_tools = []
            
        # Scan for all agent directories (ending with _agent)
        for tool_dir in sub_graphs.glob("*_agent"):
            if not tool_dir.is_dir():
                continue
            
            # Path to tool configuration - add logging to debug path issues
            logger.debug(f"Checking tool directory: {tool_dir}")
            
            # Try different possible config locations
            possible_config_paths = [
                tool_dir / "src" / "config" / "tool_config.yaml",  # New structure
            ]
            
            config_file = None
            for path in possible_config_paths:
                logger.debug(f"Checking for config at: {path}")
                if path.exists():
                    config_file = path
                    logger.debug(f"Found config at: {path}")
                    break
                    
            if not config_file:
                logger.warning(f"No tool config found in {tool_dir}")
                continue
                
            try:
                # Load basic config
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                
                tool_name = config.get("name")
                if not tool_name:
                    logger.warning(f"No tool name in config: {config_file}")
                    continue
                
                # Store config regardless of approval status
                self.tool_configs[tool_name] = config
                logger.debug(f"Loaded config for tool: {tool_name}")
                
                # Check if tool is already approved
                if tool_name not in self.approved_tools:
                    if auto_approve:
                        # Auto-approve if specified
                        self.approved_tools.add(tool_name)
                        logger.info(f"Auto-approved tool: {tool_name}")
                    else:
                        # Add to discovered list
                        discovered_tools.append(tool_name)
                        logger.info(f"Discovered new tool: {tool_name} (pending approval)")
                        continue  # Skip loading until approved
                
                logger.debug(f"Attempting to load implementation for approved tool: {tool_name}")
                # Only load approved tools
                # Look for the tool class in two locations:
                # 1. First check for API interface at the agent root
                api_file_path = tool_dir / f"{tool_name}_api.py"
                logger.debug(f"Checking for API at: {api_file_path}")
                if api_file_path.exists():
                    logger.debug(f"API file found: {api_file_path}")
                    module_path = f"src.sub_graphs.{tool_dir.name}.{tool_name}_api"
                    try:
                        logger.debug(f"Importing module: {module_path}")
                        module = importlib.import_module(module_path)
                        logger.debug(f"Module imported: {module}")
                        
                        # Find the API class - usually ends with API 
                        api_class_found = False
                        for attr_name in dir(module):
                            logger.debug(f"Checking attribute: {attr_name}")
                            if attr_name.lower().endswith('api') and not attr_name.startswith('_'):
                                api_class = getattr(module, attr_name)
                                logger.debug(f"Found API class: {api_class}")
                                self.tools[tool_name] = api_class
                                api_class_found = True
                                logger.info(f"Registered API interface: {tool_name} from {module_path}")
                                break
                        
                        if not api_class_found:
                            logger.warning(f"No API class found in module: {module_path}")
                    except Exception as e:
                        logger.error(f"Error importing API module {module_path}: {e}", exc_info=True)
                # 2. If no API interface, check for agent entry point
                elif (tool_dir / f"{tool_name}_agent.py").exists():
                    module_path = f"src.sub_graphs.{tool_dir.name}.{tool_name}_agent"
                    module = importlib.import_module(module_path)
                    
                    # Find the agent class
                    for attr_name in dir(module):
                        if attr_name.lower().endswith('agent') and not attr_name.startswith('_'):
                            agent_class = getattr(module, attr_name)
                            self.tools[tool_name] = agent_class
                            logger.info(f"Registered agent: {tool_name} from {module_path}")
                            break
                else:
                    # 3. Check for tool implementation in the src/tools directory
                    module_path = f"src.sub_graphs.{tool_dir.name}.src.tools.{tool_name}_tool"
                    try:
                        module = importlib.import_module(module_path)
                        # Look for a class ending with Tool
                        for attr_name in dir(module):
                            if attr_name.lower().endswith('tool') and not attr_name.startswith('_'):
                                tool_class = getattr(module, attr_name)
                                self.tools[tool_name] = tool_class
                                logger.info(f"Registered tool: {tool_name} from {module_path}")
                                break
                    except ImportError as e:
                        logger.error(f"Failed to import tool {tool_name}: {e}")
                
                # Persist the updated state
                self._persist_state()
                
            except Exception as e:
                logger.error(f"Failed to load tool from {tool_dir}: {e}")
        
        # Return list of newly discovered tools that need approval
        return discovered_tools
    
    def approve_tool(self, tool_name: str) -> bool:
        """
        Approve a tool for use.
        
        Args:
            tool_name: Name of the tool to approve
            
        Returns:
            True if approval was successful, False otherwise
        """
        if tool_name not in self.tool_configs:
            logger.warning(f"Cannot approve unknown tool: {tool_name}")
            return False
            
        self.approved_tools.add(tool_name)
        logger.info(f"Approved tool: {tool_name}")
        
        # Persist approvals
        self._persist_approvals()
        return True
    
    def revoke_tool(self, tool_name: str) -> bool:
        """
        Revoke approval for a tool.
        
        Args:
            tool_name: Name of the tool to revoke
            
        Returns:
            True if revocation was successful, False otherwise
        """
        if tool_name not in self.approved_tools:
            logger.warning(f"Tool {tool_name} is not currently approved")
            return False
            
        self.approved_tools.remove(tool_name)
        
        # Also remove from active tools if loaded
        if tool_name in self.tools:
            del self.tools[tool_name]
            
        logger.info(f"Revoked approval for tool: {tool_name}")
        
        # Persist approvals
        self._persist_approvals()
        return True
    
    def get_tool(self, name: str) -> Optional[Any]:
        """
        Get a tool class by name.
        
        Args:
            name: Name of the tool
            
        Returns:
            Tool class or None if not found or not approved
        """
        # Only return tools that are approved
        if name in self.approved_tools:
            return self.tools.get(name)
        return None
    
    def get_config(self, name: str) -> Optional[dict]:
        """
        Get a tool's config.
        
        Args:
            name: Name of the tool
            
        Returns:
            Tool configuration or None if not found
        """
        return self.tool_configs.get(name)
    
    def list_tools(self) -> List[str]:
        """
        List all approved and loaded tool names.
        
        Returns:
            List of approved tool names
        """
        # Only return tools that are both approved and loaded
        result = [name for name in self.tools.keys() if name in self.approved_tools]
        logger.debug(f"list_tools - approved_tools: {self.approved_tools}")
        logger.debug(f"list_tools - tools.keys: {list(self.tools.keys())}")
        logger.debug(f"list_tools - resulting list: {result}")
        return result
    
    def list_all_discovered_tools(self) -> Dict[str, bool]:
        """
        List all discovered tools with their approval status.
        
        Returns:
            Dictionary mapping tool names to approval status
        """
        return {name: name in self.approved_tools for name in self.tool_configs.keys()}
    
    def _persist_state(self):
        """Save current state to data directory."""
        try:
            state = {
                "last_updated": datetime.utcnow().isoformat(),
                "configs": self.tool_configs
            }
            
            state_file = self.data_dir / "tool_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist tool state: {e}")
    
    def _persist_approvals(self):
        """Save tool approvals to data directory."""
        try:
            approvals = {
                "last_updated": datetime.utcnow().isoformat(),
                "approved_tools": list(self.approved_tools)
            }
            
            approvals_file = self.data_dir / "approved_tools.json"
            with open(approvals_file, 'w') as f:
                json.dump(approvals, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist tool approvals: {e}")
    
    def _load_persisted_state(self):
        """Load previously persisted state if it exists."""
        try:
            state_file = self.data_dir / "tool_state.json"
            if not state_file.exists():
                return
                
            with open(state_file) as f:
                state = json.load(f)
                
            self.tool_configs = state.get("configs", {})
            
        except Exception as e:
            logger.error(f"Failed to load persisted tool state: {e}")
    
    def _load_approvals(self):
        """Load previously persisted approvals if they exist."""
        try:
            approvals_file = self.data_dir / "approved_tools.json"
            if not approvals_file.exists():
                return
                
            with open(approvals_file) as f:
                approvals = json.load(f)
                
            self.approved_tools = set(approvals.get("approved_tools", []))
            
        except Exception as e:
            logger.error(f"Failed to load persisted tool approvals: {e}")
            
    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"ToolRegistry(tools={list(self.tools.keys())}, approved={list(self.approved_tools)})" 