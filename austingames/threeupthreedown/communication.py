from fastapi import WebSocket


async def update_prompt(msg: str, websocket: WebSocket):
    """Update the prompt section of the client
    
    Args:
        msg: The message to send
        websocket: The websocket to send it over
    """
    await websocket.send_json({"target": "prompt", "text": msg})

async def update_board(msg: str, websocket: WebSocket):
    """Update the board section of the client
    
    Args:
        msg: The message to send
        websocket: The websocket to send it over
    """
    await websocket.send_json({"target": "board", "text": msg})

async def enable_form(websocket: WebSocket):
    """Enable the form
    
    Args:
        websocket: The websocket to send the command over
    """
    await websocket.send_json({"target": "enable_form"})

async def disable_form(websocket: WebSocket):
    """Disable the form
    
    Args:
        websocket: The websocket to send the command over
    """
    await websocket.send_json({"target": "disable_form"})
