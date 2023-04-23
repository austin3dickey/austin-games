# austin-games

Some python games to play.

## Games

### 3up3dn

A fast-paced Uno-type card game.

## Setting up the server

    conda create -yn austingames python>=3.11
    conda activate austingames
    pip install -r requirements.txt
    ./startup.sh

Now you can navigate to https://localhost:8000 and play the game. Others on your wifi can also play,
replacing `localhost` with your computer's local IP address.

You'll need to port forward port 80 for people outside your wifi to log in. Change the websocket
URI in the HTML file to your public IP address.

## Developing

    conda activate austingames
    pip install -r requirements-dev.txt
    pre-commit install
