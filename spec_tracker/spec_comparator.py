"""
Compares two versions of specifications to identify changes.
"""

from deepdiff import DeepDiff
from typing import Dict, List, Any
import json


class SpecComparator:
    """Compares specification versions."""

    def compare_specs(self, old_spec: Dict, new_spec: Dict) -> Dict[str, Any]:
        """
        Compare two specification versions.

        Args:
            old_spec: Dict with 'markdown' and 'proto' parsed specs
            new_spec: Dict with 'markdown' and 'proto' parsed specs

        Returns:
            Dict with added, removed, and modified elements
        """
        comparison = {
            "markdown_changes": self._compare_markdown(old_spec.get("markdown", {}), new_spec.get("markdown", {})),
            "proto_changes": self._compare_proto(old_spec.get("proto", {}), new_spec.get("proto", {})),
            "summary": {},
            "impact_classification": {},
        }

        # Keep json_changes as alias to proto_changes for backward compatibility
        comparison["json_changes"] = comparison["proto_changes"]

        # Generate summary
        comparison["summary"] = self._generate_summary(comparison)

        # Classify changes by impact
        comparison["impact_classification"] = self._classify_changes(comparison)

        return comparison

    def _classify_changes(self, comparison: Dict) -> Dict[str, Any]:
        """Classify changes by their impact level."""
        classification = {
            "breaking_changes": [],
            "non_breaking_additions": [],
            "documentation_changes": [],
            "behavioral_changes": [],
        }

        proto_changes = comparison["proto_changes"]

        # Breaking: Removed methods
        for change in proto_changes["methods"]["removed"]:
            classification["breaking_changes"].append(
                {"type": "method_removed", "method": change["name"], "impact": "Client code calling this method will break"}
            )

        # Breaking: Removed definitions
        for change in proto_changes["definitions"]["removed"]:
            classification["breaking_changes"].append(
                {"type": "definition_removed", "definition": change["name"], "impact": "Client code using this type will break"}
            )

        # Non-breaking: Added methods
        for change in proto_changes["methods"]["added"]:
            classification["non_breaking_additions"].append(
                {"type": "method_added", "method": change["name"], "impact": "New functionality available"}
            )

        # Non-breaking: Added definitions
        for change in proto_changes["definitions"]["added"]:
            classification["non_breaking_additions"].append(
                {"type": "definition_added", "definition": change["name"], "impact": "New types available for use"}
            )

        # Analyze requirement changes
        md_changes = comparison["markdown_changes"]

        # Breaking: Removed MUST requirements
        for change in md_changes["requirements"]["removed"]:
            if change["level"] in ["MUST", "SHALL", "REQUIRED"]:
                classification["breaking_changes"].append(
                    {
                        "type": "mandatory_requirement_removed",
                        "requirement": change["requirement"].text,
                        "section": change["section"],
                        "impact": "Previously mandatory behavior no longer required",
                    }
                )

        # Behavioral: Added MUST requirements
        for change in md_changes["requirements"]["added"]:
            if change["level"] in ["MUST", "SHALL", "REQUIRED"]:
                classification["behavioral_changes"].append(
                    {
                        "type": "mandatory_requirement_added",
                        "requirement": change["requirement"].text,
                        "section": change["section"],
                        "impact": "New mandatory behavior required",
                    }
                )
            elif change["level"] in ["SHOULD", "RECOMMENDED"]:
                classification["documentation_changes"].append(
                    {
                        "type": "recommendation_added",
                        "requirement": change["requirement"].text,
                        "section": change["section"],
                        "impact": "New recommended practice",
                    }
                )

        # Documentation: Section changes
        for change in md_changes["sections"]["added"]:
            classification["documentation_changes"].append(
                {"type": "section_added", "section": change["title"], "impact": "New documentation section"}
            )

        for change in md_changes["sections"]["modified"]:
            classification["documentation_changes"].append(
                {
                    "type": "section_modified",
                    "section": change["title"],
                    "impact": "Documentation updated",
                    "change_size": change["content_diff"],
                }
            )

        # Calculate impact score
        classification["impact_score"] = self._calculate_impact_score(classification)

        return classification

    def _calculate_impact_score(self, classification: Dict) -> Dict[str, int]:
        """Calculate numeric impact scores."""
        return {
            "breaking_score": len(classification["breaking_changes"]) * 10,
            "behavioral_score": len(classification["behavioral_changes"]) * 5,
            "addition_score": len(classification["non_breaking_additions"]) * 2,
            "documentation_score": len(classification["documentation_changes"]) * 1,
            "total_impact": (
                len(classification["breaking_changes"]) * 10
                + len(classification["behavioral_changes"]) * 5
                + len(classification["non_breaking_additions"]) * 2
                + len(classification["documentation_changes"]) * 1
            ),
        }

    def _compare_markdown(self, old_md: Dict, new_md: Dict) -> Dict[str, Any]:
        """Compare markdown specifications."""
        changes = {
            "requirements": {"added": [], "removed": [], "modified": []},
            "sections": {"added": [], "removed": [], "modified": []},
        }

        # Since requirement IDs are auto-generated, compare by content
        old_req_texts = {r.text: r for r in old_md.get("requirements", [])}
        new_req_texts = {r.text: r for r in new_md.get("requirements", [])}

        # Find added requirements
        for req_text, req in new_req_texts.items():
            if req_text not in old_req_texts:
                changes["requirements"]["added"].append({"requirement": req, "section": req.section, "level": req.level})

        # Find removed requirements
        for req_text, req in old_req_texts.items():
            if req_text not in new_req_texts:
                changes["requirements"]["removed"].append({"requirement": req, "section": req.section, "level": req.level})

        # Find modified requirements (same section/level but different text)
        # For now, we'll consider requirements as either added or removed
        # More sophisticated diff could identify text modifications

        # Compare sections
        old_sections = {s["title"]: s for s in old_md.get("sections", [])}
        new_sections = {s["title"]: s for s in new_md.get("sections", [])}

        # Find added sections
        for title, section in new_sections.items():
            if title not in old_sections:
                changes["sections"]["added"].append(section)

        # Find removed sections
        for title, section in old_sections.items():
            if title not in new_sections:
                changes["sections"]["removed"].append(section)

        # Find modified sections (same title but different content)
        for title in old_sections:
            if title in new_sections:
                old_content = old_sections[title]["content"]
                new_content = new_sections[title]["content"]
                if old_content != new_content:
                    changes["sections"]["modified"].append(
                        {
                            "title": title,
                            "old_content": old_content,
                            "new_content": new_content,
                            "content_diff": self._generate_text_diff(old_content, new_content),
                        }
                    )

        return changes

    def _compare_proto(self, old_proto: Dict, new_proto: Dict) -> Dict[str, Any]:
        """Compare proto specifications."""

        changes = {
            "messages": {"added": [], "removed": [], "modified": []},
            "services": {"added": [], "removed": [], "modified": []},
            "enums": {"added": [], "removed": [], "modified": []},
            "methods": {"added": [], "removed": [], "modified": []},
            "definitions": {"added": [], "removed": [], "modified": []},  # Alias for messages
        }

        # Compare messages
        old_messages = old_proto.get("messages", {})
        new_messages = new_proto.get("messages", {})

        for msg_name in new_messages:
            if msg_name not in old_messages:
                changes["messages"]["added"].append({"name": msg_name, "message": new_messages[msg_name]})
                changes["definitions"]["added"].append({"name": msg_name, "definition": new_messages[msg_name]})

        for msg_name in old_messages:
            if msg_name not in new_messages:
                changes["messages"]["removed"].append({"name": msg_name, "message": old_messages[msg_name]})
                changes["definitions"]["removed"].append({"name": msg_name, "definition": old_messages[msg_name]})

        for msg_name in old_messages:
            if msg_name in new_messages:
                diff = DeepDiff(old_messages[msg_name], new_messages[msg_name], ignore_order=True)
                if diff:
                    changes["messages"]["modified"].append({
                        "name": msg_name,
                        "old_message": old_messages[msg_name],
                        "new_message": new_messages[msg_name],
                        "diff": diff
                    })
                    changes["definitions"]["modified"].append({
                        "name": msg_name,
                        "old_definition": old_messages[msg_name],
                        "new_definition": new_messages[msg_name],
                        "diff": diff
                    })

        # Compare services and extract methods
        old_services = old_proto.get("services", {})
        new_services = new_proto.get("services", {})

        # Collect all methods from all services
        old_methods_map = {}
        new_methods_map = {}

        for svc_name, svc_info in old_services.items():
            for method in svc_info.get("methods", []):
                old_methods_map[method["name"]] = method

        for svc_name, svc_info in new_services.items():
            for method in svc_info.get("methods", []):
                new_methods_map[method["name"]] = method

        # Compare methods
        for method_name in new_methods_map:
            if method_name not in old_methods_map:
                changes["methods"]["added"].append({"name": method_name, "method_info": new_methods_map[method_name]})

        for method_name in old_methods_map:
            if method_name not in new_methods_map:
                changes["methods"]["removed"].append({"name": method_name, "method_info": old_methods_map[method_name]})

        for method_name in old_methods_map:
            if method_name in new_methods_map:
                if old_methods_map[method_name] != new_methods_map[method_name]:
                    changes["methods"]["modified"].append({
                        "name": method_name,
                        "old_info": old_methods_map[method_name],
                        "new_info": new_methods_map[method_name]
                    })

        # Compare services
        for svc_name in new_services:
            if svc_name not in old_services:
                changes["services"]["added"].append({"name": svc_name, "service": new_services[svc_name]})

        for svc_name in old_services:
            if svc_name not in new_services:
                changes["services"]["removed"].append({"name": svc_name, "service": old_services[svc_name]})

        for svc_name in old_services:
            if svc_name in new_services:
                diff = DeepDiff(old_services[svc_name], new_services[svc_name], ignore_order=True)
                if diff:
                    changes["services"]["modified"].append({
                        "name": svc_name,
                        "old_service": old_services[svc_name],
                        "new_service": new_services[svc_name],
                        "diff": diff
                    })

        # Compare enums
        old_enums = old_proto.get("enums", {})
        new_enums = new_proto.get("enums", {})

        for enum_name in new_enums:
            if enum_name not in old_enums:
                changes["enums"]["added"].append({"name": enum_name, "enum": new_enums[enum_name]})

        for enum_name in old_enums:
            if enum_name not in new_enums:
                changes["enums"]["removed"].append({"name": enum_name, "enum": old_enums[enum_name]})

        for enum_name in old_enums:
            if enum_name in new_enums:
                if old_enums[enum_name] != new_enums[enum_name]:
                    changes["enums"]["modified"].append({
                        "name": enum_name,
                        "old_enum": old_enums[enum_name],
                        "new_enum": new_enums[enum_name]
                    })

        return changes

    def _generate_text_diff(self, old_text: str, new_text: str) -> str:
        """Generate a simple text diff summary."""
        # Simple implementation - could be enhanced with proper diff algorithms
        if len(new_text) > len(old_text):
            return f"Content expanded by {len(new_text) - len(old_text)} characters"
        elif len(new_text) < len(old_text):
            return f"Content reduced by {len(old_text) - len(new_text)} characters"
        else:
            return "Content modified (same length)"

    def _generate_summary(self, comparison: Dict) -> Dict[str, Any]:
        """Generate summary statistics of changes."""
        md_changes = comparison["markdown_changes"]
        json_changes = comparison["json_changes"]

        return {
            "total_changes": (
                len(md_changes["requirements"]["added"])
                + len(md_changes["requirements"]["removed"])
                + len(md_changes["sections"]["added"])
                + len(md_changes["sections"]["removed"])
                + len(md_changes["sections"]["modified"])
                + len(json_changes["definitions"]["added"])
                + len(json_changes["definitions"]["removed"])
                + len(json_changes["definitions"]["modified"])
                + len(json_changes["methods"]["added"])
                + len(json_changes["methods"]["removed"])
            ),
            "requirement_changes": {
                "added": len(md_changes["requirements"]["added"]),
                "removed": len(md_changes["requirements"]["removed"]),
                "modified": len(md_changes["requirements"]["modified"]),
            },
            "section_changes": {
                "added": len(md_changes["sections"]["added"]),
                "removed": len(md_changes["sections"]["removed"]),
                "modified": len(md_changes["sections"]["modified"]),
            },
            "definition_changes": {
                "added": len(json_changes["definitions"]["added"]),
                "removed": len(json_changes["definitions"]["removed"]),
                "modified": len(json_changes["definitions"]["modified"]),
            },
            "method_changes": {
                "added": len(json_changes["methods"]["added"]),
                "removed": len(json_changes["methods"]["removed"]),
                "modified": len(json_changes["methods"]["modified"]),
            },
        }
