"""
Supabase Client Module
=====================

This module provides a unified interface for interacting with the Supabase database.
It handles all database operations including connections, batch operations, and data retrieval.

Key Features:
    - Supabase client initialization and connection management
    - Batch upsert operations with automatic retry and error handling
    - Timestamp and record retrieval functions
    - Logging of all database operations

Dependencies:
    - supabase-py: For Supabase database interactions
    - python-dotenv: For environment variable management
    - logging: For operation logging

Environment Variables Required:
    - SUPABASE_URL: URL of the Supabase instance
    - SUPABASE_KEY: API key for Supabase authentication

Usage:
    from src.supabase_client import get_supabase_client, batch_upsert

    # Get client instance
    client = get_supabase_client()

    # Batch upsert records
    records = [{"bet_id": "123", "data": "value"}, ...]
    batch_upsert("table_name", records)

Author: highlyprofitable108
Created: March 2025
"""

import time
import sys
import os
from typing import List, Dict, Any
from supabase import create_client, Client

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import from new consolidated modules
try:
    # Try relative imports (when used as a module)
    from .config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_LOG_FILE, setup_logging
except ImportError:
    # Fall back to absolute imports (when run directly)
    from src.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_LOG_FILE, setup_logging

# Initialize logger
logger = setup_logging(SUPABASE_LOG_FILE, "supabase")

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.
    
    Returns:
        Client: A Supabase client instance.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and key must be set in environment variables")
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {e}")
        raise

def batch_upsert(table: str, records: List[Dict[str, Any]], on_conflict="betid_timestamp", batch_size=100):
    """
    Upsert records in batches to avoid API limitations.
    
    Args:
        table: Table name
        records: List of record dictionaries
        on_conflict: Column to use for conflict resolution
        batch_size: Number of records per batch
        
    Returns:
        int: Number of successful batches
    """
    if not records:
        logger.info("No records to upsert")
        return 0
        
    # Connect to Supabase
    supabase_client = get_supabase_client()
    
    logger.info(f"Upserting {len(records)} records to {table} in batches of {batch_size}")
    
    # Process data in batches
    successful_batches = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            supabase_client.table(table).upsert(
                batch,
                on_conflict=on_conflict
            ).execute()
            successful_batches += 1
            logger.info(f"Successfully upserted batch {successful_batches} ({len(batch)} records)")
            # Small pause to prevent rate limiting
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error upserting batch to Supabase: {e}")
            
            # Attempt individual upserts on failure
            for record in batch:
                try:
                    supabase_client.table(table).upsert(
                        [record],
                        on_conflict=on_conflict
                    ).execute()
                    logger.info("Successfully upserted individual record")
                except Exception as e_inner:
                    logger.error(f"Error upserting individual record: {e_inner}")
    
    logger.info(f"Completed upserting {len(records)} records in {successful_batches} batches")
    return successful_batches 

def get_most_recent_timestamp() -> str:
    """
    Get the most recent timestamp from the betting_data table.
    
    Returns:
        str: The most recent timestamp in ISO format, or None if no records exist
    """
    try:
        supabase_client = get_supabase_client()
        response = (
            supabase_client.table('betting_data')
            .select('timestamp')
            .order('timestamp', desc=True)
            .limit(1)
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            return response.data[0]['timestamp']
        return None
    except Exception as e:
        logger.error(f"Error getting most recent timestamp: {e}")
        return None