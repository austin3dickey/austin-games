import json
from typing import Any, List

from fastapi import WebSocket

# avoid circular dependency for type hint
Cards = None


class Communicator:
    """A class to manage communications with a websocket"""

    def __init__(self, websocket: WebSocket):
        """
        Args:
            websocket: The websocket for this player
        """
        self.websocket = websocket

    async def update_prompt(self, msg: str):
        """Update the prompt section of the client

        Args:
            msg: The message to send
        """
        print({"target": "prompt", "text": msg})
        await self.websocket.send_json({"target": "prompt", "text": msg})

    async def update_board(self, msg: str):
        """Update the board section of the client

        Args:
            msg: The message to send
        """
        print({"target": "board", "text": msg})
        await self.websocket.send_json({"target": "board", "text": msg})

    async def enable_vip_form(self):
        """Enable the VIP form"""
        print({"target": "enable_vip_form"})
        await self.websocket.send_json({"target": "enable_vip_form"})

    async def enable_card_form(self):
        """Enable the card form"""
        print({"target": "enable_card_form"})
        await self.websocket.send_json({"target": "enable_card_form"})

    async def populate_cards(self, cards: Cards):
        """Populate the card form

        Args:
            cards: The cards to populate it with
        """
        print(
            {
                "target": "populate_cards",
                "cards": cards.display_list(getattr(cards, "hidden_indexes", [])),
            }
        )
        await self.websocket.send_json(
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
