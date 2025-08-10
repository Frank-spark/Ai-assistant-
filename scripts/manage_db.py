#!/usr/bin/env python3
"""Database management script for Reflex Executive Assistant."""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from src.config import get_settings
from src.storage.db import get_db_url

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_alembic_config():
    """Get Alembic configuration."""
    alembic_cfg = Config("alembic.ini")
    settings = get_settings()
    alembic_cfg.set_main_option("sqlalchemy.url", get_db_url(settings))
    return alembic_cfg


def check_database_connection():
    """Check if database is accessible."""
    try:
        settings = get_settings()
        engine = create_engine(get_db_url(settings))
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def init_database():
    """Initialize the database."""
    logger.info("Initializing database...")
    
    if not check_database_connection():
        logger.error("Cannot connect to database. Please check your configuration.")
        return False
    
    try:
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, "head")
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def create_migration(message):
    """Create a new migration."""
    logger.info(f"Creating migration: {message}")
    
    try:
        alembic_cfg = get_alembic_config()
        command.revision(alembic_cfg, message=message, autogenerate=True)
        logger.info("Migration created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        return False


def upgrade_database(revision="head"):
    """Upgrade database to specified revision."""
    logger.info(f"Upgrading database to revision: {revision}")
    
    try:
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, revision)
        logger.info("Database upgraded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to upgrade database: {e}")
        return False


def downgrade_database(revision):
    """Downgrade database to specified revision."""
    logger.info(f"Downgrading database to revision: {revision}")
    
    try:
        alembic_cfg = get_alembic_config()
        command.downgrade(alembic_cfg, revision)
        logger.info("Database downgraded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to downgrade database: {e}")
        return False


def show_migration_history():
    """Show migration history."""
    logger.info("Migration history:")
    
    try:
        alembic_cfg = get_alembic_config()
        command.history(alembic_cfg)
        return True
    except Exception as e:
        logger.error(f"Failed to show migration history: {e}")
        return False


def show_current_revision():
    """Show current database revision."""
    logger.info("Current database revision:")
    
    try:
        alembic_cfg = get_alembic_config()
        command.current(alembic_cfg)
        return True
    except Exception as e:
        logger.error(f"Failed to show current revision: {e}")
        return False


def stamp_revision(revision):
    """Stamp database with a revision without running migrations."""
    logger.info(f"Stamping database with revision: {revision}")
    
    try:
        alembic_cfg = get_alembic_config()
        command.stamp(alembic_cfg, revision)
        logger.info("Database stamped successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to stamp database: {e}")
        return False


def check_migrations():
    """Check for pending migrations."""
    logger.info("Checking for pending migrations...")
    
    try:
        alembic_cfg = get_alembic_cfg()
        command.check(alembic_cfg)
        logger.info("No pending migrations")
        return True
    except Exception as e:
        logger.info(f"Pending migrations found: {e}")
        return False


def reset_database():
    """Reset database (drop all tables and recreate)."""
    logger.warning("This will delete all data in the database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != "yes":
        logger.info("Database reset cancelled")
        return False
    
    logger.info("Resetting database...")
    
    try:
        # Downgrade to base
        alembic_cfg = get_alembic_config()
        command.downgrade(alembic_cfg, "base")
        
        # Upgrade to head
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database reset successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return False


def backup_database():
    """Create a database backup."""
    logger.info("Creating database backup...")
    
    try:
        settings = get_settings()
        # Extract database info from URL
        db_url = get_db_url(settings)
        
        # This is a simplified backup - in production you'd use pg_dump
        backup_file = f"backup_{settings.app_env}_{os.getpid()}.sql"
        
        logger.info(f"Backup would be saved to: {backup_file}")
        logger.info("For production backups, use: pg_dump -h host -U user -d database > backup.sql")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Database management for Reflex Executive Assistant")
    parser.add_argument("command", choices=[
        "init", "create", "upgrade", "downgrade", "history", "current", 
        "stamp", "check", "reset", "backup", "status"
    ], help="Database command to execute")
    
    parser.add_argument("--message", "-m", help="Migration message (for create command)")
    parser.add_argument("--revision", "-r", help="Revision for upgrade/downgrade/stamp commands")
    
    args = parser.parse_args()
    
    # Execute command
    success = False
    
    if args.command == "init":
        success = init_database()
    elif args.command == "create":
        if not args.message:
            logger.error("Migration message is required for create command")
            return 1
        success = create_migration(args.message)
    elif args.command == "upgrade":
        revision = args.revision or "head"
        success = upgrade_database(revision)
    elif args.command == "downgrade":
        if not args.revision:
            logger.error("Revision is required for downgrade command")
            return 1
        success = downgrade_database(args.revision)
    elif args.command == "history":
        success = show_migration_history()
    elif args.command == "current":
        success = show_current_revision()
    elif args.command == "stamp":
        if not args.revision:
            logger.error("Revision is required for stamp command")
            return 1
        success = stamp_revision(args.revision)
    elif args.command == "check":
        success = check_migrations()
    elif args.command == "reset":
        success = reset_database()
    elif args.command == "backup":
        success = backup_database()
    elif args.command == "status":
        success = check_database_connection()
        if success:
            show_current_revision()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 