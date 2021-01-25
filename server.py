import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from austingames import disable_form, threeupthreedown_game, update_board, update_prompt


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

game = threeupthreedown_game()


@app.get("/", response_class=HTMLResponse)
async def get():
    with open("threeupthreedown.html", "r") as f:
        return f.read()


@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str):
    await websocket.accept()
    try:
        if game.is_playing and player_name not in game.players:
            await update_prompt("A game is being played. Please try again later.", websocket)
            return
        elif game.is_playing:
            game.players[player_name].websocket = websocket
            await game.broadcast_board()
            await game.broadcast_waiting_prompt()
            while True:
                await asyncio.sleep(1000)
        else:
            is_vip = False
            if not game.players:
                is_vip = True
                await update_prompt("Start the game by entering 'go' here", websocket)
            else:
                await disable_form(websocket)
        
            game.add_player(name=player_name, is_vip=is_vip, websocket=websocket)
            current_players = "\n".join(
                name + " (VIP)" if player.is_vip else name for name, player in game.players.items()
            )
            for player in game.players.values():
                await update_board(
                    f"Waiting for VIP to start the game. Current players:\n\n{current_players}",
                    player.websocket
                )
        
            # wait for VIP to kick it off
            if is_vip:
                while True:
                    data = await websocket.receive_text()
                    if data == "go":
                        await update_prompt("", websocket)
                        await disable_form(websocket)
                        await game.play()
                        game.reset_game()
            else:
                while True:
                    await asyncio.sleep(1000)
    except WebSocketDisconnect:
        print(f"{player_name} disconnected, waiting for them to come back")
