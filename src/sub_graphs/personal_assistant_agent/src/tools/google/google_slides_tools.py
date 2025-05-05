import os
import sys
import time
from typing import Optional, List, Dict, Any, Union
from functools import lru_cache
from googleapiclient.discovery import build

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.credentials_handler import get_credentials

@lru_cache(maxsize=1)
def get_slides_service():
    """Get and cache the Google Slides service."""
    creds = get_credentials()
    return build('slides', 'v1', credentials=creds)

def create_presentation(title: str) -> str:
    """Create a new blank presentation."""
    try:
        service = get_slides_service()
        presentation = {
            'title': title
        }
        presentation = service.presentations().create(body=presentation).execute()
        return f"Created presentation with ID: {presentation.get('presentationId')}"
    except Exception as e:
        return f"Error creating presentation: {str(e)}"

def get_presentation(presentation_id: str) -> str:
    """Get presentation details."""
    try:
        service = get_slides_service()
        presentation = service.presentations().get(
            presentationId=presentation_id
        ).execute()
        return str(presentation)
    except Exception as e:
        return f"Error getting presentation: {str(e)}"

def create_slide(
    presentation_id: str,
    layout: str = "BLANK",
    insertion_index: Optional[int] = None
) -> str:
    """Create a new slide with specified layout."""
    try:
        requests = [{
            'createSlide': {
                'slideLayoutReference': {
                    'predefinedLayout': layout
                }
            }
        }]
        if insertion_index is not None:
            requests[0]['createSlide']['insertionIndex'] = insertion_index
            
        return batch_update(presentation_id, requests)
    except Exception as e:
        return f"Error creating slide: {str(e)}"

def add_text_box(
    presentation_id: str,
    page_id: str,
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
    font_size: Optional[float] = None,
    font_family: Optional[str] = None,
    color: Optional[Dict[str, float]] = None,
    bold: bool = False,
    italic: bool = False
) -> str:
    """Add a formatted text box to a slide."""
    try:
        text_box_id = f'textbox_{int(time.time())}'
        requests = [
            {
                'createShape': {
                    'objectId': text_box_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': page_id,
                        'size': {
                            'width': {'magnitude': width, 'unit': 'PT'},
                            'height': {'magnitude': height, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': x,
                            'translateY': y,
                            'unit': 'PT'
                        }
                    }
                }
            },
            {
                'insertText': {
                    'objectId': text_box_id,
                    'insertionIndex': 0,
                    'text': text
                }
            }
        ]

        # Add text style if specified
        style_request = {
            'updateTextStyle': {
                'objectId': text_box_id,
                'textRange': {
                    'type': 'ALL'
                },
                'style': {
                    'bold': bold,
                    'italic': italic
                },
                'fields': 'bold,italic'
            }
        }

        if font_size:
            style_request['updateTextStyle']['style']['fontSize'] = {
                'magnitude': font_size,
                'unit': 'PT'
            }
            style_request['updateTextStyle']['fields'] += ',fontSize'

        if font_family:
            style_request['updateTextStyle']['style']['fontFamily'] = font_family
            style_request['updateTextStyle']['fields'] += ',fontFamily'

        if color:
            style_request['updateTextStyle']['style']['foregroundColor'] = {
                'opaqueColor': {'rgbColor': color}
            }
            style_request['updateTextStyle']['fields'] += ',foregroundColor'

        requests.append(style_request)
        return batch_update(presentation_id, requests)
    except Exception as e:
        return f"Error adding text box: {str(e)}"

def add_shape(
    presentation_id: str,
    page_id: str,
    shape_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    color: Optional[Dict[str, float]] = None
) -> str:
    """Add a shape to a slide."""
    try:
        shape_id = f'shape_{int(time.time())}'
        requests = [{
            'createShape': {
                'objectId': shape_id,
                'shapeType': shape_type,
                'elementProperties': {
                    'pageObjectId': page_id,
                    'size': {
                        'width': {'magnitude': width, 'unit': 'PT'},
                        'height': {'magnitude': height, 'unit': 'PT'}
                    },
                    'transform': {
                        'scaleX': 1,
                        'scaleY': 1,
                        'translateX': x,
                        'translateY': y,
                        'unit': 'PT'
                    }
                }
            }
        }]

        if color:
            requests.append({
                'updateShapeProperties': {
                    'objectId': shape_id,
                    'fields': 'shapeBackgroundFill.solidFill.color',
                    'shapeProperties': {
                        'shapeBackgroundFill': {
                            'solidFill': {
                                'color': {
                                    'rgbColor': color
                                }
                            }
                        }
                    }
                }
            })

        return batch_update(presentation_id, requests)
    except Exception as e:
        return f"Error adding shape: {str(e)}"

def delete_object(presentation_id: str, object_id: str) -> str:
    """Delete an object from a slide."""
    try:
        requests = [{
            'deleteObject': {
                'objectId': object_id
            }
        }]
        return batch_update(presentation_id, requests)
    except Exception as e:
        return f"Error deleting object: {str(e)}"

def update_slide_background(
    presentation_id: str,
    page_id: str,
    color: Dict[str, float]
) -> str:
    """Update the background color of a slide."""
    try:
        requests = [{
            'updatePageProperties': {
                'objectId': page_id,
                'fields': 'pageBackgroundFill.solidFill.color',
                'pageProperties': {
                    'pageBackgroundFill': {
                        'solidFill': {
                            'color': {
                                'rgbColor': color
                            }
                        }
                    }
                }
            }
        }]
        return batch_update(presentation_id, requests)
    except Exception as e:
        return f"Error updating background: {str(e)}"

def batch_update(presentation_id: str, requests: List[Dict[str, Any]]) -> str:
    """Apply multiple updates to a presentation."""
    try:
        service = get_slides_service()
        body = {
            'requests': requests
        }
        response = service.presentations().batchUpdate(
            presentationId=presentation_id,
            body=body
        ).execute()
        return f"Successfully applied {len(response.get('replies', []))} updates"
    except Exception as e:
        return f"Error applying updates: {str(e)}"

def get_page_thumbnail(presentation_id: str, page_id: str) -> str:
    """Get a thumbnail URL for a specific page."""
    try:
        service = get_slides_service()
        thumbnail = service.presentations().pages().getThumbnail(
            presentationId=presentation_id,
            pageObjectId=page_id
        ).execute()
        return thumbnail.get('contentUrl', 'No thumbnail URL available')
    except Exception as e:
        return f"Error getting thumbnail: {str(e)}"

# Direct testing
if __name__ == "__main__":
    print("\nTesting Google Slides API:")
    try:
        # Test creating a presentation
        result = create_presentation("Test Presentation")
        print(f"\nCreate presentation result:\n{result}")
        
        # Extract presentation ID
        presentation_id = result.split(": ")[1]
        
        # Test getting presentation details
        print("\nPresentation details:")
        presentation = get_presentation(presentation_id)
        print(presentation)
        
        # Create a new slide
        print("\nCreating new slide:")
        slide_result = create_slide(presentation_id, "TITLE_AND_BODY")
        print(slide_result)
        
        # Get the first page ID
        pres_data = eval(presentation)
        if 'slides' in pres_data and len(pres_data['slides']) > 0:
            page_id = pres_data['slides'][0]['objectId']
            
            # Add a text box with formatting
            print("\nAdding formatted text box:")
            text_result = add_text_box(
                presentation_id=presentation_id,
                page_id=page_id,
                text="Hello, World!",
                x=100,
                y=100,
                width=300,
                height=100,
                font_size=24,
                font_family="Arial",
                color={'red': 0.5, 'green': 0.2, 'blue': 0.8},
                bold=True
            )
            print(text_result)
            
            # Add a shape
            print("\nAdding shape:")
            shape_result = add_shape(
                presentation_id=presentation_id,
                page_id=page_id,
                shape_type="RECTANGLE",
                x=50,
                y=50,
                width=200,
                height=100,
                color={'red': 0.9, 'green': 0.9, 'blue': 0.9}
            )
            print(shape_result)
            
            # Update slide background
            print("\nUpdating slide background:")
            bg_result = update_slide_background(
                presentation_id=presentation_id,
                page_id=page_id,
                color={'red': 0.95, 'green': 0.95, 'blue': 1.0}
            )
            print(bg_result)
            
            # Get page thumbnail
            print("\nGetting page thumbnail:")
            thumbnail = get_page_thumbnail(presentation_id, page_id)
            print(thumbnail)
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc()) 