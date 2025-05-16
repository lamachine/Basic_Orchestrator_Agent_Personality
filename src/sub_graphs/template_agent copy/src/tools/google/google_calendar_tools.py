"""
Google Calendar API Tools
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Union
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .credentials import CredentialsHandler, get_credentials
from googleapiclient.discovery import build
from functools import lru_cache
import pytz

@lru_cache(maxsize=1)
def get_calendar_service():
    """Get and cache the Calendar service."""
    creds = get_credentials()
    return build('calendar', 'v3', credentials=creds)

def list_events(max_results: int = 10, time_min: Optional[str] = None) -> str:
    """
    List upcoming events from the primary calendar.
    
    Args:
        max_results: Maximum number of events to return
        time_min: Start time in ISO format (default: now)
    
    Returns:
        str: JSON string containing event list
    """
    try:
        service = get_calendar_service()
        
        if not time_min:
            time_min = datetime.now(timezone.utc).isoformat()
        
        # Use 'primary' instead of email address for primary calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': start,
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'description': event.get('description', ''),
                'location': event.get('location', '')
            })
            
        return json.dumps(formatted_events, indent=2)
    except Exception as e:
        return f"Error listing events: {str(e)}"

def create_event(summary: str, start_time: str, end_time: str, 
                description: str = "", location: str = "") -> str:
    """
    Create a new calendar event.
    
    Args:
        summary: Event title
        start_time: Start time in ISO format
        end_time: End time in ISO format
        description: Event description
        location: Event location
    
    Returns:
        str: Success or error message
    """
    try:
        service = get_calendar_service()
        
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Los_Angeles',
            }
        }

        event = service.events().insert(
            calendarId='primary',  # Use primary instead of email
            body=event
        ).execute()

        return f"Event created successfully. Event ID: {event['id']}"
    except Exception as e:
        return f"Error creating event: {str(e)}"

def delete_event(event_id: str) -> str:
    """
    Delete a calendar event.
    
    Args:
        event_id: ID of the event to delete
    
    Returns:
        str: Success or error message
    """
    try:
        service = get_calendar_service()
        service.events().delete(
            calendarId='primary',  # Use primary instead of email
            eventId=event_id
        ).execute()
        return f"Event {event_id} deleted successfully"
    except Exception as e:
        return f"Error deleting event: {str(e)}"

def update_event(event_id: str, summary: Optional[str] = None, 
                start_time: Optional[str] = None, end_time: Optional[str] = None,
                description: Optional[str] = None, location: Optional[str] = None) -> str:
    """
    Update an existing calendar event.
    
    Args:
        event_id: ID of the event to update
        summary: New event title (optional)
        start_time: New start time in ISO format (optional)
        end_time: New end time in ISO format (optional)
        description: New event description (optional)
        location: New event location (optional)
    
    Returns:
        str: Success or error message
    """
    try:
        service = get_calendar_service()
        
        # Get existing event
        event = service.events().get(
            calendarId='primary',  # Use primary instead of email
            eventId=event_id
        ).execute()
        
        # Update fields if provided
        if summary:
            event['summary'] = summary
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if start_time:
            event['start']['dateTime'] = start_time
        if end_time:
            event['end']['dateTime'] = end_time

        updated_event = service.events().update(
            calendarId='primary',  # Use primary instead of email
            eventId=event_id,
            body=event
        ).execute()

        return f"Event updated successfully. Event ID: {updated_event['id']}"
    except Exception as e:
        return f"Error updating event: {str(e)}"

# ACL (Access Control) Functions
def manage_calendar_acl(action: str, calendar_id: str = 'primary', 
                       rule_id: Optional[str] = None, 
                       role: Optional[str] = None,
                       scope_type: Optional[str] = None,
                       scope_value: Optional[str] = None) -> str:
    """
    Manage calendar access control rules.
    
    Args:
        action: One of 'list', 'get', 'insert', 'delete', 'update'
        calendar_id: Calendar ID (default: primary)
        rule_id: ACL rule ID for specific operations
        role: Role for insert/update (reader, writer, owner)
        scope_type: Scope type for insert/update (user, group, domain)
        scope_value: Email or domain for the scope
    """
    try:
        service = get_calendar_service()
        
        if action == "list":
            acl = service.acl().list(calendarId=calendar_id).execute()
            return json.dumps(acl.get('items', []), indent=2)
            
        elif action == "get" and rule_id:
            rule = service.acl().get(
                calendarId=calendar_id,
                ruleId=rule_id
            ).execute()
            return json.dumps(rule, indent=2)
            
        elif action == "insert" and role and scope_type and scope_value:
            rule = {
                'role': role,
                'scope': {
                    'type': scope_type,
                    'value': scope_value
                }
            }
            result = service.acl().insert(
                calendarId=calendar_id,
                body=rule
            ).execute()
            return json.dumps(result, indent=2)
            
        elif action == "delete" and rule_id:
            service.acl().delete(
                calendarId=calendar_id,
                ruleId=rule_id
            ).execute()
            return f"ACL rule {rule_id} deleted successfully"
            
        elif action == "update" and rule_id and role:
            rule = service.acl().get(
                calendarId=calendar_id,
                ruleId=rule_id
            ).execute()
            rule['role'] = role
            result = service.acl().update(
                calendarId=calendar_id,
                ruleId=rule_id,
                body=rule
            ).execute()
            return json.dumps(result, indent=2)
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing ACL: {str(e)}"

# Calendar List Functions
def manage_calendar_list(action: str, calendar_id: Optional[str] = None,
                        summary: Optional[str] = None,
                        color_id: Optional[str] = None,
                        hidden: Optional[bool] = None) -> str:
    """
    Manage user's calendar list.
    
    Args:
        action: One of 'list', 'get', 'insert', 'delete', 'update'
        calendar_id: Calendar ID for specific operations
        summary: Calendar summary for updates
        color_id: Color ID for updates
        hidden: Whether to hide the calendar
    """
    try:
        service = get_calendar_service()
        
        if action == "list":
            calendars = service.calendarList().list().execute()
            return json.dumps(calendars.get('items', []), indent=2)
            
        elif action == "get" and calendar_id:
            calendar = service.calendarList().get(
                calendarId=calendar_id
            ).execute()
            return json.dumps(calendar, indent=2)
            
        elif action == "insert" and calendar_id:
            result = service.calendarList().insert(
                body={'id': calendar_id}
            ).execute()
            return json.dumps(result, indent=2)
            
        elif action == "delete" and calendar_id:
            service.calendarList().delete(
                calendarId=calendar_id
            ).execute()
            return f"Calendar {calendar_id} removed from list"
            
        elif action == "update" and calendar_id:
            calendar = service.calendarList().get(
                calendarId=calendar_id
            ).execute()
            if summary:
                calendar['summaryOverride'] = summary
            if color_id:
                calendar['colorId'] = color_id
            if hidden is not None:
                calendar['hidden'] = hidden
            result = service.calendarList().update(
                calendarId=calendar_id,
                body=calendar
            ).execute()
            return json.dumps(result, indent=2)
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing calendar list: {str(e)}"

# Calendar Management Functions
def manage_calendar(action: str, calendar_id: Optional[str] = None,
                   summary: Optional[str] = None,
                   description: Optional[str] = None,
                   time_zone: Optional[str] = None) -> str:
    """
    Manage calendars.
    
    Args:
        action: One of 'get', 'insert', 'delete', 'update', 'clear'
        calendar_id: Calendar ID for specific operations
        summary: Calendar summary for create/update
        description: Calendar description for create/update
        time_zone: Calendar time zone for create/update
    """
    try:
        service = get_calendar_service()
        
        if action == "get" and calendar_id:
            calendar = service.calendars().get(
                calendarId=calendar_id
            ).execute()
            return json.dumps(calendar, indent=2)
            
        elif action == "insert" and summary:
            calendar = {
                'summary': summary,
                'timeZone': time_zone or 'America/Los_Angeles'
            }
            if description:
                calendar['description'] = description
            result = service.calendars().insert(body=calendar).execute()
            return json.dumps(result, indent=2)
            
        elif action == "delete" and calendar_id:
            service.calendars().delete(calendarId=calendar_id).execute()
            return f"Calendar {calendar_id} deleted"
            
        elif action == "update" and calendar_id:
            calendar = service.calendars().get(
                calendarId=calendar_id
            ).execute()
            if summary:
                calendar['summary'] = summary
            if description:
                calendar['description'] = description
            if time_zone:
                calendar['timeZone'] = time_zone
            result = service.calendars().update(
                calendarId=calendar_id,
                body=calendar
            ).execute()
            return json.dumps(result, indent=2)
            
        elif action == "clear" and calendar_id:
            service.calendars().clear(calendarId=calendar_id).execute()
            return f"Calendar {calendar_id} cleared"
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing calendar: {str(e)}"

# Enhanced Event Functions
def quick_add_event(calendar_id: str, text: str) -> str:
    """
    Quickly add an event using natural language.
    
    Args:
        calendar_id: Calendar ID (use 'primary' for primary calendar)
        text: Natural language text describing the event
    """
    try:
        service = get_calendar_service()
        event = service.events().quickAdd(
            calendarId=calendar_id,
            text=text
        ).execute()
        return json.dumps(event, indent=2)
    except Exception as e:
        return f"Error quick adding event: {str(e)}"

def move_event(calendar_id: str, event_id: str, destination_id: str) -> str:
    """
    Move an event to a different calendar.
    
    Args:
        calendar_id: Source calendar ID
        event_id: Event to move
        destination_id: Destination calendar ID
    """
    try:
        service = get_calendar_service()
        event = service.events().move(
            calendarId=calendar_id,
            eventId=event_id,
            destination=destination_id
        ).execute()
        return json.dumps(event, indent=2)
    except Exception as e:
        return f"Error moving event: {str(e)}"

def get_event_instances(calendar_id: str, event_id: str, 
                       time_min: Optional[str] = None,
                       time_max: Optional[str] = None,
                       max_results: int = 10) -> str:
    """
    Get instances of a recurring event.
    
    Args:
        calendar_id: Calendar ID
        event_id: Recurring event ID
        time_min: Start time in ISO format
        time_max: End time in ISO format
        max_results: Maximum number of instances to return
    """
    try:
        service = get_calendar_service()
        instances = service.events().instances(
            calendarId=calendar_id,
            eventId=event_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results
        ).execute()
        return json.dumps(instances.get('items', []), indent=2)
    except Exception as e:
        return f"Error getting event instances: {str(e)}"

def import_event(calendar_id: str, ical_data: str) -> str:
    """
    Import an event from iCal data.
    
    Args:
        calendar_id: Calendar ID
        ical_data: iCal event data
    """
    try:
        service = get_calendar_service()
        event = service.events().import_(
            calendarId=calendar_id,
            body={'iCalUID': ical_data}
        ).execute()
        return json.dumps(event, indent=2)
    except Exception as e:
        return f"Error importing event: {str(e)}"

# Freebusy Functions
def query_freebusy(time_min: str, time_max: str, calendar_ids: List[str]) -> str:
    """
    Query free/busy information for calendars.
    
    Args:
        time_min: Start time in ISO format
        time_max: End time in ISO format
        calendar_ids: List of calendar IDs to query
    """
    try:
        service = get_calendar_service()
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in calendar_ids]
        }
        freebusy = service.freebusy().query(body=body).execute()
        return json.dumps(freebusy, indent=2)
    except Exception as e:
        return f"Error querying freebusy: {str(e)}"

# Settings Functions
def manage_settings(action: str, setting_id: Optional[str] = None) -> str:
    """
    Manage user settings.
    
    Args:
        action: One of 'list', 'get'
        setting_id: Setting ID for 'get' action
    """
    try:
        service = get_calendar_service()
        
        if action == "list":
            settings = service.settings().list().execute()
            return json.dumps(settings.get('items', []), indent=2)
            
        elif action == "get" and setting_id:
            setting = service.settings().get(
                setting=setting_id
            ).execute()
            return json.dumps(setting, indent=2)
            
        return "Invalid action or missing required parameters"
    except Exception as e:
        return f"Error managing settings: {str(e)}"

# Colors Function
def get_calendar_colors() -> str:
    """Get color definitions for calendars and events."""
    try:
        service = get_calendar_service()
        colors = service.colors().get().execute()
        return json.dumps(colors, indent=2)
    except Exception as e:
        return f"Error getting colors: {str(e)}"

# Test the functions if run directly
if __name__ == "__main__":
    print("\nTesting Calendar functions:")
    try:
        # Test listing calendars
        print("\n1. Testing manage_calendar_list():")
        calendars = manage_calendar_list(action="list")
        print(calendars)
        
        # Test getting calendar colors
        print("\n2. Testing get_calendar_colors():")
        colors = get_calendar_colors()
        print(colors)
        
        # Test listing events
        print("\n3. Testing list_events():")
        events = list_events(max_results=3)
        print(events)
        
        # Test creating an event for today at 7pm PST
        print("\n4. Testing create_event():")
        today = datetime.now()
        start_time = today.replace(hour=19, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        # Format times in ISO format with PST timezone
        start_iso = start_time.strftime("%Y-%m-%dT19:00:00-07:00")
        end_iso = end_time.strftime("%Y-%m-%dT20:00:00-07:00")
        
        event_result = create_event(
            summary="Test Event - Today at 7pm",
            start_time=start_iso,
            end_time=end_iso,
            description="This is a test event created by the calendar tool",
            location="Virtual"
        )
        print(event_result)
        
        # Extract event ID from the result
        event_id = event_result.split("Event ID: ")[-1].strip()
        
        # Test quick add event
        print("\n5. Testing quick_add_event():")
        quick_event = quick_add_event(
            calendar_id="primary",
            text="Meeting with Team tomorrow at 2pm for 1 hour"
        )
        print(quick_event)
        
        # Test updating the event
        print("\n6. Testing update_event():")
        update_result = update_event(
            event_id=event_id,
            summary="Updated Test Event",
            description="This event was updated by the test"
        )
        print(update_result)
        
        # Test querying free/busy
        print("\n7. Testing query_freebusy():")
        tomorrow = today + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
        
        freebusy = query_freebusy(
            time_min=tomorrow_start.isoformat() + "Z",
            time_max=tomorrow_end.isoformat() + "Z",
            calendar_ids=["primary"]
        )
        print(freebusy)
        
        # Test getting calendar settings
        print("\n8. Testing manage_settings():")
        settings = manage_settings(action="list")
        print(settings)
        
        # Test getting ACL rules
        print("\n9. Testing manage_calendar_acl():")
        acl_rules = manage_calendar_acl(action="list")
        print(acl_rules)
        
        # Test listing events again to verify changes
        print("\n10. Verifying event creation - listing events again:")
        updated_events = list_events(max_results=5)
        print(updated_events)
        
        # Clean up by deleting the test event
        print("\n11. Cleaning up - deleting test event:")
        delete_result = delete_event(event_id)
        print(delete_result)
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc()) 