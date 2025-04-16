# Truthcord 
A Discord webhook bot to fetch and post content from Truth Social to a Discord channel.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/AnthonyZJiang/truthcord.git
cd truthcord
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your environment:
   - Create a `.env` file:
```shell

# COMPULSORY VARIABLES
# user name of the blogger to track
TRUTHSOCIAL_USER=
# discord webhook bot url
DISCORD_WEBHOOK_URL=
# YOUR truth social username
TRUTHSOCIAL_USERNAME=
# Your truth social password
TRUTHSOCIAL_PASSWORD=


# OPIONAL VARIABLES
# Rate at which truth social posts are refreshed.
TRUTHSOCIAL_RATE_LIMIT=60
LOG_LEVEL=INFO
# Your imgur API details, if you want to upload files greater than Discord limit. However, IMGUR has its own limits.
IMGUR_CLIENT_ID=
IMGUR_CLIENT_SECRET=
IMGUR_REFRESH_TOKEN=
# AZURE translator API details
AZURE_TRANSLATOR_KEY=
AZURE_TRANSLATOR_LOCATION=
TRANSLATE_FROM_LANGUAGE=
TRANSLATE_TO_LANGUAGE=
# Discord limits
DISCORD_CHARACTER_LIMIT=2000
DISCORD_FILE_LIMIT=10485760
```

## Usage

Run the bot with the following command:

```shell
python bot.py

# or if you want to pull all messages since 2 day 13 hours 25 minutes 5 seconds ago
python bot.py pull_since=-2d13h25m5s
```

If you want to use python venv, setup your venv in '.venv', then you can also run autostart.sh to skip `source activate`:
```shell
./autostart.sh
```

### Time Format

The `pull_since` argument accepts a relative time format:
- `-XdYhZmWs` where:
  - `X` is days (optional)
  - `Y` is hours (optional)
  - `Z` is minutes (optional)
  - `W` is seconds (optional)

Examples:
- `-1d2h3m4s` - 1 day, 2 hours, 3 minutes, and 4 seconds ago
- `-2h30m` - 2 hours and 30 minutes ago
- `-1d30s` - 1 day and 30 seconds ago
- 

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter any issues or have questions, please open an issue in the repository. 