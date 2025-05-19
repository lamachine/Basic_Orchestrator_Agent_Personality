"""
Google People API Tools
"""

import json
import logging
import os
import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build

from .credentials import CredentialsHandler, get_credentials

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@lru_cache(maxsize=1)
def get_people_service():
    """Get and cache the Google People service."""
    creds = get_credentials()
    return build("people", "v1", credentials=creds)


# Contact Management Functions
def people_contact_create(
    given_name: str,
    family_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> str:
    """Create a new contact."""
    try:
        service = get_people_service()
        body = {
            "names": [
                {
                    "givenName": given_name,
                    "familyName": family_name if family_name else "",
                }
            ]
        }

        if email:
            body["emailAddresses"] = [{"value": email}]
        if phone:
            body["phoneNumbers"] = [{"value": phone}]

        result = service.people().createContact(body=body).execute()
        return f"Contact created successfully: {result.get('resourceName')}"
    except Exception as e:
        return f"Error creating contact: {str(e)}"


def people_contact_batch_create(contacts: List[Dict[str, Any]]) -> str:
    """Create multiple contacts at once."""
    try:
        service = get_people_service()
        body = {
            "contacts": [
                {
                    "names": [
                        {
                            "givenName": contact.get("given_name", ""),
                            "familyName": contact.get("family_name", ""),
                        }
                    ],
                    "emailAddresses": (
                        [{"value": contact["email"]}] if contact.get("email") else []
                    ),
                    "phoneNumbers": ([{"value": contact["phone"]}] if contact.get("phone") else []),
                }
                for contact in contacts
            ]
        }

        result = service.people().batchCreateContacts(body=body).execute()
        return f"Created {len(result.get('createdPeople', []))} contacts"
    except Exception as e:
        return f"Error batch creating contacts: {str(e)}"


def people_contact_batch_delete(resource_names: List[str]) -> str:
    """Delete multiple contacts."""
    try:
        service = get_people_service()
        result = (
            service.people().batchDeleteContacts(body={"resourceNames": resource_names}).execute()
        )
        return "Contacts deleted successfully"
    except Exception as e:
        return f"Error deleting contacts: {str(e)}"


def people_contact_batch_update(contacts: List[Dict[str, Any]]) -> str:
    """Update multiple contacts."""
    try:
        service = get_people_service()
        body = {
            "contacts": [
                {
                    "resourceName": contact["resource_name"],
                    "etag": contact.get("etag", ""),
                    "names": [
                        {
                            "givenName": contact.get("given_name", ""),
                            "familyName": contact.get("family_name", ""),
                        }
                    ],
                    "emailAddresses": (
                        [{"value": contact["email"]}] if contact.get("email") else []
                    ),
                    "phoneNumbers": ([{"value": contact["phone"]}] if contact.get("phone") else []),
                }
                for contact in contacts
            ],
            "updateMask": "names,emailAddresses,phoneNumbers",
        }

        result = service.people().batchUpdateContacts(body=body).execute()
        return f"Updated {len(result.get('updateResult', []))} contacts"
    except Exception as e:
        return f"Error updating contacts: {str(e)}"


# Contact Group Management Functions
def people_group_contact_create(group_name: str) -> str:
    """Create a new contact group."""
    try:
        service = get_people_service()
        result = (
            service.contactGroups().create(body={"contactGroup": {"name": group_name}}).execute()
        )
        return f"Contact group created successfully: {result.get('resourceName')}"
    except Exception as e:
        return f"Error creating contact group: {str(e)}"


def people_group_contact_get(resource_name: str) -> str:
    """Get a specific contact group."""
    try:
        service = get_people_service()
        result = service.contactGroups().get(resourceName=resource_name, maxMembers=1000).execute()
        return str(result)
    except Exception as e:
        return f"Error getting contact group: {str(e)}"


def people_group_contact_update(resource_name: str, new_name: str) -> str:
    """Update a contact group's name."""
    try:
        service = get_people_service()
        result = (
            service.contactGroups()
            .update(
                resourceName=resource_name,
                body={"contactGroup": {"name": new_name}, "updateGroupFields": "name"},
            )
            .execute()
        )
        return f"Contact group updated successfully: {result.get('resourceName')}"
    except Exception as e:
        return f"Error updating contact group: {str(e)}"


def people_group_contact_delete(resource_name: str) -> str:
    """Delete a contact group."""
    try:
        service = get_people_service()
        service.contactGroups().delete(resourceName=resource_name).execute()
        return "Contact group deleted successfully"
    except Exception as e:
        return f"Error deleting contact group: {str(e)}"


def people_group_contact_members(
    resource_name: str, member_resource_names: List[str], action: str = "add"
) -> str:
    """Modify members of a contact group."""
    try:
        service = get_people_service()
        if action.lower() == "add":
            result = (
                service.contactGroups()
                .members()
                .modify(
                    resourceName=resource_name,
                    body={"resourceNamesToAdd": member_resource_names},
                )
                .execute()
            )
            return f"Added {len(result.get('memberResourceNames', []))} members to group"
        elif action.lower() == "remove":
            result = (
                service.contactGroups()
                .members()
                .modify(
                    resourceName=resource_name,
                    body={"resourceNamesToRemove": member_resource_names},
                )
                .execute()
            )
            return f"Removed {len(member_resource_names)} members from group"
        else:
            return "Invalid action. Use 'add' or 'remove'"
    except Exception as e:
        return f"Error modifying group members: {str(e)}"


# Profile Information Functions
def people_profile_get(person_fields: str = "names,emailAddresses,phoneNumbers") -> str:
    """Get user's profile information."""
    try:
        service = get_people_service()
        result = (
            service.people().get(resourceName="people/me", personFields=person_fields).execute()
        )
        return str(result)
    except Exception as e:
        return f"Error getting profile: {str(e)}"


# Direct testing
if __name__ == "__main__":
    print("\nTesting Google People API:")
    try:
        # Test creating a contact
        print("\n1. Testing people_contact_create():")
        contact_result = people_contact_create(
            given_name="Test",
            family_name="Contact",
            email="test@example.com",
            phone="+1234567890",
        )
        print(contact_result)

        # Test getting profile
        print("\n2. Testing people_profile_get():")
        profile = people_profile_get()
        print(profile)

        # Test creating a group
        print("\n3. Testing people_group_contact_create():")
        group_result = people_group_contact_create("Test Group")
        print(group_result)

        print("\nAll tests completed successfully!")

    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback

        print("\nFull traceback:")
        print(traceback.format_exc())
