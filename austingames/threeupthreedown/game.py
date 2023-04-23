import collections

from .cards import Card, Cards, Deck, Discard, ThreeDown
from .communication import Communicator


class Player:
    """A player of the game."""

    def __init__(self, is_vip: bool, comms: Communicator) -> None:
        """
        Args:
            is_vip: Whether they're the first player to join
            comms: The player's Communicator
        """
        self.is_vip = is_vip
        self.comms = comms
        self.hand = Cards()
        self.three_up = Cards()
        self.three_down = ThreeDown()

    async def place_three_up(self) -> None:
        """Before the game starts, choose cards to be your 3up"""
        cards = await self.hand.choose(
            comms=self.comms,
            prompt="3 cards to place as your 3up:",
            min_num=3,
            max_num=3,
            playing_faceup=False,
            min_card=None,
        )
        assert cards
        self.three_up += cards

    async def take_turn(
        self, top_discard_card: Card | None
    ) -> tuple[Cards | None, str]:
        """Take a turn from one of your piles of cards.

        Args:
            top_discard_card: The card at the top of the discard pile

        Returns:
            A tuple of: 1) the cards chosen (or None if the player must pick up the discard pile),
            and 2) the location from which the cards were chosen to display in the log
        """
        if self.hand:
            cards = await self.hand.choose(
                comms=self.comms,
                prompt="Card(s) to play:",
                min_num=1,
                max_num=len(self.hand),
                playing_faceup=True,
                min_card=top_discard_card,
            )
            location = "hand"
        elif self.three_up:
            cards = await self.three_up.choose(
                comms=self.comms,
                prompt="Card(s) to play from your 3up:",
                min_num=1,
                max_num=len(self.three_up),
                playing_faceup=True,
                min_card=top_discard_card,
            )
            location = "3up"
        else:
            cards = await self.three_down.choose(
                comms=self.comms,
                prompt="Card to play from your 3dn:",
                min_num=1,
                max_num=1,
                playing_faceup=False,
                min_card=top_discard_card,
            )
            location = "3dn"

        return cards, location

    def add_to_hand(self, cards: Cards) -> None:
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
        hand = (
            self.hand.display(hide_indexes=list(range(len(self.hand))))
            if hide_hand
            else self.hand
        )
        three_down = (
            self.three_down.display(hide_indexes=list(range(len(self.three_down))))
            if hide_hand
            else self.three_down
        )

        return (
            f"{player_name}\n"
            f"{'~' * len(player_name)}\n"
            f"{player_name}'s hand: {hand}\n"
            f"{player_name}'s 3up: {self.three_up}\n"
            f"{player_name}'s 3dn: {three_down}\n"
        )


class TurnLog(collections.deque[str]):
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

    def __init__(self) -> None:
        self.reset_game()

    def reset_game(self) -> None:
        """Reset the game to a new game state"""
        self.is_playing = False
        self.current_turn = ""
        self.players: dict[str, Player] = {}
        self.deck = Deck()
        self.discard = Discard()
        self.turn_log = TurnLog([], self.TURN_LOG_LENGTH)

    def add_player(self, name: str, is_vip: bool, comms: Communicator) -> None:
        """
        Add a player to the game before it starts

        Args:
            name: The name of the player to add
            is_vip: Whether they're the first player to join
            comms: The player's Communicator
        """
        self.players[name] = Player(is_vip, comms)
        self.players[name].add_to_hand(self.deck.deal(6))
        self.players[name].three_down += self.deck.deal(3)

    def board_view(self, player_name: str) -> str:
        """Compile a view of the board to a specific player

        Args:
            player_name: The name of the player whose view it is

        Returns:
            A string to display
        """
        # put the current player on top
        players = [(player_name, self.players[player_name])] + [
            (name, player)
            for name, player in self.players.items()
            if name != player_name
        ]
        player_descriptions = "\n".join(
            player.display(player_name=name, hide_hand=name != player_name)
            for name, player in players
        )

        return (
            f"{self.current_turn}'s turn!\n\n"
            f"Draw pile: {self.deck}\n"
            f"Discard pile: {self.discard}\n\n"
            f"{player_descriptions}\n\n"
            f"{self.turn_log}"
        )

    async def broadcast_board(self) -> None:
        """Broadcast the views of the board to all players"""
        for player_name, player in self.players.items():
            await player.comms.update_board(self.board_view(player_name))

    async def broadcast_waiting_prompt(self) -> None:
        """Broadcast the waiting prompt to all players whose turn it isn't"""
        for player_name, player in self.players.items():
            if player_name != self.current_turn:
                await player.comms.update_prompt(
                    f"Waiting for {self.current_turn} to play"
                )

    async def everyone_place_three_up(self) -> None:
        """Before the game starts, everyone go around and place their 3up cards"""
        for player_name, player in self.players.items():
            self.current_turn = player_name
            await self.broadcast_board()
            await self.broadcast_waiting_prompt()
            await player.place_three_up()

    async def everyone_take_a_turn(self) -> str | None:
        """Everyone go around and take a turn

        Returns:
            None unless a player has won; then a message describing how they won
        """
        for player_name, player in self.players.items():
            self.current_turn = player_name
            turns_left = 1
            while turns_left:
                await self.broadcast_board()
                await self.broadcast_waiting_prompt()
                top_discard = self.discard[-1] if self.discard else None
                cards, location = await player.take_turn(top_discard)
                turns_left -= 1
                if cards:
                    # the player played cards
                    if not player.three_down:
                        winning_msg = f"{player_name} won with a {cards[0]}!! Woohoo!!!"
                        self.turn_log.appendleft(winning_msg)
                        await self.broadcast_board()
                        return winning_msg

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
                    self.turn_log.appendleft(
                        f"{player_name} picked up the discard pile"
                    )
        # no one won yet
        return None

    async def play(self) -> str:
        """Play the game!

        Returns:
            The win message
        """
        for player in self.players.values():
            await player.comms.enable_card_form()
        self.is_playing = True
        await self.everyone_place_three_up()
        winning_msg = None
        while not winning_msg:
            winning_msg = await self.everyone_take_a_turn()
        self.is_playing = False
        return winning_msg
