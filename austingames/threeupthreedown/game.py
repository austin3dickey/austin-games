import argparse
import collections
import os
from typing import Optional

from .cards import Card, Cards, Deck, Discard, ThreeDown


class Player:
    """A player of the game."""

    def __init__(self):
        self.hand = Cards()
        self.three_up = Cards()
        self.three_down = ThreeDown()

    def place_three_up(self):
        """Before the game starts, choose cards to be your 3up"""
        cards = self.hand.choose(
            prompt="Space-separated indexes of 3 cards to place as your 3up",
            min_num=3,
            max_num=3,
            playing_faceup=False,
            min_card=None,
        )
        self.three_up += cards

    def take_turn(self, top_discard_card: Card) -> tuple[Optional[Cards], str]:
        """Take a turn from one of your piles of cards.

        Args:
            top_discard_card: The card at the top of the discard pile

        Returns:
            A tuple of: 1) the cards chosen (or None if the player must pick up the discard pile),
            and 2) the location from which the cards were chosen to display in the log
        """
        if self.hand:
            cards = self.hand.choose(
                prompt="Space-separated indexes of card(s) to play",
                min_num=1,
                max_num=len(self.hand),
                playing_faceup=True,
                min_card=top_discard_card,
            )
            location = "hand"
        elif self.three_up:
            cards = self.three_up.choose(
                prompt="Space-separated indexes of card(s) to play from your 3up",
                min_num=1,
                max_num=len(self.three_up),
                playing_faceup=True,
                min_card=top_discard_card,
            )
            location = "3up"
        else:
            cards = self.three_down.choose(
                prompt="Index of the card to play from your 3dn",
                min_num=1,
                max_num=1,
                playing_faceup=False,
                min_card=top_discard_card,
            )
            location = "3dn"

        return cards, location

    def add_to_hand(self, cards: Cards):
        """Add cards to your hand and sort them if your hand is too big

        Args:
            cards: The cards to add
        """
        self.hand += cards
        if len(self.hand) > 6:
            self.hand.sort()

    def display(self, player_name: str, hide_hand: bool) -> str:
        """Render a message displaying the player's situation

        Args:
            player_name: The player's name
            hide_hand: Whether to hide the hand (if it's not the active player)

        Returns:
            A string to display
        """
        hand = self.hand.display(hide_indexes=range(len(self.hand))) if hide_hand else self.hand
        three_down = (
            self.three_down.display(hide_indexes=range(len(self.three_down)))
            if hide_hand
            else self.three_down
        )

        return f"""{player_name}
{'~' * len(player_name)}
{player_name}'s hand: {hand}
{player_name}'s 3up: {self.three_up}
{player_name}'s 3dn: {three_down}
        """


class TurnLog(collections.deque):
    """A log of what happened in the last few turns"""

    def __str__(self) -> str:
        if len(self) == 0:
            return ""
        elif len(self) == 1:
            title = "Last turn:"
            return f"{title}\n{'~' * len(title)}\n{self[0]}"
        else:
            title = f"Last {len(self)} turns (most recent at top):"
            return f"{title}\n{'~' * len(title)}\n" + "\n".join(self)


class Game:
    """A class tracking everything happening in the game"""

    TURN_LOG_LENGTH = 10

    def __init__(self, player_names: list[str]):
        """
        Args:
            player_names: The names of the players to initialize
        """
        self.players = {name: Player() for name in player_names}
        self.deck = Deck()
        self.discard = Discard()
        self.turn_log = TurnLog([], self.TURN_LOG_LENGTH)
        for name in self.players:
            self.players[name].add_to_hand(self.deck.deal(6))
            self.players[name].three_down += self.deck.deal(3)

    def print_board(self, player_name: str):
        """Print a view of the board for a specific player

        Args:
            player_name: The name of the player whose view it is
        """
        os.system("clear")

        # put the current player on top
        players = [(player_name, self.players[player_name])] + [
            (name, player) for name, player in self.players.items() if name != player_name
        ]
        player_descriptions = "\n".join(
            player.display(player_name=name, hide_hand=name != player_name)
            for name, player in players
        )

        print(
            f"""
{player_name}'s turn!

Draw pile: {self.deck}
Discard pile: {self.discard}

{player_descriptions}

{self.turn_log}
            """
        )

    def everyone_place_three_up(self):
        """Before the game starts, everyone go around and place their 3up cards"""
        for player_name, player in self.players.items():
            self.print_board(player_name)
            player.place_three_up()

    def everyone_take_a_turn(self) -> Optional[str]:
        """Everyone go around and take a turn

        Returns:
            None unless a player has won; then a message describing how they won
        """
        for player_name, player in self.players.items():
            turns_left = 1
            while turns_left:
                self.print_board(player_name)
                top_discard = self.discard[-1] if self.discard else None
                cards, location = player.take_turn(top_discard)
                turns_left -= 1
                if cards:
                    # the player played cards
                    if not player.three_down:
                        return f"{player_name} won with a {cards[0]}!! Woohoo!!!"

                    # If the card has extra turns, add them here
                    turns_left += cards[0].extra_turns
                    self.discard += cards

                    # Deal back up to 3 cards if they exist in the deck
                    cards_to_deal = min(max(0, 3 - len(player.hand)), len(self.deck))
                    player.add_to_hand(self.deck.deal(cards_to_deal))

                    # Add a message to the turn log
                    msg = f"{player_name} played {cards} from their {location}"
                    if not self.discard:
                        msg += " and the discard pile was cleared"
                    self.turn_log.appendleft(msg)
                else:
                    # The player has to pick up the discard pile
                    player.add_to_hand(self.discard)
                    self.discard.clear()
                    self.turn_log.appendleft(f"{player_name} picked up the discard pile")
        # no one won yet
        return None

    def play(self):
        """Play the game!"""
        self.everyone_place_three_up()
        winning_msg = None
        while not winning_msg:
            winning_msg = self.everyone_take_a_turn()
        print(winning_msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("names", help="Comma-separated names of players")
    args = parser.parse_args()

    g = Game(args.names.split(","))
    g.play()
