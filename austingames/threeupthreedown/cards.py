import asyncio
import random
from typing import List, Optional, Union

from .communication import Communicator


SMALL = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3, 10: 3, "C": 3, "C+1": 2, "C+2": 1}
MEDIUM = {1: 5, 2: 5, 3: 5, 4: 5, 5: 5, 6: 5, 7: 5, 8: 5, 9: 5, 10: 5, "C": 5, "C+1": 4, "C+2": 1}
LARGE = {1: 7, 2: 7, 7: 7, 4: 7, 5: 7, 6: 7, 7: 7, 8: 7, 9: 7, 10: 7, "C": 7, "C+1": 6, "C+2": 1}


class Card:
    """A card."""

    def __init__(self, value: Union[int, str]):
        """
        Args:
            value: The value of the card.
        """
        self.value = value

    @property
    def is_clear(self) -> bool:
        """Is this card a Clear card?"""
        return isinstance(self.value, str)

    @property
    def extra_turns(self) -> int:
        """How many extra turns this card gives you"""
        if self.value == "C+2":
            return 2
        elif self.value == "C+1":
            return 1
        else:
            return 0

    def __ge__(self, other: "Card") -> bool:
        try:
            return self.value >= other.value
        except TypeError:
            # clear cards are always higher
            return self.is_clear

    def __lt__(self, other: "Card") -> bool:
        try:
            return self.value < other.value
        except TypeError:
            # clear cards are always higher
            return other.is_clear

    def __eq__(self, other: "Card") -> bool:
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __str__(self) -> str:
        return f"[\u00A0{self.value}\u00A0]"


class Cards(list):
    """A pile of cards."""

    async def choose(
        self,
        comms: Communicator,
        prompt: str,
        min_num: int,
        max_num: int,
        playing_faceup: bool,
        min_card: Optional[Card],
    ) -> Optional["Cards"]:
        """Ask for the cards to choose and validate they work before popping them out of the pile.

        Args:
            comms: The player's Communicator
            prompt: A prompt for the cards to choose
            min_num: The minimum number of cards to choose
            max_num: The maximum number of cards to choose
            playing_faceup: Whether we're playing from a faceup hand
            min_card: The minimum possible card to play, or None if any card will do

        Returns:
            Cards that were chosen, or None if the player must pick up the discard pile
        """
        # Exit early if nothing is playable
        if min_card and playing_faceup and all(card < min_card for card in self):
            await comms.update_prompt(
                "Uh-oh, none of your cards are playable! Picking up the discard pile..."
            )
            await asyncio.sleep(2)
            await comms.update_prompt("")
            return None

        await comms.update_prompt(prompt)
        await comms.populate_cards(self)
        while True:
            indexes = await comms.receive_card_indexes()

            # Make a bunch of assertions about the chosen cards
            try:
                assert len(indexes) >= min_num, f"Must select at least {min_num} card(s)"
                assert len(indexes) <= max_num, f"Must select at most {max_num} card(s)"
                cards = [self[ix] for ix in indexes]
                if playing_faceup:
                    assert (
                        len(set(cards)) == 1
                    ), "If selecting multiple cards, they must be the same"
                    assert not (
                        len(cards) > 1 and cards[0].extra_turns
                    ), f"You can only play one {cards[0]} at a time"
                if min_card:
                    if playing_faceup:
                        assert (
                            cards[0] >= min_card
                        ), f"Card needs to be equal to or bigger than {min_card}"
                    else:
                        # Playing from 3dn
                        if cards[0] < min_card:
                            await comms.update_prompt(
                                f"\nYou picked {cards[0]} but it needs to be equal to or bigger "
                                f"than {min_card}! Picking up the discard pile...",
                            )
                            self.hidden_indexes = [
                                ix for ix in self.hidden_indexes if ix != next(iter(indexes))
                            ]
                            await asyncio.sleep(2)
                            await comms.update_prompt("")
                            return None

                # If assertions pass, exit the while loop
                break
            except AssertionError as e:
                await comms.update_prompt(prompt + "\n" + e.args[0])
                await comms.populate_cards(self)

        await comms.update_prompt("")
        return Cards(self.pop(ix) for ix in sorted(indexes, reverse=True))

    def display(self, hide_indexes: List[int]) -> str:
        """Display the cards. Some could be facedown.

        Args:
            hide_indexes: List of indexes of facedown cards

        Returns:
            A string representation of the pile of cards
        """
        if len(self) == 0:
            return "< empty >"
        elif hide_indexes and len(self) > 6:
            return f"< {len(self)} cards >"
        else:
            return " ".join(self.display_list(hide_indexes))

    def display_list(self, hide_indexes: List[int]) -> List[str]:
        """Render the cards into a list of strings. Some could be facedown.

        Args:
            hide_indexes: List of indexes of facedown cards

        Returns:
            A list of string representations of the cards
        """
        return ["[~]" if ix in hide_indexes else str(card) for ix, card in enumerate(self)]

    def __str__(self) -> str:
        # display all cards faceup
        return self.display(hide_indexes=[])


class Deck(Cards):
    """A deck of cards that can deal and shuffle."""

    def __init__(self):
        super().__init__(Card(value) for value, num in SMALL.items() for _ in range(num))
        self.shuffle()

    def shuffle(self):
        """Shuffle the deck in-place."""
        random.shuffle(self)

    def deal(self, n: int) -> Cards:
        """Deal cards from the deck.

        Args:
            n: The number of cards to deal

        Returns:
            The cards dealt
        """
        return [self.pop() for _ in range(n)]

    def __str__(self) -> str:
        # display all cards facedown
        return self.display(hide_indexes=range(len(self)))


class Discard(Cards):
    """The discard pile. Clears when a clear or 3 identical cards in a row are played."""

    def __iadd__(self, cards: Cards) -> "Discard":
        new = self + list(cards)
        if new[-1].is_clear or (len(new) >= 3 and len(set(new[-3:])) == 1):
            # clear the discard
            return Discard()
        else:
            return Discard(new)

    def __str__(self) -> str:
        if len(self) <= 1:
            return super().__str__()
        elif len(self) == 2:
            return f"{self[-1]} (and 1 more card)"
        else:
            return f"{self[-1]} (and {len(self) - 1} more cards)"


class ThreeDown(Cards):
    """3 cards, some of which may be unknown"""

    def __init__(self):
        super().__init__()
        self.hidden_indexes = [0, 1, 2]

    def pop(self, index: int) -> Card:
        self.hidden_indexes = [
            ix if ix < index else ix - 1 for ix in self.hidden_indexes if ix != index
        ]
        return super().pop(index)

    def __str__(self) -> str:
        # display cards facedown if they're hidden
        return self.display(hide_indexes=self.hidden_indexes)
