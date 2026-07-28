import psycopg2
import json
import logging
import os
from routes.upsert import handle_upsert
from routes.pipeline import handle_pipeline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Use environment variables for RDS/PostgreSQL credentials
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
    )

def lambda_handler(event, context):
    command = event.get("command")
    conn = get_db_connection() # Connect to Postgres instead of local file
    
    try:
        if command == "upsert":
            result = handle_upsert(conn, event.get("file_paths", []))
            return {"statusCode": 200, "body": json.dumps(result)}
        elif command == "pipeline":
            result = handle_pipeline(conn, event.get("query"))
            return {"statusCode": 200, "body": json.dumps(result)}
        else:
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid command"})}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    finally:
        conn.close()
