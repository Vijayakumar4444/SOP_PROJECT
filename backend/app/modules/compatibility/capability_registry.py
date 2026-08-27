from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json

from .models import MissingPhase1MetadataError, VariableCapability


ROOT = Path(__file__).resolve().parents[4]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _int_year(value: str) -> list[int]:
    years = []
    for part in str(value or "").replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            years.append(int(part))
        elif "-" in part and part[:4].isdigit():
            years.append(int(part[:4]))
    return sorted(set(years))


class DataCapabilityRegistryBuilder:
    def __init__(self, root: Path = ROOT):
        self.root = root

    def build(self) -> dict[str, Any]:
        metadata_path = self.root / "data/reference/template_metadata.json"
        reference_path = self.root / "data/processed/reference_template.csv"
        missingness_path = self.root / "data/reports/missingness_report.csv"
        source_path = self.root / "data/source_registry.csv"
        variable_path = self.root / "data/reference/variable_dictionary.csv"
        if not metadata_path.exists() or not reference_path.exists():
            raise MissingPhase1MetadataError("Phase 1 metadata/reference template is missing.")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        missingness = {row["variable"]: row for row in _read_csv(missingness_path)}
        sources = {row["source_id"]: row for row in _read_csv(source_path)}
        variables = _read_csv(variable_path)

        with reference_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            sample_rows = []
            row_count = 0
            districts = set()
            urban_rural = set()
            primary_sources = set()
            for row in reader:
                row_count += 1
                if len(sample_rows) < 50:
                    sample_rows.append(row)
                if row.get("district"):
                    districts.add(row["district"])
                if row.get("urban_rural"):
                    urban_rural.add(row["urban_rural"])
                if row.get("primary_source_id"):
                    primary_sources.add(row["primary_source_id"])

        capabilities: dict[str, dict[str, Any]] = {}
        for var in variables:
            name = var.get("canonical_variable", "")
            if not name:
                continue
            miss = missingness.get(name, {})
            missing_pct = float(miss.get("missing_percentage") or 0)
            non_null = 1.0 - missing_pct
            row_level = name in headers
            source_ids = sorted(primary_sources) if row_level else []
            reference_years = [2024] if row_level else _int_year(var.get("reference_year", ""))
            capabilities[name] = VariableCapability(
                canonical_name=name,
                level=var.get("level") or ("PERSON" if row_level else "STATE"),
                data_type=var.get("data_type", ""),
                unit=var.get("unit", ""),
                sources=source_ids,
                reference_years=reference_years,
                non_null_percentage=round(non_null * 100, 4),
                missing_percentage=round(missing_pct * 100, 4),
                geographic_resolution=self._geo_resolution(name, row_level),
                quality_flag="A" if row_level and source_ids else var.get("quality_flag", ""),
                source_variables=var.get("source_variables", ""),
                lineage=[self._lineage(name, source_ids, sources)] if source_ids else [],
                aggregate_only=not row_level,
                notes=var.get("notes", ""),
            ).__dict__

        self._add_aggregate_capabilities(capabilities, sources)
        registry = {
            "data_foundation_version": metadata.get("version", "UNKNOWN"),
            "state": metadata.get("state", "Tamil Nadu"),
            "reference_records": row_count,
            "available_source_records": metadata.get("available_plfs_tamil_nadu_source_rows", row_count),
            "sources": sources,
            "district_count": len(districts),
            "urban_rural_values": sorted(urban_rural),
            "variables": capabilities,
            "joint_datasets": {
                "reference_template": {
                    "source_id": "SRC_PLFS_2024_OPENCITY_PUBLIC_MIRROR",
                    "variables": headers,
                    "row_count": row_count,
                    "reference_year": 2024,
                    "district_count": len(districts),
                }
            },
            "known_limitations": metadata.get("limitations", []),
        }
        out = self.root / "data/metadata/data_capability_registry.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
        return registry

    def _lineage(self, variable: str, source_ids: list[str], sources: dict[str, dict[str, str]]) -> dict[str, str]:
        source_id = source_ids[0] if source_ids else ""
        source = sources.get(source_id, {})
        return {
            "canonical_variable": variable,
            "processed_variable": variable,
            "source_variable": "PLFS harmonized source field; see data layout workbook",
            "source_dataset": source.get("dataset_name", source_id),
            "publisher": source.get("publisher", ""),
        }

    def _geo_resolution(self, name: str, row_level: bool) -> list[str]:
        if not row_level:
            return ["STATE"]
        if name in {"district", "district_code"}:
            return ["DISTRICT"]
        if name == "urban_rural":
            return ["URBAN_RURAL"]
        return ["STATE", "DISTRICT", "URBAN_RURAL"]

    def _add_aggregate_capabilities(self, capabilities: dict[str, dict[str, Any]], sources: dict[str, dict[str, str]]) -> None:
        aggregate_defs = {
            "scheduled_caste_indicator": ("SRC_TN_DES_GLANCE_2023_24", 2011, "STATE"),
            "scheduled_tribe_indicator": ("SRC_TN_DES_GLANCE_2023_24", 2011, "STATE"),
            "worker_category": ("SRC_TN_DES_GLANCE_2023_24", 2011, "STATE"),
            "literacy_rate": ("SRC_TN_DES_GLANCE_2023_24", 2011, "STATE"),
            "health_insurance": ("SRC_NFHS5_IIPS_2019_21", 2021, "STATE"),
            "disability_status": ("SRC_NFHS5_IIPS_2019_21", 2021, "STATE"),
        }
        for name, (source_id, year, geo) in aggregate_defs.items():
            if name in capabilities and not capabilities[name].get("sources"):
                continue
            source = sources.get(source_id, {})
            capabilities.setdefault(name, {
                "canonical_name": name,
                "level": geo,
                "data_type": "aggregate",
                "unit": "",
                "sources": [source_id],
                "reference_years": [year],
                "non_null_percentage": 100.0 if source.get("access_status") != "MANUAL_DOWNLOAD_REQUIRED" else 0.0,
                "missing_percentage": 0.0 if source.get("access_status") != "MANUAL_DOWNLOAD_REQUIRED" else 100.0,
                "geographic_resolution": [geo],
                "quality_flag": "B" if source.get("access_status") != "MANUAL_DOWNLOAD_REQUIRED" else "",
                "source_variables": "aggregate publication/catalog indicator",
                "lineage": [{
                    "canonical_variable": name,
                    "processed_variable": "aggregate calibration/provenance table",
                    "source_variable": name,
                    "source_dataset": source.get("dataset_name", source_id),
                    "publisher": source.get("publisher", ""),
                }],
                "aggregate_only": True,
                "notes": "Aggregate-only capability; not usable for person-level eligibility.",
            })
