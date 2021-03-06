import json
import os
from datetime import datetime

import discord
import pytz
import requests
from dotenv import load_dotenv

from keep_alive import keep_alive

# LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
LOCAL_TZ = pytz.timezone('Australia/Sydney')
load_dotenv()

client = discord.Client()


def _convert_isotime_to_local_time(string):
    return datetime.fromisoformat(string[:-1] + "+00:00").replace(tzinfo=pytz.utc).astimezone(LOCAL_TZ)


def _get_emoji(name):
    name = name.replace(" ", "").strip()
    emoji_list = [emoji for emoji in client.emojis if emoji.name == name]
    if len(emoji_list) == 0:
        return ""
    else:
        return str(emoji_list[0])


@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello!")

    if message.content.startswith("$fixtures"):

        def _extract_time_data(data):
            for week in data:
                gameweek_time = _convert_isotime_to_local_time(week["deadline_time"])
                if gameweek_time > datetime.now().replace(tzinfo=pytz.utc).astimezone(LOCAL_TZ):
                    return gameweek_time, week["id"]

        def _parse_teams(teams):
            return {team["id"]: team for team in teams}

        def _parse_fixtures(fixtures, teams):
            # https://www.reddit.com/r/FantasyPL/comments/f8t3bw/cheatsheet_of_all_current_fpl_endpoints/
            def _get_kickoff_emoji(hour):
                def _get_emoji(string):
                    return string

                hour = int(hour)
                if hour < 1:
                    return _get_emoji("yellow_circle")
                if hour < 2:
                    return _get_emoji("orange_circle")
                if hour < 7:
                    return _get_emoji("red_circle")
                if hour < 9:
                    return _get_emoji("orange_circle")
                if hour < 24:
                    return _get_emoji("green_circle")
                return ""

            fixtures_list = ["Fixtures:"]

            for fixture in fixtures:
                home_team = fixture["team_h"]
                away_team = fixture["team_a"]
                home_name = teams[home_team]["name"]
                home_emoji = _get_emoji(home_name)
                away_name = teams[away_team]["name"]
                away_emoji = _get_emoji(away_name)
                kickoff_time = _convert_isotime_to_local_time(fixture["kickoff_time"])
                kickoff_string = kickoff_time.strftime("%A %d %B %Y %I:%M %p")
                kickoff_hour = kickoff_time.strftime("%H")
                fixtures_list.append(
                    f"`{home_name: >14}` {home_emoji}` v `{away_emoji} `{away_name: <14} @ {kickoff_string: >33}` :{_get_kickoff_emoji(kickoff_hour)}:"
                )

            return "\n".join(fixtures_list)

        pl_blob = requests.get(
            "https://fantasy.premierleague.com/api/bootstrap-static/"
        )
        pl_blob_json = json.loads(pl_blob.text)
        deadline_time, gameweek = _extract_time_data(pl_blob_json["events"])
        header = f"EPL:\nGameweek {gameweek} deadline: `{deadline_time.strftime('%A %d %B %Y %I:%M %p')}`\n"

        teams_dict = _parse_teams(pl_blob_json["teams"])

        pl_fixtures = requests.get(
            f"https://fantasy.premierleague.com/api/fixtures?event={gameweek}"
        )
        pl_fixtures_json = json.loads(pl_fixtures.text)
        fixtures = _parse_fixtures(pl_fixtures_json, teams_dict)

        await message.channel.send("\n".join([header, fixtures]))


keep_alive()
client.run(os.getenv("TOKEN"))
