"""
Database configuration for Supabase PostgreSQL connection.

Loads connection details from environment variables for security.
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class DatabaseConfig:
    """
    Database configuration manager.
    """
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Supabase connection details
        self.host = os.getenv('SUPABASE_DB_HOST', 'localhost')
        self.port = os.getenv('SUPABASE_DB_PORT', '5432')
        self.database = os.getenv('SUPABASE_DB_NAME', 'postgres')
        self.user = os.getenv('SUPABASE_DB_USER', 'postgres')
        self.password = os.getenv('SUPABASE_DB_PASSWORD', '')
        
        # SSL mode (Supabase requires SSL)
        self.sslmode = os.getenv('SUPABASE_DB_SSLMODE', 'require')
        
        # Optional: Direct connection string override
        self.connection_string = os.getenv('DATABASE_URL', None)
    
    def get_connection_string(self) -> str:
        """
        Get PostgreSQL connection string.
        
        Returns:
            Connection string for psycopg2
        """
        # If direct connection string is provided, use it
        if self.connection_string:
            return self.connection_string
        
        # Otherwise, build from components
        conn_str = (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={self.user} "
            f"password={self.password} "
            f"sslmode={self.sslmode}"
        )
        
        return conn_str
    
    def validate(self) -> bool:
        """
        Validate that required configuration is present.
        
        Returns:
            True if configuration is valid
        """
        if self.connection_string:
            return True
        
        required = [self.host, self.database, self.user, self.password]
        return all(required)
    
    def print_info(self, hide_password: bool = True) -> None:
        """
        Print configuration information.
        
        Args:
            hide_password: Whether to hide password in output
        """
        print("Database Configuration:")
        print(f"  Host: {self.host}")
        print(f"  Port: {self.port}")
        print(f"  Database: {self.database}")
        print(f"  User: {self.user}")
        
        if hide_password:
            print(f"  Password: {'*' * len(self.password) if self.password else '(not set)'}")
        else:
            print(f"  Password: {self.password}")
        
        print(f"  SSL Mode: {self.sslmode}")


# Global config instance
_config = None


def get_config() -> DatabaseConfig:
    """
    Get the global database configuration instance.
    
    Returns:
        DatabaseConfig instance
    """
    global _config
    if _config is None:
        _config = DatabaseConfig()
    return _config


def get_connection_string() -> str:
    """
    Get the database connection string.
    
    Returns:
        Connection string for psycopg2
    """
    config = get_config()
    
    if not config.validate():
        raise ValueError(
            "Database configuration is incomplete. "
            "Please set environment variables: "
            "SUPABASE_DB_HOST, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD"
        )
    
    return config.get_connection_string()


# Example .env file template
ENV_TEMPLATE = """
# Supabase PostgreSQL Configuration
# Copy this to .env and fill in your details

# Supabase connection details
SUPABASE_DB_HOST=your-project.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password-here
SUPABASE_DB_SSLMODE=require

# Alternatively, use a single connection string
# DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
"""


def create_env_template(output_path: str = ".env.example") -> None:
    """
    Create a .env template file.
    
    Args:
        output_path: Path to save the template
    """
    with open(output_path, 'w') as f:
        f.write(ENV_TEMPLATE)
    
    print(f"✓ Created environment template: {output_path}")
    print("Copy this to .env and fill in your Supabase details.")


if __name__ == "__main__":
    # Test configuration
    config = get_config()
    config.print_info()
    
    if config.validate():
        print("\n✓ Configuration is valid")
        print(f"\nConnection string: {config.get_connection_string()[:50]}...")
    else:
        print("\n❌ Configuration is incomplete")
        print("\nCreate a .env file with:")
        print(ENV_TEMPLATE)
