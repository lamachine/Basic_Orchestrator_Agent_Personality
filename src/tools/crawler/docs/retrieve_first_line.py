import os
from supabase import create_client, Client
import httpx
from dotenv import load_dotenv

# Load environment variables first
load_dotenv(override=True)

def get_table_name() -> str:
    """Get the table name from environment variables."""
    return os.getenv("CURRENT_SOURCE_TABLE", "dev_docs_site_pages")

# Initialize Supabase client with local Docker setup
supabase: Client = create_client(
    "http://localhost:3001",  # Supabase Studio dashboard URL
    os.getenv("SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3MzczOTExMDAsImV4cCI6MjA1Mjc1MTEwMH0.Q5ZyhDUo6eMHN3sn27I01q-z-uHhSXf2XHRQzwjIpto"),
    options={
        "http_client": httpx.Client(verify=False),  # Disable SSL verification for local development
        "postgrest_client_timeout": 30  # Increase timeout
    }
)

def get_first_line():
    try:
        # Get the table name from environment variables
        table_name = get_table_name()
        
        print(f"Attempting to query table: {table_name}")
        
        # Query the first row from the table
        response = supabase.table(table_name).select("*").limit(1).execute()
        
        # Check if we got any data
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            return "No data found in the table"
            
    except Exception as e:
        print(f"Full error details: {str(e)}")
        return f"Error retrieving data: {str(e)}"

if __name__ == "__main__":
    # Get and print the first line
    result = get_first_line()
    print("First line of data:", result)
