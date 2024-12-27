import os
import sys
import logging
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from config import DATABASE_CONFIG

# Add the root directory (ShogiBotRP) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the connection pool
try:
    pool = ConnectionPool(
        conninfo=" ".join(f"{k}={v}" for k, v in DATABASE_CONFIG.items()),
        min_size=1,  # Minimum number of connections in the pool
        max_size=10,  # Maximum number of connections in the pool
    )
    logging.info("Database connection pool initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize the database connection pool: {e}")
    raise

def execute_query(query, params=None, guild_id=None, debug=False):
    """
    Executes a query that modifies the database (e.g., INSERT, UPDATE, DELETE).
    Includes optional `guild_id` parameter for multi-guild support.

    :param query: SQL query to execute.
    :param params: Query parameters.
    :param guild_id: Optional guild ID for multi-guild queries.
    :param debug: If True, logs the query and parameters for debugging.
    """
    if guild_id:
        params = tuple(params or ()) + (guild_id,)

    try:
        with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
            if debug:
                logging.debug(f"Executing query: {query} with params: {params}")
            cursor.execute(query, params)
            logging.info(f"Query executed successfully: {query}")
    except Exception as e:
        logging.error(f"Error executing query: {query} with params: {params}. Error: {e}")
        raise


def fetch_query(query, params=None, guild_id=None, debug=False):
    """
    Fetches data from the database (e.g., SELECT queries).
    Includes optional `guild_id` parameter for multi-guild support.

    :param query: SQL query to execute.
    :param params: Query parameters.
    :param guild_id: Optional guild ID for multi-guild queries.
    :param debug: If True, logs the query and parameters for debugging.
    :return: Query result.
    """
    if guild_id:
        params = tuple(params or ()) + (guild_id,)

    try:
        with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
            if debug:
                logging.debug(f"Executing query: {query} with params: {params}")
            cursor.execute(query, params)
            result = cursor.fetchall()
            logging.info(f"Query executed successfully: {query}")
            if debug:
                logging.debug(f"Query result: {result}")
            return result
    except Exception as e:
        logging.error(f"Error executing query: {query} with params: {params}. Error: {e}")
        raise

