"""
Specification parser for extracting requirements and structure.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Requirement:
    """Represents a specification requirement."""

    id: str
    section: str
    level: str  # MUST, SHALL, SHOULD, MAY
    text: str
    context: str  # Surrounding text for context


class SpecParser:
    """Parses A2A specification documents."""

    # Regex patterns for requirements
    REQUIREMENT_PATTERN = re.compile(
        r"(.*?)(MUST|SHALL|SHOULD|MAY|REQUIRED|RECOMMENDED)(?! NOT)(.*?)(?:\.|$)", re.MULTILINE | re.IGNORECASE
    )

    # Section header patterns
    SECTION_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def parse_markdown(self, content: str) -> Dict[str, Any]:
        """
        Parse markdown specification.

        Returns:
            Dict with sections, requirements, and structure
        """
        result = {
            "sections": self._extract_sections(content),
            "requirements": self._extract_requirements(content),
            "structure": self._analyze_structure(content),
        }
        return result

    def parse_proto(self, content: str) -> Dict[str, Any]:
        """
        Parse proto file to extract structure and definitions.

        Returns:
            Dict with messages, services, enums, and fields
        """
        result = {
            "messages": self._extract_proto_messages(content),
            "services": self._extract_proto_services(content),
            "enums": self._extract_proto_enums(content),
            "package": self._extract_proto_package(content),
            "imports": self._extract_proto_imports(content),
        }
        return result

    def _extract_definitions(self, schema: dict) -> Dict[str, Any]:
        """Extract all type definitions from schema."""
        definitions = schema.get("definitions", {})
        extracted = {}

        for def_name, def_content in definitions.items():
            extracted[def_name] = {
                "type": def_content.get("type", "unknown"),
                "description": def_content.get("description", ""),
                "properties": def_content.get("properties", {}),
                "required": def_content.get("required", []),
                "enum": def_content.get("enum", []),
            }

        return extracted

    def _extract_required_fields(self, schema: dict) -> Dict[str, List[str]]:
        """Extract required fields for each object type."""
        definitions = schema.get("definitions", {})
        required_fields = {}

        for def_name, def_content in definitions.items():
            if def_content.get("type") == "object":
                required = def_content.get("required", [])
                if required:
                    required_fields[def_name] = required

        return required_fields

    def _extract_methods(self, schema: dict) -> Dict[str, Any]:
        """Extract method signatures from request/response definitions."""
        definitions = schema.get("definitions", {})
        methods = {}

        # Look for request/response pairs
        for def_name, def_content in definitions.items():
            if def_name.endswith("Request"):
                method_name = def_name.replace("Request", "")
                response_name = method_name + "Response"

                properties = def_content.get("properties", {})
                method_prop = properties.get("method", {})

                if "const" in method_prop:
                    rpc_method = method_prop["const"]
                    methods[rpc_method] = {
                        "request_type": def_name,
                        "response_type": response_name if response_name in definitions else None,
                        "params": properties.get("params", {}),
                        "description": def_content.get("description", ""),
                    }

        return methods

    def _extract_schema_info(self, schema: dict) -> Dict[str, Any]:
        """Extract general schema information."""
        return {
            "schema_version": schema.get("$schema", ""),
            "total_definitions": len(schema.get("definitions", {})),
            "has_error_codes": any("Error" in name for name in schema.get("definitions", {}).keys()),
            "has_requests": any("Request" in name for name in schema.get("definitions", {}).keys()),
            "has_responses": any("Response" in name for name in schema.get("definitions", {}).keys()),
        }

    def _extract_sections(self, content: str) -> List[Dict[str, str]]:
        """Extract section headers and their content."""
        sections = []
        section_matches = list(self.SECTION_PATTERN.finditer(content))

        for i, match in enumerate(section_matches):
            level = len(match.group(1))  # Number of # characters
            title = match.group(2).strip()
            start_pos = match.end()

            # Find end position (next section of same or higher level)
            end_pos = len(content)
            for j in range(i + 1, len(section_matches)):
                next_match = section_matches[j]
                next_level = len(next_match.group(1))
                if next_level <= level:
                    end_pos = next_match.start()
                    break

            section_content = content[start_pos:end_pos].strip()

            sections.append(
                {"level": level, "title": title, "content": section_content, "start_pos": match.start(), "end_pos": end_pos}
            )

        return sections

    def _extract_requirements(self, content: str) -> List[Requirement]:
        """Extract all requirements (MUST, SHALL, SHOULD, MAY)."""
        requirements = []

        # Split content into sections first
        sections = self._extract_sections(content)

        req_id_counter = 1

        for section in sections:
            section_name = section["title"]
            section_content = section["content"]

            # Find all requirements in this section
            for match in self.REQUIREMENT_PATTERN.finditer(section_content):
                before_text = match.group(1).strip()
                requirement_level = match.group(2).upper()
                after_text = match.group(3).strip()

                # Create requirement text
                req_text = f"{before_text} {requirement_level} {after_text}".strip()

                # Get surrounding context (50 chars before and after)
                start_context = max(0, match.start() - 50)
                end_context = min(len(section_content), match.end() + 50)
                context = section_content[start_context:end_context].strip()

                requirement = Requirement(
                    id=f"REQ-{req_id_counter:03d}", section=section_name, level=requirement_level, text=req_text, context=context
                )

                requirements.append(requirement)
                req_id_counter += 1

        return requirements

    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze overall document structure."""
        sections = self._extract_sections(content)

        structure = {
            "total_sections": len(sections),
            "section_hierarchy": {},
            "top_level_sections": [s for s in sections if s["level"] == 1],
            "content_length": len(content),
        }

        # Build hierarchy
        for section in sections:
            level = section["level"]
            if level not in structure["section_hierarchy"]:
                structure["section_hierarchy"][level] = []
            structure["section_hierarchy"][level].append(section["title"])

        return structure

    def generate_refs_file(self, markdown_content: Dict[str, Any], output_path: str = "reports/refs.txt") -> None:
        """
        Generate a reference file containing only the headings from specification.md.

        Args:
            markdown_content: The content of specification.md
            output_path: Path where to save the refs.txt file
        """
        from pathlib import Path

        sections = markdown_content["sections"]
        
        # Ensure parent directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write headings to file
        with open(output_file, "w", encoding="utf-8") as f:
            for section in sections:
                f.write("#" * section["level"] + " " + section["title"] + "\n")
            f.write("\n")  # Add final newline

    def _extract_proto_package(self, content: str) -> str:
        """Extract package declaration from proto file."""
        package_pattern = re.compile(r"^\s*package\s+([a-zA-Z0-9_.]+)\s*;", re.MULTILINE)
        match = package_pattern.search(content)
        return match.group(1) if match else ""

    def _extract_proto_imports(self, content: str) -> List[str]:
        """Extract import statements from proto file."""
        import_pattern = re.compile(r'^\s*import\s+"([^"]+)"\s*;', re.MULTILINE)
        return [match.group(1) for match in import_pattern.finditer(content)]

    def _extract_proto_messages(self, content: str) -> Dict[str, Any]:
        """Extract message definitions from proto file."""
        messages = {}

        # Pattern to match message blocks
        message_pattern = re.compile(
            r'^\s*message\s+(\w+)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
            re.MULTILINE | re.DOTALL
        )

        for match in message_pattern.finditer(content):
            message_name = match.group(1)
            message_body = match.group(2)

            messages[message_name] = {
                "fields": self._extract_proto_fields(message_body),
                "nested_messages": [],  # Could be enhanced to parse nested messages
            }

        return messages

    def _extract_proto_fields(self, message_body: str) -> List[Dict[str, Any]]:
        """Extract fields from a message body."""
        fields = []

        # Pattern to match field definitions
        field_pattern = re.compile(
            r'^\s*(optional|required|repeated)?\s*(\w+)\s+(\w+)\s*=\s*(\d+)',
            re.MULTILINE
        )

        for match in field_pattern.finditer(message_body):
            label = match.group(1) or "optional"
            field_type = match.group(2)
            field_name = match.group(3)
            field_number = match.group(4)

            fields.append({
                "name": field_name,
                "type": field_type,
                "label": label,
                "number": int(field_number),
            })

        return fields

    def _extract_proto_services(self, content: str) -> Dict[str, Any]:
        """Extract service definitions from proto file."""
        services = {}

        # Pattern to match service blocks
        service_pattern = re.compile(
            r'^\s*service\s+(\w+)\s*\{([^}]+)\}',
            re.MULTILINE | re.DOTALL
        )

        for match in service_pattern.finditer(content):
            service_name = match.group(1)
            service_body = match.group(2)

            services[service_name] = {
                "methods": self._extract_proto_rpc_methods(service_body),
            }

        return services

    def _extract_proto_rpc_methods(self, service_body: str) -> List[Dict[str, Any]]:
        """Extract RPC methods from a service body."""
        methods = []

        # Pattern to match RPC method definitions
        rpc_pattern = re.compile(
            r'^\s*rpc\s+(\w+)\s*\(\s*(?:stream\s+)?(\w+)\s*\)\s*returns\s*\(\s*(?:stream\s+)?(\w+)\s*\)',
            re.MULTILINE
        )

        for match in rpc_pattern.finditer(service_body):
            method_name = match.group(1)
            request_type = match.group(2)
            response_type = match.group(3)

            # Check for streaming
            full_match = match.group(0)
            request_streaming = "stream" in full_match.split("returns")[0]
            response_streaming = "stream" in full_match.split("returns")[1]

            methods.append({
                "name": method_name,
                "request_type": request_type,
                "response_type": response_type,
                "request_streaming": request_streaming,
                "response_streaming": response_streaming,
            })

        return methods

    def _extract_proto_enums(self, content: str) -> Dict[str, Any]:
        """Extract enum definitions from proto file."""
        enums = {}

        # Pattern to match enum blocks
        enum_pattern = re.compile(
            r'^\s*enum\s+(\w+)\s*\{([^}]+)\}',
            re.MULTILINE | re.DOTALL
        )

        for match in enum_pattern.finditer(content):
            enum_name = match.group(1)
            enum_body = match.group(2)

            # Extract enum values
            value_pattern = re.compile(r'^\s*(\w+)\s*=\s*(\d+)', re.MULTILINE)
            values = []

            for value_match in value_pattern.finditer(enum_body):
                values.append({
                    "name": value_match.group(1),
                    "number": int(value_match.group(2)),
                })

            enums[enum_name] = {"values": values}

        return enums
