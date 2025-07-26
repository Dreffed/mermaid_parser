# ===== mermaid_parser.py =====
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum

class DiagramType(Enum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequenceDiagram"
    CLASS = "classDiagram"
    STATE = "stateDiagram"
    GANTT = "gantt"
    PIE = "pie"
    UNKNOWN = "unknown"

@dataclass
class DiagramNode:
    id: str
    label: str
    shape_type: str = "rectangle"
    position: Tuple[int, int] = (0, 0)
    style: Dict = None

    def __post_init__(self):
        if self.style is None:
            self.style = {}

@dataclass
class DiagramEdge:
    source: str
    target: str
    label: str = ""
    edge_type: str = "arrow"  # arrow, dotted, thick, etc.
    style: Dict = None

    def __post_init__(self):
        if self.style is None:
            self.style = {}

class MermaidParseError(Exception):
    def __init__(self, message, line_number=None, details=None):
        super().__init__(message)
        self.line_number = line_number
        self.details = details

class MermaidParser:
    def __init__(self):
        self.diagram_type_patterns = {
            r'^flowchart\s+(TD|TB|BT|RL|LR)': DiagramType.FLOWCHART,
            r'^graph\s+(TD|TB|BT|RL|LR)': DiagramType.FLOWCHART,
            r'^sequenceDiagram': DiagramType.SEQUENCE,
            r'^classDiagram': DiagramType.CLASS,
            r'^stateDiagram': DiagramType.STATE,
            r'^gantt': DiagramType.GANTT,
            r'^pie': DiagramType.PIE,
        }

        # Flowchart patterns
        self.node_patterns = {
            r'(\w+)\[([^\]]+)\]': ('rectangle', lambda m: (m.group(1), m.group(2))),
            r'(\w+)\(([^\)]+)\)': ('rounded', lambda m: (m.group(1), m.group(2))),
            r'(\w+)\{([^\}]+)\}': ('diamond', lambda m: (m.group(1), m.group(2))),
            r'(\w+)\(\(([^\)]+)\)\)': ('circle', lambda m: (m.group(1), m.group(2))),
            r'(\w+)\[\[([^\]]+)\]\]': ('subroutine', lambda m: (m.group(1), m.group(2))),
        }

        self.edge_patterns = {
            r'(\w+)\s*-->\s*(\w+)': ('arrow', ''),
            r'(\w+)\s*---\s*(\w+)': ('line', ''),
            r'(\w+)\s*--\|([^|]+)\|-->\s*(\w+)': ('arrow', lambda m: m.group(2)),
            r'(\w+)\s*--\s*([^-]+)\s*-->\s*(\w+)': ('arrow', lambda m: m.group(2)),
            r'(\w+)\s*-\.->\s*(\w+)': ('dotted_arrow', ''),
            r'(\w+)\s*==>\s*(\w+)': ('thick_arrow', ''),
        }

    def parse(self, mermaid_code: str) -> Dict:
        """Parse Mermaid code and return structured representation"""
        if not mermaid_code.strip():
            raise MermaidParseError("Empty Mermaid code provided")

        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]

        if not lines:
            raise MermaidParseError("No valid content found")

        # Detect diagram type
        diagram_type = self._detect_diagram_type(lines[0])

        # Parse based on type
        if diagram_type in [DiagramType.FLOWCHART]:
            return self._parse_flowchart(lines)
        elif diagram_type == DiagramType.SEQUENCE:
            return self._parse_sequence(lines)
        else:
            raise MermaidParseError(f"Diagram type {diagram_type.value} not yet supported")

    def _detect_diagram_type(self, first_line: str) -> DiagramType:
        """Detect the type of Mermaid diagram"""
        for pattern, diagram_type in self.diagram_type_patterns.items():
            if re.match(pattern, first_line.strip(), re.IGNORECASE):
                return diagram_type

        # Default to flowchart if no specific type detected
        return DiagramType.FLOWCHART

    def _parse_flowchart(self, lines: List[str]) -> Dict:
        """Parse flowchart diagram"""
        nodes = {}
        edges = []
        direction = "TD"  # Default direction

        # Extract direction from first line if present
        first_line = lines[0]
        direction_match = re.search(r'(TD|TB|BT|RL|LR)', first_line)
        if direction_match:
            direction = direction_match.group(1)

        for line_num, line in enumerate(lines[1:], 2):  # Skip first line (diagram declaration)
            try:
                # Try to parse as node definition
                node_parsed = False
                for pattern, (shape_type, extractor) in self.node_patterns.items():
                    match = re.search(pattern, line)
                    if match:
                        if callable(extractor):
                            node_id, label = extractor(match)
                        else:
                            node_id, label = extractor

                        nodes[node_id] = DiagramNode(
                            id=node_id,
                            label=label,
                            shape_type=shape_type
                        )
                        node_parsed = True
                        break

                if node_parsed:
                    continue

                # Try to parse as edge definition
                edge_parsed = False
                for pattern, (edge_type, label_extractor) in self.edge_patterns.items():
                    match = re.search(pattern, line)
                    if match:
                        if callable(label_extractor):
                            source, target = match.group(1), match.group(3)
                            label = label_extractor(match)
                        else:
                            source, target = match.group(1), match.group(2)
                            label = label_extractor

                        # Ensure source and target nodes exist
                        if source not in nodes:
                            nodes[source] = DiagramNode(id=source, label=source)
                        if target not in nodes:
                            nodes[target] = DiagramNode(id=target, label=target)

                        edges.append(DiagramEdge(
                            source=source,
                            target=target,
                            label=label,
                            edge_type=edge_type
                        ))
                        edge_parsed = True
                        break

                if not edge_parsed and line.strip():
                    # Check for simple node reference
                    simple_node_match = re.match(r'^(\w+)$', line.strip())
                    if simple_node_match:
                        node_id = simple_node_match.group(1)
                        if node_id not in nodes:
                            nodes[node_id] = DiagramNode(id=node_id, label=node_id)
                    else:
                        print(f"Warning: Could not parse line {line_num}: {line}")

            except Exception as e:
                raise MermaidParseError(f"Error parsing line {line_num}: {line}", line_num, str(e))

        # Calculate basic positions based on direction
        self._calculate_positions(list(nodes.values()), edges, direction)

        return {
            'type': DiagramType.FLOWCHART.value,
            'nodes': list(nodes.values()),
            'edges': edges,
            'metadata': {
                'direction': direction,
                'node_count': len(nodes),
                'edge_count': len(edges)
            }
        }

    def _parse_sequence(self, lines: List[str]) -> Dict:
        """Parse sequence diagram (basic implementation)"""
        participants = []
        messages = []

        for line in lines[1:]:  # Skip first line
            # Parse participant
            participant_match = re.match(r'participant\s+(\w+)(?:\s+as\s+(.+))?', line)
            if participant_match:
                participant_id = participant_match.group(1)
                participant_label = participant_match.group(2) or participant_id
                participants.append(DiagramNode(
                    id=participant_id,
                    label=participant_label,
                    shape_type='participant'
                ))
                continue

            # Parse message
            message_match = re.match(r'(\w+)\s*->>?\s*(\w+)\s*:\s*(.+)', line)
            if message_match:
                source, target, message = message_match.groups()
                messages.append(DiagramEdge(
                    source=source,
                    target=target,
                    label=message,
                    edge_type='message'
                ))

        return {
            'type': DiagramType.SEQUENCE.value,
            'nodes': participants,
            'edges': messages,
            'metadata': {
                'participant_count': len(participants),
                'message_count': len(messages)
            }
        }

    def _calculate_positions(self, nodes: List[DiagramNode], edges: List[DiagramEdge], direction: str):
        """Calculate basic positions for nodes based on diagram direction"""
        if not nodes:
            return

        # Simple layout algorithm
        node_spacing_x = 200
        node_spacing_y = 150
        start_x, start_y = 100, 100

        # Create a simple grid layout for now
        # In a real implementation, you'd want a proper graph layout algorithm

        if direction in ['TD', 'TB']:  # Top to bottom
            for i, node in enumerate(nodes):
                node.position = (start_x + (i % 3) * node_spacing_x,
                               start_y + (i // 3) * node_spacing_y)
        elif direction in ['LR']:  # Left to right
            for i, node in enumerate(nodes):
                node.position = (start_x + (i // 3) * node_spacing_x,
                               start_y + (i % 3) * node_spacing_y)
        else:  # Default positioning
            for i, node in enumerate(nodes):
                node.position = (start_x + (i % 3) * node_spacing_x,
                               start_y + (i // 3) * node_spacing_y)
