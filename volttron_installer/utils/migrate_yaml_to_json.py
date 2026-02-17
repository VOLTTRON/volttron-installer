"""
Migration utility to convert existing YAML platform files to JSON format.
Run this once to migrate from the old YAML-per-platform structure to the new JSON storage.
"""
from pathlib import Path
import yaml
import json
from datetime import datetime
from typing import Optional

from loguru import logger

from volttron_installer.backend.models import PlatformDefinition
from volttron_installer.settings import get_settings


async def migrate_yaml_to_json(data_dir: Optional[Path] = None, backup: bool = True) -> dict:
    """
    Migrate YAML platform files to a single JSON file.
    
    Args:
        data_dir: Directory containing platform YAML files (defaults to settings data_dir)
        backup: Whether to keep YAML files as backup (default: True)
    
    Returns:
        dict with migration stats: {
            "migrated": int,
            "failed": list[str],
            "backup_path": Optional[str]
        }
    """
    if data_dir is None:
        data_dir = Path(get_settings().data_dir)
    
    data_dir = Path(data_dir)
    json_file = data_dir / "instances.json"
    
    stats = {
        "migrated": 0,
        "failed": [],
        "backup_path": None
    }
    
    # Check if JSON file already exists
    if json_file.exists():
        logger.warning(f"JSON file already exists at {json_file}. Migration skipped.")
        return stats
    
    # Find all YAML files
    yaml_files = []
    for platform_dir in data_dir.iterdir():
        if platform_dir.is_dir():
            yaml_file = platform_dir / f"{platform_dir.name}.yml"
            if yaml_file.exists():
                yaml_files.append(yaml_file)
    
    if not yaml_files:
        logger.info("No YAML files found to migrate.")
        # Create empty JSON file
        json_data = {
            "version": "1.0",
            "last_modified": datetime.utcnow().isoformat(),
            "instances": []
        }
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        return stats
    
    logger.info(f"Found {len(yaml_files)} YAML files to migrate")
    
    # Load and convert YAML files
    instances = []
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            # Validate by creating PlatformDefinition
            platform = PlatformDefinition(**yaml_data)
            instances.append(platform.model_dump())
            stats["migrated"] += 1
            logger.info(f"Migrated: {yaml_file}")
            
        except Exception as e:
            logger.error(f"Failed to migrate {yaml_file}: {e}")
            stats["failed"].append(str(yaml_file))
    
    # Create JSON file
    json_data = {
        "version": "1.0",
        "last_modified": datetime.utcnow().isoformat(),
        "instances": instances,
        "migration_info": {
            "migrated_at": datetime.utcnow().isoformat(),
            "source": "yaml_files",
            "yaml_count": len(yaml_files)
        }
    }
    
    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    logger.info(f"Created JSON file at {json_file}")
    
    # Handle backup/cleanup
    if backup:
        backup_dir = data_dir / f"yaml_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        
        for yaml_file in yaml_files:
            import shutil
            yaml_dir = yaml_file.parent
            backup_target = backup_dir / yaml_dir.name
            shutil.copytree(yaml_dir, backup_target)
        
        stats["backup_path"] = str(backup_dir)
        logger.info(f"Created backup at {backup_dir}")
    
    # Optionally remove YAML dirs (only if backup was created)
    # Uncomment the following lines to enable automatic cleanup:
    # if backup:
    #     for yaml_file in yaml_files:
    #         yaml_dir = yaml_file.parent
    #         shutil.rmtree(yaml_dir)
    #     logger.info("Removed original YAML directories")
    
    logger.info(f"Migration complete: {stats['migrated']} migrated, {len(stats['failed'])} failed")
    return stats


def run_migration():
    """Synchronous wrapper for running migration as a script."""
    import asyncio
    
    logger.info("Starting YAML to JSON migration...")
    stats = asyncio.run(migrate_yaml_to_json())
    
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"Successfully migrated: {stats['migrated']} platforms")
    
    if stats['failed']:
        print(f"Failed migrations: {len(stats['failed'])}")
        for failed_file in stats['failed']:
            print(f"  - {failed_file}")
    
    if stats['backup_path']:
        print(f"Backup created at: {stats['backup_path']}")
    
    print("="*60 + "\n")
    
    return stats


if __name__ == "__main__":
    run_migration()
