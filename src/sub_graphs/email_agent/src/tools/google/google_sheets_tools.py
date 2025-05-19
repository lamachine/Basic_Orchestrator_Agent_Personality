"""
Google Sheets API Tools
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .credentials import CredentialsHandler, get_credentials


@lru_cache(maxsize=1)
def get_service():
    """Get and cache the Google Sheets service."""
    creds = get_credentials()
    return build("sheets", "v4", credentials=creds)


def create_spreadsheet(title: str) -> str:
    """
    Create a new spreadsheet.

    Args:
        title: The name of the new spreadsheet

    Returns:
        str: The ID of the created spreadsheet
    """
    try:
        service = get_service()
        spreadsheet = {"properties": {"title": title}}
        spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
        return f"Created spreadsheet with ID: {spreadsheet['spreadsheetId']}"
    except Exception as e:
        return f"Error creating spreadsheet: {str(e)}"


def read_range(spreadsheet_id: str, range_name: str) -> str:
    """
    Read values from a specified range.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_name: The A1 notation of the range to read

    Returns:
        str: The values in the range as a formatted string
    """
    try:
        service = get_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])

        if not values:
            return "No data found."

        # Format the data as a string
        return "\n".join(["\t".join(row) for row in values])
    except Exception as e:
        return f"Error reading range: {str(e)}"


def write_range(spreadsheet_id: str, range_name: str, values: List[List[str]]) -> str:
    """
    Write values to a specified range.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_name: The A1 notation of the range to write
        values: 2D array of values to write

    Returns:
        str: Confirmation message
    """
    try:
        service = get_service()
        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )
        return f"Updated {result.get('updatedCells')} cells"
    except Exception as e:
        return f"Error writing to range: {str(e)}"


def append_values(spreadsheet_id: str, range_name: str, values: List[List[str]]) -> str:
    """
    Append values to a specified range.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_name: The A1 notation of where to append
        values: 2D array of values to append

    Returns:
        str: Confirmation message
    """
    try:
        service = get_service()
        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        return f"Appended {len(values)} rows"
    except Exception as e:
        return f"Error appending values: {str(e)}"


def clear_range(spreadsheet_id: str, range_name: str) -> str:
    """
    Clear values in a specified range.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_name: The A1 notation of the range to clear

    Returns:
        str: Confirmation message
    """
    try:
        service = get_service()
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name, body={}
        ).execute()
        return f"Cleared range {range_name}"
    except Exception as e:
        return f"Error clearing range: {str(e)}"


def batch_update(spreadsheet_id: str, ranges: List[str], values: List[List[List[str]]]) -> str:
    """
    Update multiple ranges in a batch.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        ranges: List of A1 notations of ranges to update
        values: List of 2D arrays of values to write

    Returns:
        str: Confirmation message
    """
    try:
        service = get_service()
        data = []
        for range_name, value in zip(ranges, values):
            data.append({"range": range_name, "values": value})

        body = {"valueInputOption": "RAW", "data": data}

        result = (
            service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
            .execute()
        )
        return f"Updated {len(result.get('responses', []))} ranges"
    except Exception as e:
        return f"Error in batch update: {str(e)}"


def get_spreadsheet_info(spreadsheet_id: str) -> str:
    """
    Get information about a spreadsheet.

    Args:
        spreadsheet_id: The ID of the spreadsheet

    Returns:
        str: Formatted spreadsheet information
    """
    try:
        service = get_service()
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

        info = [
            f"Title: {spreadsheet['properties']['title']}",
            f"Locale: {spreadsheet['properties'].get('locale', 'Not set')}",
            f"Time zone: {spreadsheet['properties'].get('timeZone', 'Not set')}",
            "\nSheets:",
        ]

        for sheet in spreadsheet.get("sheets", []):
            props = sheet["properties"]
            info.append(f"- {props['title']} (ID: {props['sheetId']})")

        return "\n".join(info)
    except Exception as e:
        return f"Error getting spreadsheet info: {str(e)}"


# Direct testing
if __name__ == "__main__":
    print("\nTesting Google Sheets API:")
    try:
        # Test creating a spreadsheet
        result = create_spreadsheet("Test Spreadsheet")
        print(f"\nCreate spreadsheet result:\n{result}")

        # Extract spreadsheet ID from result
        spreadsheet_id = result.split(": ")[1]

        # Test writing values
        test_values = [
            ["Name", "Age", "City"],
            ["John", "30", "New York"],
            ["Jane", "25", "San Francisco"],
        ]
        print(f"\nWrite values result:\n{write_range(spreadsheet_id, 'Sheet1!A1:C3', test_values)}")

        # Test reading values
        print(f"\nRead values result:\n{read_range(spreadsheet_id, 'Sheet1!A1:C3')}")

        # Test appending values
        new_row = [["Bob", "35", "Chicago"]]
        print(f"\nAppend values result:\n{append_values(spreadsheet_id, 'Sheet1!A1', new_row)}")

        # Verify the append by reading all values
        print(f"\nVerifying appended data:\n{read_range(spreadsheet_id, 'Sheet1!A1:C4')}")

        # Test batch update
        batch_ranges = ["Sheet1!D1:D4"]
        batch_values = [[["Status"], ["Active"], ["Inactive"], ["Active"]]]
        print(f"\nBatch update result:\n{batch_update(spreadsheet_id, batch_ranges, batch_values)}")

        # Test clearing a range
        print(f"\nClear range result:\n{clear_range(spreadsheet_id, 'Sheet1!D1:D4')}")

        # Test getting spreadsheet info
        print(f"\nSpreadsheet info:\n{get_spreadsheet_info(spreadsheet_id)}")

        print("\nAll tests completed successfully!")

    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback

        print("\nFull traceback:")
        print(traceback.format_exc())
