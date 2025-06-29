#!/usr/bin/env python3
"""Run Alembic database migrations."""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def run_migrations():
    """Run all pending Alembic migrations."""
    try:
        from alembic import command
        from alembic.config import Config
        
        # Check if alembic.ini exists
        if not os.path.exists('alembic.ini'):
            print("❌ alembic.ini not found in current directory")
            print("Make sure you're running this from the backend directory")
            return False
            
        print("📋 Running Alembic database migrations...")
        
        # Load Alembic configuration
        alembic_cfg = Config('alembic.ini')
        
        # Show current revision
        try:
            current_rev = command.current(alembic_cfg)
            print(f"📍 Current database revision: {current_rev or 'None'}")
        except Exception as e:
            print(f"⚠️  Could not determine current revision: {e}")
        
        # Run migrations
        print("🔄 Upgrading database to latest revision...")
        command.upgrade(alembic_cfg, 'head')
        
        print("✅ Database migrations completed successfully!")
        
        # Show new current revision
        try:
            new_rev = command.current(alembic_cfg)
            print(f"📍 New database revision: {new_rev}")
        except Exception:
            pass
            
        return True
        
    except ImportError as e:
        print("❌ Alembic not installed. Please install it first:")
        print("   pip install alembic")
        print("   Or if using a virtual environment:")
        print("   python -m pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("\nThis could happen if:")
        print("- Database is not running")
        print("- Database connection settings are incorrect")
        print("- Migration files have syntax errors")
        print("- Migration was already applied")
        return False

def show_migration_status():
    """Show the current migration status."""
    try:
        from alembic import command
        from alembic.config import Config
        
        if not os.path.exists('alembic.ini'):
            print("❌ alembic.ini not found")
            return
            
        alembic_cfg = Config('alembic.ini')
        
        print("📋 Migration Status:")
        print("-" * 50)
        
        # Show history
        command.history(alembic_cfg)
        
    except Exception as e:
        print(f"❌ Could not show migration status: {e}")

def create_new_migration(message):
    """Create a new migration file."""
    try:
        from alembic import command
        from alembic.config import Config
        
        if not os.path.exists('alembic.ini'):
            print("❌ alembic.ini not found")
            return False
            
        alembic_cfg = Config('alembic.ini')
        
        print(f"📝 Creating new migration: {message}")
        command.revision(alembic_cfg, message=message, autogenerate=True)
        
        print("✅ Migration file created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Alembic migration helper")
    parser.add_argument("action", nargs="?", default="upgrade", 
                       choices=["upgrade", "status", "create"],
                       help="Action to perform (default: upgrade)")
    parser.add_argument("--message", "-m", help="Message for new migration")
    
    args = parser.parse_args()
    
    if args.action == "upgrade":
        success = run_migrations()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        show_migration_status()
    elif args.action == "create":
        if not args.message:
            print("❌ Please provide a message with --message")
            sys.exit(1)
        success = create_new_migration(args.message)
        sys.exit(0 if success else 1)