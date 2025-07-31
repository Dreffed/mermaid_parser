import requests
import json
import time
import urllib.parse
from typing import Dict, Any, List, Optional
from .base_converter import BaseConverter, ConversionError

class MiroConverter(BaseConverter):
    """Converter for Miro platform with OAuth 2.0 and Personal Access Token support"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://api.miro.com/v2"

        # CORRECT Miro OAuth endpoints
        self.oauth_authorize_url = "https://miro.com/oauth/authorize"
        self.oauth_token_url = "https://api.miro.com/v1/oauth/token"  # ← This was the issue!

        # Determine authentication method
        self.access_token = config.get('access_token')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.redirect_uri = config.get('redirect_uri') or config.get('redirect_url')
        self.refresh_token = config.get('refresh_token')

        # Validate configuration
        self._validate_auth_config()

    def _validate_auth_config(self):
        """Validate authentication configuration"""
        has_access_token = bool(self.access_token)
        has_oauth_creds = bool(self.client_id and self.client_secret)

        if not has_access_token and not has_oauth_creds:
            raise ConversionError(
                "Miro authentication not configured. Provide either:\n"
                "1. Personal Access Token (access_token), or\n"
                "2. OAuth credentials (client_id + client_secret + redirect_uri)"
            )

        if has_oauth_creds and not self.redirect_uri:
            raise ConversionError(
                "OAuth flow requires redirect_uri when using client_id and client_secret"
            )

    def _node_to_miro_shape(self, node) -> Dict:
        """Convert a diagram node to Miro shape data"""
        print(f"Converting node: {node.id}, label: {getattr(node, 'label', 'N/A')}, type: {getattr(node, 'shape_type', 'N/A')}")

        # Map Mermaid shapes to Miro shapes
        shape_type_mapping = {
            'rectangle': 'rectangle',
            'rounded': 'round_rectangle',
            'diamond': 'rhombus',
            'circle': 'circle',
            'subroutine': 'rectangle',
            'participant': 'rectangle'
        }

        miro_shape_type = shape_type_mapping.get(getattr(node, 'shape_type', 'rectangle'), 'rectangle')
        node_label = getattr(node, 'label', str(node.id))

        # Calculate position
        x_pos = 0.0
        y_pos = 0.0
        if hasattr(node, 'position') and node.position:
            x_pos = float(node.position[0])
            y_pos = float(node.position[1])

        # Simplified shape data to avoid parameter issues
        shape_data = {
            'data': {
                'shape': miro_shape_type,
                'content': str(node_label)
            },
            'position': {
                'x': x_pos,
                'y': y_pos
            },
            'geometry': {
                'width': 120.0,
                'height': 80.0
            }
            # Removed complex styling that might cause parameter issues
        }

        return shape_data

    def get_auth_url(self, state: str = None) -> str:
        """
        Generate OAuth authorization URL for user consent

        Args:
            state: Optional state parameter for security

        Returns:
            Authorization URL to redirect users to
        """
        if not self.client_id or not self.redirect_uri:
            raise ConversionError("OAuth not configured - missing client_id or redirect_uri")

        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'boards:read boards:write'  # Required scopes for board operations
        }

        if state:
            params['state'] = state

        query_string = urllib.parse.urlencode(params)
        return f"{self.oauth_authorize_url}?{query_string}"

    def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            authorization_code: Code received from OAuth callback

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        if not self.client_id or not self.client_secret:
            raise ConversionError("OAuth not configured - missing client credentials")

        # Miro expects form-encoded data, not JSON
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'redirect_uri': self.redirect_uri
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            print(f"Exchanging code for token at: {self.oauth_token_url}")
            print(f"Redirect URI: {self.redirect_uri}")

            response = requests.post(
                self.oauth_token_url,
                data=token_data,  # Use data, not json for form encoding
                headers=headers,
                timeout=30
            )

            print(f"Token exchange response status: {response.status_code}")
            print(f"Token exchange response: {response.text}")

            response.raise_for_status()

            token_response = response.json()

            # Store the new access token
            self.access_token = token_response.get('access_token')
            self.refresh_token = token_response.get('refresh_token')

            return token_response

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise ConversionError(f"Failed to exchange code for token: {error_msg}")
        except requests.exceptions.RequestException as e:
            raise ConversionError(f"Network error during token exchange: {str(e)}")
        except Exception as e:
            raise ConversionError(f"Unexpected error during token exchange: {str(e)}")

    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh access token using refresh token

        Returns:
            New token response
        """
        if not self.refresh_token:
            raise ConversionError("No refresh token available")

        if not self.client_id or not self.client_secret:
            raise ConversionError("OAuth not configured - missing client credentials")

        refresh_data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.oauth_token_url,
                data=refresh_data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            token_response = response.json()

            # Update tokens
            self.access_token = token_response.get('access_token')
            if 'refresh_token' in token_response:
                self.refresh_token = token_response.get('refresh_token')

            return token_response

        except requests.exceptions.RequestException as e:
            raise ConversionError(f"Failed to refresh access token: {str(e)}")

    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None, retry_on_auth_error: bool = True) -> Dict:
        """Make authenticated request to Miro API with automatic token refresh"""
        if not self.access_token:
            raise ConversionError("No access token available. Please authenticate first.")

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = None

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ConversionError(f"Unsupported HTTP method: {method}")

            # Handle authentication errors with token refresh
            if response.status_code == 401 and retry_on_auth_error and self.refresh_token:
                try:
                    print("Access token expired, attempting refresh...")
                    self.refresh_access_token()

                    # Retry the request with new token
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    if method.upper() == 'GET':
                        response = requests.get(url, headers=headers, params=params)
                    elif method.upper() == 'POST':
                        response = requests.post(url, headers=headers, json=data)
                    elif method.upper() == 'PUT':
                        response = requests.put(url, headers=headers, json=data)
                    elif method.upper() == 'PATCH':
                        response = requests.patch(url, headers=headers, json=data)
                    elif method.upper() == 'DELETE':
                        response = requests.delete(url, headers=headers)

                except Exception as refresh_error:
                    print(f"Token refresh failed: {refresh_error}")
                    # Continue with original response

            response.raise_for_status()

            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get('message', error_msg)
                if 'details' in error_data:
                    error_msg += f": {error_data['details']}"
            except (ValueError, AttributeError):
                error_msg = str(e)

            raise ConversionError(f"Miro API error: {error_msg}")

        except requests.exceptions.RequestException as e:
            raise ConversionError(f"Network error connecting to Miro: {str(e)}")

        except Exception as e:
            raise ConversionError(f"Unexpected error: {str(e)}")

    def test_connection(self) -> Dict:
        """Test connection to Miro API"""
        try:
            # Try to get user info first (lighter request)
            try:
                user_info = self._make_request('GET', 'users/me')
                user_name = user_info.get('name', 'Unknown')
                user_email = user_info.get('email', 'Unknown')
            except:
                user_name = "Unknown"
                user_email = "Unknown"

            # Try to get boards to test permissions
            result = self._make_request('GET', 'boards', params={'limit': 1})

            return {
                'status': 'success',
                'message': 'Successfully connected to Miro API',
                'details': {
                    'user_name': user_name,
                    'user_email': user_email,
                    'boards_accessible': len(result.get('data', [])),
                    'user_authenticated': True,
                    'auth_method': 'Personal Token' if not self.client_id else 'OAuth 2.0'
                }
            }

        except ConversionError as e:
            return {
                'status': 'error',
                'message': f'Failed to connect to Miro API: {str(e)}',
                'details': {
                    'user_authenticated': False,
                    'auth_method': 'Personal Token' if not self.client_id else 'OAuth 2.0'
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Unexpected error testing Miro connection: {str(e)}',
                'details': {
                    'user_authenticated': False
                }
            }

    # ... rest of the methods remain the same ...
    def convert(self, parsed_diagram: Dict, options: Dict = None) -> Dict:
        """Convert parsed Mermaid diagram to Miro board"""
        if options is None:
            options = {}

        try:
            print("=== MIRO CONVERT START ===")

            # Validate parsed diagram
            if not isinstance(parsed_diagram, dict):
                raise ConversionError("Invalid parsed diagram format")

            nodes = parsed_diagram.get('nodes', [])
            edges = parsed_diagram.get('edges', [])
            diagram_type = parsed_diagram.get('type', 'unknown')

            print(f"Diagram type: {diagram_type}")
            print(f"Nodes count: {len(nodes)}")
            print(f"Edges count: {len(edges)}")

            if not nodes:
                raise ConversionError("No nodes found in diagram")

            # Create a new board
            board_name = options.get('board_name', f"Mermaid {diagram_type.title()} - {time.strftime('%Y-%m-%d %H:%M')}")

            # Simplified board data to avoid parameter issues
            board_data = {
                'name': board_name
            }

            print(f"Creating board with data: {board_data}")

            try:
                board_result = self._make_request('POST', 'boards', board_data)
                board_id = board_result['id']
                print(f"Board created successfully: {board_id}")
            except Exception as board_error:
                print(f"Board creation failed: {board_error}")
                raise ConversionError(f"Failed to create Miro board: {str(board_error)}")

            # Track created items
            shape_mapping = {}  # node_id -> miro_shape_id
            created_shapes = 0
            created_connectors = 0

            # Convert nodes to Miro shapes
            print("=== CREATING SHAPES ===")
            for i, node in enumerate(nodes):
                try:
                    print(f"Creating shape {i+1}/{len(nodes)}: {node.id}")
                    shape_data = self._node_to_miro_shape(node)
                    print(f"Shape data: {json.dumps(shape_data, indent=2)}")

                    shape_result = self._make_request('POST', f'boards/{board_id}/shapes', shape_data)
                    shape_mapping[node.id] = shape_result['id']
                    created_shapes += 1
                    print(f"Shape created successfully: {shape_result['id']}")

                except Exception as shape_error:
                    print(f"Failed to create shape for node {node.id}: {str(shape_error)}")
                    # Continue with other shapes instead of failing completely

            print(f"Created {created_shapes} shapes successfully")

            # Convert edges to Miro connectors
            print("=== CREATING CONNECTORS ===")
            for i, edge in enumerate(edges):
                try:
                    if edge.source in shape_mapping and edge.target in shape_mapping:
                        print(f"Creating connector {i+1}/{len(edges)}: {edge.source} -> {edge.target}")

                        connector_data = self._edge_to_miro_connector(
                            edge,
                            shape_mapping[edge.source],
                            shape_mapping[edge.target]
                        )
                        print(f"Connector data: {json.dumps(connector_data, indent=2)}")

                        connector_result = self._make_request('POST', f'boards/{board_id}/connectors', connector_data)
                        created_connectors += 1
                        print(f"Connector created successfully: {connector_result.get('id', 'unknown')}")
                    else:
                        print(f"Skipping edge {edge.source} -> {edge.target} (missing shapes)")

                except Exception as connector_error:
                    print(f"Failed to create connector for edge {edge.source} -> {edge.target}: {str(connector_error)}")
                    # Continue with other connectors

            print(f"Created {created_connectors} connectors successfully")

            # Generate board URL
            board_url = f"https://miro.com/app/board/{board_id}/"

            result = {
                'url': board_url,
                'board_id': board_id,
                'board_name': board_name,
                'shapes_created': created_shapes,
                'connectors_created': created_connectors,
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'success': True
            }

            print(f"=== MIRO CONVERT SUCCESS ===")
            print(f"Result: {result}")
            return result

        except ConversionError:
            raise  # Re-raise conversion errors as-is

        except Exception as e:
            print(f"=== MIRO CONVERT ERROR ===")
            print(f"Error: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise ConversionError(f"Failed to convert diagram to Miro: {str(e)}")


    def _edge_to_miro_connector(self, edge, start_item_id: str, end_item_id: str) -> Dict:
        """Convert a diagram edge to Miro connector data"""
        print(f"Converting edge: {edge.source} -> {edge.target}, label: {getattr(edge, 'label', '')}")

        # Simplified connector data
        connector_data = {
            'startItem': {
                'id': start_item_id
            },
            'endItem': {
                'id': end_item_id
            }
            # Removed complex styling that might cause parameter issues
        }

        # Add label if present
        edge_label = getattr(edge, 'label', '')
        if edge_label and edge_label.strip():
            connector_data['captions'] = [{
                'content': edge_label.strip(),
                'position': 0.5
            }]

        return connector_data
