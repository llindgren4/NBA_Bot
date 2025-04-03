import discord
import json
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.endpoints import leaguestandingsv3
import asyncio
import pytz  # For timezone handling
import warnings
from dotenv import load_dotenv
import os


warnings.filterwarnings("ignore", category=FutureWarning)

load_dotenv()

# Discord bot setup
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Load or initialize the sports channel IDs for multiple servers
CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"SPORTS_CHANNELS": {}, "TIME_ZONES": {}}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

config = load_config()
SPORTS_CHANNELS = config.get("SPORTS_CHANNELS", {})

# Team mappings
TEAM_ID_TO_NAME = {
    "1610612737": "Atlanta Hawks",
    "1610612738": "Boston Celtics",
    "1610612739": "Cleveland Cavaliers",
    "1610612740": "New Orleans Pelicans",
    "1610612741": "Chicago Bulls",
    "1610612742": "Dallas Mavericks",
    "1610612743": "Denver Nuggets",
    "1610612744": "Golden State Warriors",
    "1610612745": "Houston Rockets",
    "1610612746": "LA Clippers",
    "1610612747": "Los Angeles Lakers",
    "1610612748": "Miami Heat",
    "1610612749": "Milwaukee Bucks",
    "1610612750": "Minnesota Timberwolves",
    "1610612751": "Brooklyn Nets",
    "1610612752": "New York Knicks",
    "1610612753": "Orlando Magic",
    "1610612754": "Indiana Pacers",
    "1610612755": "Philadelphia 76ers",
    "1610612756": "Phoenix Suns",
    "1610612757": "Portland Trail Blazers",
    "1610612758": "Sacramento Kings",
    "1610612759": "San Antonio Spurs",
    "1610612760": "Oklahoma City Thunder",
    "1610612761": "Toronto Raptors",
    "1610612762": "Utah Jazz",
    "1610612763": "Memphis Grizzlies",
    "1610612764": "Washington Wizards",
    "1610612765": "Detroit Pistons",
    "1610612766": "Charlotte Hornets",
}

TEAM_ID_TO_EMOJI = {
    "1610612737": "<:1900hawks:1357071341202968647>",  # Atlanta Hawks
    "1610612738": "<:1609celtics:1357071309019811912>",  # Boston Celtics
    "1610612739": "<:9460cavaliers:1357072065315999988>",  # Cleveland Cavaliers
    "1610612740": "<:2128pelicans:1357071377932353576>",  # New Orleans Pelicans
    "1610612741": "<:7199bulls:1357071780069642480>",  # Chicago Bulls
    "1610612742": "<:6534mavericks:1357071705855492106>",  # Dallas Mavericks
    "1610612743": "<:7985nuggets:1357071806221127740>",  # Denver Nuggets
    "1610612744": "<:7061warriors:1357071734314106900>",  # Golden State Warriors
    "1610612745": "<:4635rockets:1357071513466962120>",  # Houston Rockets
    "1610612746": "<:6452clippers:1357071052814946545>",  # LA Clippers
    "1610612747": "<:3503lakers:1357071439613923418>",  # Los Angeles Lakers
    "1610612748": "<:5463heat:1357071596887736592>",  # Miami Heat
    "1610612749": "<:3434bucks:1357071076454306012>",  # Milwaukee Bucks
    "1610612750": "<:1338timberwolves:1357071297246400702>",  # Minnesota Timberwolves
    "1610612751": "<:8159nets:1357071827511283722>",  # Brooklyn Nets
    "1610612752": "<:8941knicks:1357071086537150494>",  # New York Knicks
    "1610612753": "<:3090magic:1357071393132642575>",  # Orlando Magic
    "1610612754": "<:9445pacers:1357072041726972155>",  # Indiana Pacers
    "1610612755": "<:207676ers:1357071358646947860>",  # Philadelphia 76ers
    "1610612756": "<:3754suns:1357071463588298895>",  # Phoenix Suns
    "1610612757": "<:8613trailblazers:1357071136080400495>",  # Portland Trail Blazers
    "1610612758": "<:1758kings:1357071323301675029>",  # Sacramento Kings
    "1610612759": "<:1274spurs:1357071270004654141>",  # San Antonio Spurs
    "1610612760": "<:1338thunder:1357071285116735559>",  # Oklahoma City Thunder
    "1610612761": "<:8831raptors:1357071997712203916>",  # Toronto Raptors
    "1610612762": "<:8173jazz:1357071854900088932>",  # Utah Jazz
    "1610612763": "<:4737grizzlies:1357071121471770674>",  # Memphis Grizzlies
    "1610612764": "<:4963wizards:1357071540889456682>",  # Washington Wizards
    "1610612765": "<:6534pistons:1357071103142658239>",  # Detroit Pistons
    "1610612766": "<:4070hornets:1357071486149464316>",  # Charlotte Hornets
}

# Mapping of time zone abbreviations to pytz time zones
TIMEZONE_ABBREVIATIONS = {
    "ET": "US/Eastern",
    "CST": "US/Central",
    "MST": "US/Mountain",
    "PST": "US/Pacific",
    "EST": "US/Eastern",
    "CDT": "US/Central",
    "MDT": "US/Mountain",
    "PDT": "US/Pacific",
}
# Helper function to fetch NBA games
def get_nba_games(date):
    date_str = date.strftime("%Y-%m-%d")
    scoreboard = scoreboardv2.ScoreboardV2(game_date=date_str).get_dict()
    game_header = scoreboard["resultSets"][0]["rowSet"]  # GameHeader dataset
    line_score = scoreboard["resultSets"][1]["rowSet"]  # LineScore dataset
    return game_header, line_score

def fetch_team_records():
    """
    Fetches the current win-loss records for all NBA teams.
    Returns a dictionary mapping team names to their records.
    """
    standings = leaguestandingsv3.LeagueStandingsV3().get_dict()
    records = {}

    # Extract team standings data
    for team in standings["resultSets"][0]["rowSet"]:
        team_id = str(team[2])
        wins = team[13]       # Wins
        losses = team[14]     # Losses
        records[team_id] = f"{wins}-{losses}"  # Format as "W-L"

    return records

# Format NBA game data for display
def format_nba_games(games, line_scores, guild_id):
    if not games:
        return "No NBA games today.\n"

    # Get the server's time zone or default to US/Eastern
    timezone = config.get("TIME_ZONES", {}).get(str(guild_id), "US/Eastern")
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    formatted_games = []

    # Fetch team records
    team_records = fetch_team_records()

    # Create a dictionary for scores from the LineScore dataset
    scores = {}
    for line_score in line_scores:
        team_id = str(line_score[3])  # TEAM_ID
        total_points = line_score[22]  # PTS
        scores[team_id] = total_points

    for game in games:
        home_team_id = str(game[6])  # HOME_TEAM_ID
        away_team_id = str(game[7])  # VISITOR_TEAM_ID
        game_time_str = game[4]  # GAME_STATUS_TEXT or time string
        game_status_id = game[3]  # GAME_STATUS_ID
        game_status_text = game[4]  # GAME_STATUS_TEXT (e.g., "Scheduled", "1st Qtr", "Final")

        # Map team IDs to team names and emojis
        home_team_name = TEAM_ID_TO_NAME.get(home_team_id, "Unknown Team")
        away_team_name = TEAM_ID_TO_NAME.get(away_team_id, "Unknown Team")
        home_team_emoji = TEAM_ID_TO_EMOJI.get(home_team_id, "")
        away_team_emoji = TEAM_ID_TO_EMOJI.get(away_team_id, "")

        # Get team records
        home_team_record = team_records.get(home_team_id, "0-0")
        away_team_record = team_records.get(away_team_id, "0-0")

        # Get scores for live games
        home_team_score = scores.get(home_team_id, 0)
        away_team_score = scores.get(away_team_id, 0)

        # Determine the winner for completed games
        if game_status_id == 3:  # Final
            if home_team_score > away_team_score:
                formatted_games.append(
                    f"Final: {home_team_emoji} **{home_team_name} ({home_team_record})** {home_team_score} - {away_team_score} {away_team_emoji} {away_team_name} ({away_team_record})"
                )
            else:
                formatted_games.append(
                    f"Final: {home_team_emoji} {home_team_name} ({home_team_record}) {home_team_score} - {away_team_score} {away_team_emoji} **{away_team_name} ({away_team_record})**"
                )
        elif game_status_id == 2:  # In Progress
            formatted_games.append(
                f"**LIVE** {game_status_text.strip()} : {home_team_emoji} {home_team_name} ({home_team_record}) **{home_team_score} - {away_team_score}** {away_team_emoji} {away_team_name} ({away_team_record})"
            )
        else:  # Scheduled
            try:
                # Attempt to parse the game time if it's a valid time string
                game_time = datetime.strptime(game_time_str, "%I:%M %p").replace(
                    year=now.year, month=now.month, day=now.day
                )
                # Make game_time timezone-aware and convert to the server's time zone
                game_time = pytz.timezone("US/Eastern").localize(game_time).astimezone(tz)
                tz_abbreviation = game_time.tzname()
                formatted_time = game_time.strftime('%I:%M %p') + f" {tz_abbreviation}"
            except ValueError:
                # If parsing fails, use the game status text (e.g., "1st Qtr", "Final")
                formatted_time = game_status_text

            formatted_games.append(
                f"{formatted_time} : {home_team_emoji} {home_team_name} ({home_team_record}) vs {away_team_emoji} {away_team_name} ({away_team_record})"
            )

    # Combine all games into a visually appealing block
    response = "**NBA Games:**\n\n" + "\n".join(formatted_games)
    return response

async def post_daily_games():
    # Set the target time zone to PST
    pst = pytz.timezone("US/Pacific")

    while True:
        # Get the current time in PST
        now = datetime.now(pst)

        # Calculate the next 10 AM PST
        next_post_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if now >= next_post_time:
            # If it's already past 10 AM, schedule for 10 AM the next day
            next_post_time += timedelta(days=1)

        # Calculate the time to sleep until the next post
        sleep_time = (next_post_time - now).total_seconds()
        print(f"Bot will post daily games at {next_post_time} PST. Sleeping for {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)

        # Determine the date to fetch games for
        post_date = next_post_time.date() if now.hour >= 10 else now.date()

        # Fetch games for the determined date
        games, line_scores = get_nba_games(post_date)

        # Format the games for display
        for guild_id, channel_id in SPORTS_CHANNELS.items():
            try:
                channel = client.get_channel(channel_id)
                if channel:
                    response = format_nba_games(games, line_scores, guild_id)
                    await channel.send(response)
            except Exception as e:
                print(f"Error posting daily games to guild {guild_id}: {e}")

        # Wait until 10 AM PST the next day
        now = datetime.now(pst)
        next_post_time = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        sleep_time = (next_post_time - now).total_seconds()
        print(f"Next post scheduled for {next_post_time} PST. Sleeping for {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    # Ensure all connected servers are in the config
    for guild in client.guilds:
        if str(guild.id) not in SPORTS_CHANNELS:
            print(f"Adding new server to config: {guild.name} (ID: {guild.id})")
            SPORTS_CHANNELS[str(guild.id)] = None  # No sports channel set yet
            config["SPORTS_CHANNELS"] = SPORTS_CHANNELS

        if str(guild.id) not in config.get("TIME_ZONES", {}):
            print(f"Setting default time zone for server: {guild.name} (ID: {guild.id})")
            if "TIME_ZONES" not in config:
                config["TIME_ZONES"] = {}
            config["TIME_ZONES"][str(guild.id)] = "US/Eastern"  # Default to Eastern Time

    # Save the updated config
    save_config(config)

    # Schedule the daily NBA games post
    client.loop.create_task(post_daily_games())

@client.event
async def on_message(message):
    global SPORTS_CHANNELS, config

    # Ignore bot's own messages
    if message.author == client.user:
        return

    # Ignore DMs (no guild context)
    if message.guild is None:
        await message.channel.send("This bot only works in servers.")
        return

    # Handle the "!setchannel" command
    if message.content.lower().startswith("!setchannel"):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You must be an administrator to set the sports channel.")
            return

        # Set the current channel as the sports channel
        SPORTS_CHANNELS[str(message.guild.id)] = message.channel.id
        config["SPORTS_CHANNELS"] = SPORTS_CHANNELS
        save_config(config)
        await message.channel.send(f"This channel has been set as the sports channel for daily NBA updates.")
        return

    # Handle the "!settimezone" command
    if message.content.lower().startswith("!settimezone"):
        try:
            _, timezone = message.content.split(" ", 1)
            # Check if the input is an abbreviation and map it to a full time zone
            if timezone.upper() in TIMEZONE_ABBREVIATIONS:
                timezone = TIMEZONE_ABBREVIATIONS[timezone.upper()]
            # Validate the time zone
            pytz.timezone(timezone)
            if "TIME_ZONES" not in config:
                config["TIME_ZONES"] = {}
            config["TIME_ZONES"][str(message.guild.id)] = timezone
            save_config(config)
            await message.channel.send(f"Time zone for this server has been set to `{timezone}`.")
        except (ValueError, pytz.UnknownTimeZoneError):
            await message.channel.send(
                "Invalid time zone. Please provide a valid time zone abbreviation (e.g., `ET`, `CST`) or full name (e.g., `America/New_York`)."
            )
        return

    # Ensure commands are only used in the sports channel
    if str(message.guild.id) not in SPORTS_CHANNELS or message.channel.id != SPORTS_CHANNELS[str(message.guild.id)]:
        return

    # Handle sports commands
    if message.content.lower() == "!nba":
        # Get the server's time zone or default to US/Eastern
        timezone = config.get("TIME_ZONES", {}).get(str(message.guild.id), "US/Eastern")
        tz = pytz.timezone(timezone)

        # Get the current time in the server's time zone
        now = datetime.now(tz)

        # Determine the date to fetch games for
        # Fetch previous day's games until 10 AM Eastern, then switch to today's games
        if now.hour < 10:  # Before 10 AM
            fetch_date = (now - timedelta(days=1)).date()  # Previous day
        else:  # 10 AM or later
            fetch_date = now.date()  # Current day

        # Fetch games for the determined date
        games, line_scores = get_nba_games(fetch_date)

        # Format the games for display
        response = format_nba_games(games, line_scores, message.guild.id)
        await message.channel.send(response)
                
client.run(TOKEN)