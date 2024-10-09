# Business Brilliance Discord Bot

The **Business Brilliance Discord bot** automates the registration process for new members joining our collegiate networking community. This bot is built to handle the growing influx of members across over 2,500 universities, making onboarding seamless by collecting essential information like names, school affiliations, and graduation years. It automatically assigns roles and sets nicknames for each member.

This bot is designed for scalability and flexibility, providing a fully automated solution for large communities.

## Features

- **Automated Registration**: New members provide their first name, select their school, and optionally their graduation year. The bot assigns roles and nicknames based on the school affiliation.
- **Customizable**: Easily add or remove schools and roles using built-in commands. Adapt the bot to fit the needs of your growing community.
- **School Selection with Pagination**: Supports a large list of schools, using a paginated menu to simplify selection.
- **Alumni and Guest Support**: Handles special categories like alumni or non-student guests, assigning appropriate roles.
- **Notification System**: Sends notifications to a designated channel when a new school or affiliation is added.

## Installation

### Requirements

- Python 3.8+
- Discord.py library (v2.0+)
- A `config.json` file for custom configurations (template provided)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/byw1/Business-Brilliance-Discord-Bot.git
   cd Business-Brilliance-Discord-Bot

2. Install the required dependencies:
   ```bash
    pip install -r requirements.txtot

3. Create a `config.json` file based on the provided `config.example.json` and fill in the required details for your schools and roles.

4. Set your Discord bot token as an environment variable:
   ```bash
   export DISCORD_BOT_TOKEN=your-bot-token

5. Run the bot:
   ```bash
   python discord.py

## Configuration
You can configure the bot using a `config.json` file. The bot expects the following structure:
   ```json
{
  "schools": {
    "School Name": {
      "abbreviation": "SCHOOL_ABBR",
      "type": "College/University"
    }
  },
  "roles": {
    "SCHOOL_ABBR": [ROLE_ID]
  },
  "notification_channel_id": null
}
```
- Schools: Add any number of schools with their abbreviation and type.
- Roles: Associate role IDs with school abbreviations to assign the correct role.
- Notification Channel: Set a channel ID to receive notifications when a new school or affiliation is added.

## Commands
### Slash Commands:
- /sendjoinmessage: Sends the join button for new members to begin the registration process.
- /add school: Adds a new school to the list of selectable schools.
- /add role: Associates a Discord role with a school abbreviation.
- /remove school: Removes a school and its associated roles.
- /remove role: Removes a role associated with a school abbreviation.
- /set notificationchannel: Sets the channel where notifications for new school affiliations are sent.

## Contribution
Contributions are welcome! If you have suggestions or improvements, feel free to open an issue or submit a pull request.

## License
This project is licensed under the MIT License – see the `LICENSE` file for details.
