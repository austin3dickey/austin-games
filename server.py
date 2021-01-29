import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from austingames.threeupthreedown.communication import Communicator
from austingames.threeupthreedown.game import Game


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

game = Game()


@app.get("/", response_class=HTMLResponse)
async def get():
    with open("threeupthreedown.html", "r") as f:
        return f.read()


@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str):
    await websocket.accept()
    comms = Communicator(websocket)

    try:
        # handle a game already in play
        if game.is_playing and player_name not in game.players:
            await comms.update_prompt("A game is being played. Please try again later.")
            return
        elif game.is_playing:
            game.players[player_name].comms = comms
            await game.broadcast_board()
            await game.broadcast_waiting_prompt()
            while True:
                # play as non-VIP
                await asyncio.sleep(1000)

        # game hasn't started yet; set it up
        is_vip = not game.players
        if is_vip:
            await comms.update_prompt("Start the game when everyone has joined!")
            await comms.enable_vip_form()

        game.add_player(name=player_name, is_vip=is_vip, comms=comms)
        current_players = "\n".join(
            name + " (VIP)" if player.is_vip else name for name, player in game.players.items()
        )

        for player in game.players.values():
            await player.comms.update_board(
                f"Waiting for VIP to start the game. Current players:\n\n{current_players}",
            )

        # wait for VIP to kick it off
        if is_vip:
            await websocket.receive_text()
            await comms.update_prompt("")
            win_msg = await game.play()
            for player in game.players.values():
                await player.comms.update_prompt(win_msg + " Refresh page to start again :)")
            game.reset_game()
        else:
            while True:
                # play as non-VIP
                await asyncio.sleep(1000)

    except WebSocketDisconnect:
        if not game.is_playing:
            game.players.pop(player_name, None)
        print(f"{player_name} disconnected, waiting for them to come back")
