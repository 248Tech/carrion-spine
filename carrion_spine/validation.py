from __future__ import annotations

import configparser
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


@dataclass(slots=True, frozen=True)
class ValidationResult:
    ok: bool
    message: str
    profile_name: str | None = None


class Validator(ABC):
    """Base validation interface."""

    @abstractmethod
    def validate_bytes(self, content: bytes) -> ValidationResult:
        raise NotImplementedError


def _decode_text(content: bytes) -> str:
    return content.decode("utf-8", errors="strict")


class XMLFormatValidator(Validator):
    """Well-formed XML validator with basic XXE hardening."""

    def validate_bytes(self, content: bytes) -> ValidationResult:
        try:
            text = _decode_text(content)
            lower = text.lower()
            if "<!doctype" in lower or "<!entity" in lower:
                return ValidationResult(False, "DOCTYPE/ENTITY is not allowed.")
            ET.fromstring(text)
            return ValidationResult(True, "XML is well-formed.")
        except Exception as exc:  # Defensive: return parser failure reason.
            return ValidationResult(False, f"Invalid XML: {exc}")


class JSONFormatValidator(Validator):
    def validate_bytes(self, content: bytes) -> ValidationResult:
        try:
            json.loads(_decode_text(content))
            return ValidationResult(True, "JSON is parseable.")
        except Exception as exc:
            return ValidationResult(False, f"Invalid JSON: {exc}")


class YAMLFormatValidator(Validator):
    """YAML validator scaffold.

    TODO: Wire `yaml.safe_load` from PyYAML dependency if enabled.
    """

    def validate_bytes(self, content: bytes) -> ValidationResult:
        text = _decode_text(content).strip()
        if not text:
            return ValidationResult(False, "YAML cannot be empty.")
        # Minimal syntax sanity fallback when PyYAML is unavailable.
        if "\x00" in text:
            return ValidationResult(False, "YAML contains invalid null bytes.")
        return ValidationResult(True, "YAML basic checks passed.")


class INIFormatValidator(Validator):
    def validate_bytes(self, content: bytes) -> ValidationResult:
        parser = configparser.ConfigParser()
        try:
            parser.read_string(_decode_text(content))
            return ValidationResult(True, "INI is parseable.")
        except Exception as exc:
            return ValidationResult(False, f"Invalid INI: {exc}")


class FileProfile(ABC):
    """Config file profile contract for domain-specific validation."""

    name: str

    @abstractmethod
    def applies_to(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def validate(self, content: bytes) -> ValidationResult:
        raise NotImplementedError


@dataclass(slots=True, frozen=True)
class XMLNumericBound:
    xpath: str
    minimum: int
    maximum: int


class ServerConfigProfile(FileProfile):
    """Example profile for `serverconfig.xml`."""

    name = "serverconfig.xml"
    required_settings: tuple[str, ...] = (
        "ServerName",
        "ServerPort",
        "ServerMaxPlayerCount",
    )
    numeric_bounds: tuple[XMLNumericBound, ...] = (
        XMLNumericBound(".//property[@name='ServerPort']", 1, 65535),
        XMLNumericBound(".//property[@name='ServerMaxPlayerCount']", 1, 200),
    )

    def applies_to(self, path: Path) -> bool:
        return path.name.lower() == "serverconfig.xml"

    def validate(self, content: bytes) -> ValidationResult:
        fmt = XMLFormatValidator().validate_bytes(content)
        if not fmt.ok:
            return ValidationResult(False, fmt.message, self.name)
        root = ET.fromstring(_decode_text(content))

        seen = {node.get("name", "") for node in root.findall(".//property")}
        missing = [name for name in self.required_settings if name not in seen]
        if missing:
            return ValidationResult(False, f"Missing required settings: {', '.join(missing)}", self.name)

        for bound in self.numeric_bounds:
            node = root.find(bound.xpath)
            if node is None:
                continue
            value = node.get("value")
            if value is None or not value.isdigit():
                return ValidationResult(False, f"{bound.xpath} must be numeric.", self.name)
            ivalue = int(value)
            if not (bound.minimum <= ivalue <= bound.maximum):
                return ValidationResult(
                    False,
                    f"{bound.xpath} out of bounds ({bound.minimum}-{bound.maximum}).",
                    self.name,
                )
        return ValidationResult(True, "Profile checks passed.", self.name)


class ServerAdminProfile(FileProfile):
    name = "serveradmin.xml"

    def applies_to(self, path: Path) -> bool:
        return path.name.lower() == "serveradmin.xml"

    def validate(self, content: bytes) -> ValidationResult:
        fmt = XMLFormatValidator().validate_bytes(content)
        if not fmt.ok:
            return ValidationResult(False, fmt.message, self.name)
        root = ET.fromstring(_decode_text(content))
        if root.find(".//admins") is None:
            return ValidationResult(False, "Missing <admins> node.", self.name)
        return ValidationResult(True, "Profile checks passed.", self.name)


class ServerToolsProfile(FileProfile):
    name = "servertools-xml"

    def applies_to(self, path: Path) -> bool:
        return "servertools" in path.name.lower() and path.suffix.lower() == ".xml"

    def validate(self, content: bytes) -> ValidationResult:
        return XMLFormatValidator().validate_bytes(content)


class ValidationService:
    """Multi-layer validation: format + optional profile."""

    def __init__(self, profiles: list[FileProfile] | None = None) -> None:
        self.profiles = profiles or [ServerConfigProfile(), ServerAdminProfile(), ServerToolsProfile()]

    def validate(self, *, file_type: str, path: Path, content: bytes) -> ValidationResult:
        format_validator = self._format_validator(file_type)
        fmt_result = format_validator.validate_bytes(content)
        if not fmt_result.ok:
            return fmt_result

        for profile in self.profiles:
            if profile.applies_to(path):
                return profile.validate(content)
        return ValidationResult(True, "No profile checks required.")

    def _format_validator(self, file_type: str) -> Validator:
        mapping: dict[str, Validator] = {
            "xml": XMLFormatValidator(),
            "json": JSONFormatValidator(),
            "yaml": YAMLFormatValidator(),
            "ini": INIFormatValidator(),
        }
        validator = mapping.get(file_type.lower())
        if validator is None:
            raise ValueError(f"Unsupported file type: {file_type}")
        return validator


def reject_probably_binary(content: bytes) -> bool:
    """Reject binary-like uploads quickly."""
    if b"\x00" in content:
        return True
    sample = content[:1024]
    non_text = sum(1 for b in sample if b < 9 or (13 < b < 32))
    return bool(sample) and (non_text / len(sample)) > 0.30


def maybe_parse_json(content: bytes) -> Any:
    """TODO: helper for future semantic diffing."""
    return json.loads(_decode_text(content))

