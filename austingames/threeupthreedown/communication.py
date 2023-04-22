import json
from typing import List, TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    from .cards import Cards


class Communicator:
    """A class to manage communications with a websocket"""

    def __init__(self, websocket: WebSocket):
        """
        Args:
            websocket: The websocket for this player
        """
        self.websocket = websocket

    async def send(self, stuff: dict):
        """Send something with debug printing."""
        print(f"sending {stuff}")
        await self.websocket.send_json(stuff)

    async def update_prompt(self, msg: str):
        """Update the prompt section of the client

        Args:
            msg: The message to send
        """
        await self.send({"target": "prompt", "text": msg})

    async def update_board(self, msg: str):
        """Update the board section of the client

        Args:
            msg: The message to send
        """
        await self.send({"target": "board", "text": msg})

    async def enable_vip_form(self):
        """Enable the VIP form"""
        await self.send({"target": "enable_vip_form"})

    async def enable_card_form(self):
        """Enable the card form"""
        await self.send({"target": "enable_card_form"})

    async def populate_cards(self, cards: "Cards"):
        """Populate the card form

        Args:
            cards: The cards to populate it with
        """
        await self.send(
            {
                "target": "populate_cards",
                "cards": cards.display_list(getattr(cards, "hidden_indexes", [])),
            }
        )

    async def receive_card_indexes(self) -> List[int]:
        """Receive card indexes from the client

        Returns:
            The list of card indexes
        """
        data = await self.websocket.receive_text()
        print(f"received {data}")
        return json.loads(f"[{data}]")
