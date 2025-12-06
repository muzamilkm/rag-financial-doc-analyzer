"""
Initialize database schema for pgvector storage.

Simple script to create the financial_documents table and indexes
in your Supabase PostgreSQL database.

Usage:
    python init_database.py [--recreate]

Options:
    --recreate: Drop existing schema and recreate from scratch
"""

import sys
import psycopg2
from core.database.config import get_connection_string, get_config
from core.database.schema import DatabaseSchema


def main():
    """Initialize database schema."""
    
    # Check for recreate flag
    recreate = '--recreate' in sys.argv or '--force' in sys.argv
    
    print("=" * 80)
    print("Database Schema Initialization")
    print("=" * 80)
    
    # Validate configuration
    config = get_config()
    
    print("\n📋 Configuration:")
    config.print_info()
    
    if not config.validate():
        print("\n❌ Error: Database configuration is incomplete")
        print("Please create a .env file with your Supabase credentials.")
        print("\nExample .env file:")
        print("-" * 40)
        print("SUPABASE_DB_HOST=db.xxxxx.supabase.co")
        print("SUPABASE_DB_NAME=postgres")
        print("SUPABASE_DB_USER=postgres")
        print("SUPABASE_DB_PASSWORD=your-password")
        print("SUPABASE_DB_SSLMODE=require")
        return 1
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    try:
        conn = psycopg2.connect(get_connection_string())
        print("   ✓ Connected successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return 1
    
    # Create schema
    print("\n🗄️  Initializing schema...")
    if recreate:
        print("   ⚠️  Warning: Dropping existing schema and recreating")
        confirm = input("   Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("   Cancelled")
            return 0
    
    try:
        schema = DatabaseSchema(conn)
        schema.create_schema(drop_existing=recreate)
        print("   ✓ Schema created successfully")
    except Exception as e:
        print(f"   ❌ Schema creation failed: {e}")
        conn.close()
        return 1
    
    # Show statistics
    print("\n📊 Database Statistics:")
    try:
        stats = schema.get_table_stats()
        print(f"   Total documents: {stats['total_documents']:,}")
        print(f"   Text chunks: {stats['text_chunks']:,}")
        print(f"   Table rows: {stats['table_rows']:,}")
        
        if stats['companies']:
            print(f"\n   Companies: {', '.join(stats['companies'])}")
        else:
            print(f"\n   Companies: (none yet)")
            
    except Exception as e:
        print(f"   ⚠️  Could not fetch statistics: {e}")
    
    # Close connection
    conn.close()
    
    print("\n" + "=" * 80)
    print("✓ Database initialization completed successfully!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Run: python example_complete_pipeline.py")
    print("  2. Insert your embeddings into the database")
    print("  3. Perform similarity searches")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
