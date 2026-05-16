#!/usr/bin/env python3
"""
Database Seeder for Configuration Migration
============================================
Seeds database with configuration data from YAML files.

Features:
- Idempotent: Safe to run multiple times
- Environment variable expansion
- Force mode for overwriting existing data
- Verification mode

Usage:
    python scripts/seed_database.py              # Seed all configs
    python scripts/seed_database.py --force      # Force overwrite
    python scripts/seed_database.py --verify     # Verify only
    python scripts/seed_database.py --only=system_configs  # Seed specific config
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from supabase import Client, create_client

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ConfigFlattener:
    """Flatten nested dictionaries for database storage."""

    @staticmethod
    def flatten(data: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
        """
        Flatten nested dictionary into dot-separated keys.

        Example:
            {"application": {"api": {"port": 8000}}}
            -> {"application.api.port": 8000}
        """
        items: list[tuple] = []

        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict) and not ConfigFlattener._is_config_object(value):
                # Recursively flatten nested dicts
                items.extend(ConfigFlattener.flatten(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))

        return dict(items)

    @staticmethod
    def _is_config_object(value: dict[str, Any]) -> bool:
        """Check if dict should be stored as JSON (not flattened further)."""
        # Store as JSON if it contains list/array values or is a complex config
        if any(isinstance(v, (list, dict)) for v in value.values()):
            return True
        return False

    @staticmethod
    def unflatten(data: dict[str, Any], sep: str = ".") -> dict[str, Any]:
        """
        Unflatten dot-separated keys into nested dictionary.

        Example:
            {"application.api.port": 8000}
            -> {"application": {"api": {"port": 8000}}}
        """
        result: dict[str, Any] = {}

        for key, value in data.items():
            parts = key.split(sep)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result


class EnvironmentExpander:
    """Expand environment variables in configuration values."""

    @staticmethod
    def expand(value: Any) -> Any:
        """
        Expand environment variables in strings.

        Example:
            "${OPENAI_API_KEY}" -> actual API key from environment
        """
        if isinstance(value, str):
            # Match ${VAR_NAME} pattern
            pattern = r"\$\{([A-Z_]+)\}"
            matches = re.findall(pattern, value)

            for var_name in matches:
                env_value = os.getenv(var_name, f"${{{var_name}}}")
                value = value.replace(f"${{{var_name}}}", env_value)

            return value
        elif isinstance(value, dict):
            return {k: EnvironmentExpander.expand(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [EnvironmentExpander.expand(item) for item in value]
        else:
            return value


class DatabaseSeeder:
    """Main database seeder class."""

    def __init__(self, supabase_url: str, supabase_key: str, force: bool = False):
        self.client: Client = create_client(supabase_url, supabase_key)
        self.force = force
        self.stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

    async def seed_all(self) -> None:
        """Seed all configuration types."""
        print("\n🌱 Starting database seeding...")
        print("=" * 60)

        await self.seed_system_configs()
        await self.seed_judge_llm_configs()
        await self.seed_target_ai_systems()
        await self.seed_evaluation_criteria()
        await self.seed_test_cases()

        print("\n" + "=" * 60)
        print("✅ Database seeding complete!")
        print(f"   Inserted: {self.stats['inserted']}")
        print(f"   Updated:  {self.stats['updated']}")
        print(f"   Skipped:  {self.stats['skipped']}")
        print(f"   Errors:   {self.stats['errors']}")

    async def seed_system_configs(self) -> None:
        """Seed system_configs table from system_defaults.yaml."""
        print("\n📝 Seeding system_configs...")

        yaml_path = PROJECT_ROOT / "config" / "system_defaults.yaml"
        if not yaml_path.exists():
            print(f"   ⚠️  YAML file not found: {yaml_path}")
            return

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Remove metadata and version fields
        data.pop("metadata", None)
        data.pop("version", None)
        data.pop("environments", None)  # Handle separately if needed

        # Flatten the configuration
        flattened = ConfigFlattener.flatten(data)

        # Insert each config entry
        for config_key, value in flattened.items():
            await self._upsert_system_config(config_key, value, "default")

        print(f"   ✅ Seeded {len(flattened)} system configs")

    async def seed_judge_llm_configs(self) -> None:
        """Seed judge_llm_configs table from judge_llm_configs.yaml."""
        print("\n📝 Seeding judge_llm_configs...")

        yaml_path = PROJECT_ROOT / "config" / "judge_llm_configs.yaml"
        if not yaml_path.exists():
            print(f"   ⚠️  YAML file not found: {yaml_path}")
            return

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        configs = data.get("configs", {})
        for name, config_data in configs.items():
            await self._upsert_judge_llm_config(name, config_data)

        print(f"   ✅ Seeded {len(configs)} judge LLM configs")

    async def seed_target_ai_systems(self) -> None:
        """Seed target_ai_systems table from target_ai_system.yaml."""
        print("\n📝 Seeding target_ai_systems...")

        yaml_path = PROJECT_ROOT / "config" / "target_ai_system.yaml"
        if not yaml_path.exists():
            print(f"   ⚠️  YAML file not found: {yaml_path}")
            return

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        system_config = data.get("target_ai_system", {})
        stub_config = data.get("stub_config", {})

        # Prepare data for database
        db_data = {
            "name": "default",
            "description": data.get("description", "Default target AI system"),
            "url": system_config.get("url", "http://localhost:8080/api/chat"),
            "timeout_seconds": system_config.get("timeout", 30),
            "headers": json.dumps(system_config.get("headers", {})),
            "request_config": json.dumps(system_config.get("request_format", {})),
            "response_config": json.dumps(system_config.get("response_parser", {})),
            "stub_enabled": stub_config.get("enabled", False),
            "stub_responses": json.dumps(stub_config.get("response_patterns", {})),
        }

        await self._upsert_target_ai_system(db_data)

        print("   ✅ Seeded target AI system config")

    async def seed_evaluation_criteria(self) -> None:
        """Seed evaluation_criteria table from rubric_criteria.yaml."""
        print("\n📝 Seeding evaluation_criteria...")

        yaml_path = PROJECT_ROOT / "config" / "test_cases" / "rubric_criteria.yaml"
        if not yaml_path.exists():
            print(f"   ⚠️  YAML file not found: {yaml_path}")
            return

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        db_data = {
            "name": "default",
            "version": data.get("version", "1.0"),
            "description": data.get("description", "Default evaluation criteria"),
            "hard_rules_enabled": data.get("hard_rules", {}).get("enabled", False),
            "hard_rules": json.dumps(data.get("hard_rules", {}).get("rules", [])),
            "soft_judge_criteria": json.dumps(data.get("soft_judge", {}).get("criteria", [])),
            "risk_score_config": json.dumps(data.get("risk_score_calculation", {})),
            "recommendation_templates": json.dumps(data.get("recommendation_templates", {})),
        }

        await self._upsert_evaluation_criteria(db_data)

        print("   ✅ Seeded evaluation criteria")

    async def seed_test_cases(self) -> None:
        """Seed test_cases table from YAML files."""
        print("\n📝 Seeding test_cases...")

        test_cases_dir = PROJECT_ROOT / "config" / "test_cases"
        yaml_files = list(test_cases_dir.rglob("*.yaml"))

        # Filter out rubric_criteria.yaml
        yaml_files = [f for f in yaml_files if f.name != "rubric_criteria.yaml"]

        count = 0
        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                # Handle both single test case and list of test cases
                test_cases = data if isinstance(data, list) else [data]

                for test_case in test_cases:
                    if "id" in test_case:  # Valid test case
                        await self._upsert_test_case(test_case)
                        count += 1
            except Exception as e:
                print(f"   ⚠️  Error processing {yaml_file.name}: {e}")

        print(f"   ✅ Seeded {count} test cases")

    # Helper methods for database operations

    async def _upsert_system_config(
        self, config_key: str, value: Any, environment: str = "default"
    ) -> None:
        """Upsert a single system config entry."""
        # Expand environment variables
        value = EnvironmentExpander.expand(value)

        # Determine value type
        value_type = self._get_value_type(value)

        # Convert value to string for storage
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        try:
            # Check if exists
            result = (
                self.client.table("system_configs")
                .select("id")
                .eq("config_key", config_key)
                .eq("environment", environment)
                .execute()
            )

            if result.data and not self.force:
                self.stats["skipped"] += 1
                return

            # Upsert
            data = {
                "config_key": config_key,
                "value": value_str,
                "value_type": value_type,
                "environment": environment,
                "is_active": True,
            }

            self.client.table("system_configs").upsert(data).execute()

            if result.data:
                self.stats["updated"] += 1
            else:
                self.stats["inserted"] += 1

        except Exception as e:
            print(f"   ❌ Error upserting {config_key}: {e}")
            self.stats["errors"] += 1

    async def _upsert_judge_llm_config(self, name: str, config_data: dict[str, Any]) -> None:
        """Upsert a judge LLM config entry."""
        try:
            model_config = config_data.get("model", {})
            params = config_data.get("parameters", {})

            data = {
                "name": name,
                "provider": model_config.get("provider", "openai"),
                "model_name": model_config.get("name", "gpt-4"),
                "model_version": model_config.get("version"),
                "temperature": params.get("temperature", 0.0),
                "seed": params.get("seed"),
                "prompt_name": "judge_evaluation_prompt",  # Default
                "prompt_version": "1.0.0",  # Default
                "enable_idempotency_check": False,
                "idempotency_runs": 3,
                "is_active": True,
            }

            self.client.table("judge_llm_configs").upsert(data).execute()
            self.stats["inserted"] += 1

        except Exception as e:
            print(f"   ❌ Error upserting judge config {name}: {e}")
            self.stats["errors"] += 1

    async def _upsert_target_ai_system(self, data: dict[str, Any]) -> None:
        """Upsert a target AI system config."""
        try:
            self.client.table("target_ai_systems").upsert(data).execute()
            self.stats["inserted"] += 1
        except Exception as e:
            print(f"   ❌ Error upserting target AI system: {e}")
            self.stats["errors"] += 1

    async def _upsert_evaluation_criteria(self, data: dict[str, Any]) -> None:
        """Upsert evaluation criteria config."""
        try:
            self.client.table("evaluation_criteria").upsert(data).execute()
            self.stats["inserted"] += 1
        except Exception as e:
            print(f"   ❌ Error upserting evaluation criteria: {e}")
            self.stats["errors"] += 1

    async def _upsert_test_case(self, test_case: dict[str, Any]) -> None:
        """Upsert a test case."""
        try:
            data = {
                "id": test_case["id"],
                "name": test_case["name"],
                "description": test_case["description"],
                "private_data_access": test_case.get("private_data_access", False),
                "untrusted_content_exposure": test_case.get("untrusted_content_exposure", False),
                "external_communication": test_case.get("external_communication", False),
                "input_text": test_case["input_text"],
                "expected_safe_behavior": test_case["expected_safe_behavior"],
                "risk_level": test_case["risk_level"],
            }

            self.client.table("test_cases").upsert(data).execute()
            self.stats["inserted"] += 1

        except Exception as e:
            print(f"   ❌ Error upserting test case {test_case.get('id')}: {e}")
            self.stats["errors"] += 1

    @staticmethod
    def _get_value_type(value: Any) -> str:
        """Determine the value type for database storage."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (dict, list)):
            return "json"
        else:
            return "string"

    async def verify(self) -> None:
        """Verify seeded data in database."""
        print("\n🔍 Verifying database contents...")
        print("=" * 60)

        tables = [
            "system_configs",
            "judge_llm_configs",
            "target_ai_systems",
            "evaluation_criteria",
            "test_cases",
        ]

        for table in tables:
            try:
                result = self.client.table(table).select("*", count="exact").execute()
                count = result.count if hasattr(result, "count") else len(result.data)
                print(f"   {table}: {count} rows")
            except Exception as e:
                print(f"   ❌ Error querying {table}: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Seed database with configuration data")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing data")
    parser.add_argument("--verify", action="store_true", help="Verify only (no seeding)")
    parser.add_argument(
        "--only",
        choices=[
            "system_configs",
            "judge_llm_configs",
            "target_ai_systems",
            "evaluation_criteria",
            "test_cases",
        ],
        help="Seed only specific configuration type",
    )

    args = parser.parse_args()

    # Load environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in environment")
        sys.exit(1)

    seeder = DatabaseSeeder(supabase_url, supabase_key, force=args.force)

    if args.verify:
        await seeder.verify()
    elif args.only:
        method = getattr(seeder, f"seed_{args.only}")
        await method()
    else:
        await seeder.seed_all()
        await seeder.verify()


if __name__ == "__main__":
    asyncio.run(main())
