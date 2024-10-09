import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# Load the bot token from an environment variable or replace with your token
TOKEN = 'your-bot-token'

if TOKEN is None:
    raise ValueError("Bot token not found. Please set the DISCORD_BOT_TOKEN environment variable.")

intents = discord.Intents.all()
intents.members = True  # Subscribe to the members intent

bot = commands.Bot(command_prefix='!', intents=intents)

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default empty config
        return {'schools': {}, 'roles': {}, 'notification_channel_id': None}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

config = load_config()

MEMBER_ROLE_ID = 825908181951709224  # Replace with your actual 'Member' role ID
GUEST_ROLE_ID = 1148284141897531524  # 'Guest' role ID as provided

class JoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Click to Get Access', style=discord.ButtonStyle.green, custom_id='join_button')
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Send modal to collect first name
        await interaction.response.send_modal(FirstNameModal())

class FirstNameModal(discord.ui.Modal, title="First Name"):
    first_name = discord.ui.TextInput(label="First Name", placeholder="Enter your first name")

    async def on_submit(self, interaction: discord.Interaction):
        first_name_value = self.first_name.value.strip()
        # Proceed to school type selection
        await proceed_to_school_type(interaction, first_name_value)

async def proceed_to_school_type(interaction, first_name):
    # Build school type select
    school_types = ['Alumni', 'College/University', 'Community College', 'Highschool', 'Other']
    options = [discord.SelectOption(label=stype) for stype in school_types]
    school_type_select = discord.ui.Select(placeholder="Select your school type", options=options)

    async def school_type_select_callback(select_interaction: discord.Interaction):
        selected_type = school_type_select.values[0]
        if selected_type == 'Alumni':
            # Proceed to college/university selection and skip graduation year
            await proceed_to_school_selection(
                select_interaction,
                first_name,
                'College/University',
                skip_year=True,
                for_alumni=True
            )
        elif selected_type == 'College/University':
            # Proceed directly to school selection
            await proceed_to_school_selection(select_interaction, first_name, 'College/University')
        elif selected_type in ['Community College', 'Highschool']:
            # Use the abbreviations from config
            school_info = config['schools'].get(selected_type, {'abbreviation': selected_type})
            school_abbr = school_info['abbreviation']
            # Proceed directly to graduation year selection
            await proceed_to_graduation(select_interaction, first_name, selected_type, school_abbr)
        elif selected_type == 'Other':
            # Proceed to other affiliation
            await proceed_to_other_affiliation(select_interaction, first_name)
        else:
            await select_interaction.response.send_message("Invalid selection.", ephemeral=True)

    school_type_select.callback = school_type_select_callback
    view = discord.ui.View()
    view.add_item(school_type_select)
    await interaction.response.send_message("Select your school type:", view=view, ephemeral=True)

async def proceed_to_other_affiliation(interaction, first_name):
    # Send modal to collect clarification
    class OtherAffiliationModal(discord.ui.Modal, title="Your Affiliation"):
        clarification = discord.ui.TextInput(label="Please specify", placeholder="e.g., Entrepreneur, Guest")

        async def on_submit(self, interaction: discord.Interaction):
            clarification_value = self.clarification.value.strip()
            # Send notification to the configured channel
            notification_channel_id = config.get('notification_channel_id')
            if notification_channel_id:
                notification_channel = interaction.guild.get_channel(notification_channel_id)
                if notification_channel:
                    await notification_channel.send(
                        f"{interaction.user.mention} joined with affiliation: {clarification_value}"
                    )
            # Set nickname and assign roles
            await finalize_registration_other(interaction, first_name, clarification_value)

    await interaction.response.send_modal(OtherAffiliationModal())

async def finalize_registration_other(interaction, first_name, clarification):
    # Set nickname as 'FirstName | Guest'
    nickname = f"{first_name} | Guest"
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    if member:
        await member.edit(nick=nickname)
        # Assign Member role and Guest role
        roles_to_assign = []
        member_role = guild.get_role(MEMBER_ROLE_ID)
        guest_role = guild.get_role(GUEST_ROLE_ID)
        if member_role:
            roles_to_assign.append(member_role)
        if guest_role:
            roles_to_assign.append(guest_role)
        if roles_to_assign:
            await member.add_roles(*roles_to_assign)
        await interaction.response.send_message(
            f"Your nickname has been set to {nickname} and roles assigned.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Error: Could not find you in the server.", ephemeral=True
        )

async def proceed_to_other_school(interaction, first_name):
    # Send modal to collect school name and abbreviation (no school type)
    class OtherSchoolModal(discord.ui.Modal, title="Other School"):
        school_name = discord.ui.TextInput(label="School Name", placeholder="Enter your school name")
        school_abbr = discord.ui.TextInput(label="School Abbreviation", placeholder="Enter abbreviation")

        async def on_submit(self, interaction: discord.Interaction):
            school_name_value = self.school_name.value.strip()
            school_abbr_value = self.school_abbr.value.strip()
            # Assume school type is 'College/University'
            # Send notification to the configured channel
            notification_channel_id = config.get('notification_channel_id')
            if notification_channel_id:
                notification_channel = interaction.guild.get_channel(notification_channel_id)
                if notification_channel:
                    await notification_channel.send(
                        f"{interaction.user.mention} joined from a new school, {school_name_value} ({school_abbr_value})"
                    )
            # Proceed to graduation year selection
            await proceed_to_graduation(interaction, first_name, school_name_value, school_abbr_value)

    await interaction.response.send_modal(OtherSchoolModal())

async def proceed_to_school_selection(interaction, first_name, school_type, skip_year=False, for_alumni=False):
    # Filter schools based on school type
    schools = [
        name for name, info in config['schools'].items()
        if info['type'] == school_type
    ]

    schools.sort()
    schools.append('Other')

    # Implement pagination
    page = 0
    items_per_page = 25  # Max options per select menu as per Discord's limit
    total_pages = (len(schools) + items_per_page - 1) // items_per_page  # Ceiling division

    # Function to create the view for the current page
    def create_view(page):
        start = page * items_per_page
        end = start + items_per_page
        page_schools = schools[start:end]

        options = [discord.SelectOption(label=school) for school in page_schools]
        school_select = discord.ui.Select(placeholder=f"Select your school (Page {page + 1}/{total_pages})", options=options)

        async def school_select_callback(select_interaction: discord.Interaction):
            selected_school = school_select.values[0]
            if selected_school == 'Other':
                # User inputs their school manually
                await proceed_to_other_school(select_interaction, first_name)
            else:
                school_info = config['schools'][selected_school]
                school_abbr = school_info['abbreviation']
                if skip_year or for_alumni:
                    # Skip graduation year and proceed to finalize
                    await finalize_registration(select_interaction, first_name, selected_school, school_abbr, is_alumni=for_alumni)
                else:
                    await proceed_to_graduation(select_interaction, first_name, selected_school, school_abbr)

        school_select.callback = school_select_callback

        view = discord.ui.View()
        view.add_item(school_select)

        # Add pagination buttons if necessary
        if total_pages > 1:
            if page > 0:
                back_button = discord.ui.Button(emoji='⬅️', style=discord.ButtonStyle.secondary)

                async def back_callback(button_interaction: discord.Interaction):
                    await update_message(button_interaction, page - 1)

                back_button.callback = back_callback
                view.add_item(back_button)

            if page < total_pages - 1:
                forward_button = discord.ui.Button(emoji='➡️', style=discord.ButtonStyle.secondary)

                async def forward_callback(button_interaction: discord.Interaction):
                    await update_message(button_interaction, page + 1)

                forward_button.callback = forward_callback
                view.add_item(forward_button)

        return view

    # Function to update the message with a new page
    async def update_message(interaction, new_page):
        new_view = create_view(new_page)
        await interaction.response.edit_message(view=new_view)

    # Send the initial message
    initial_view = create_view(page)
    await interaction.response.send_message("Select your school:", view=initial_view, ephemeral=True)

async def proceed_to_graduation(interaction, first_name, school_name, school_abbr):
    # Build grad year select
    years = [str(year) for year in range(2024, 2030)]  # Adjust years as needed
    years.append('Skip')
    options = [discord.SelectOption(label=year) for year in years]
    year_select = discord.ui.Select(placeholder="Select your graduation year or Skip", options=options)

    async def year_select_callback(select_interaction: discord.Interaction):
        grad_year = year_select.values[0]
        if grad_year == 'Skip':
            await finalize_registration(select_interaction, first_name, school_name, school_abbr, grad_year=None)
        else:
            await finalize_registration(select_interaction, first_name, school_name, school_abbr, grad_year=grad_year)

    year_select.callback = year_select_callback
    view = discord.ui.View()
    view.add_item(year_select)
    await interaction.response.send_message("Select your graduation year or Skip:", view=view, ephemeral=True)

async def finalize_registration(interaction, first_name, school_name, school_abbr, grad_year=None, is_alumni=False):
    # Build nickname
    if is_alumni:
        nickname = f"{first_name} | {school_abbr} Alum"
    elif grad_year:
        nickname = f"{first_name} | {school_abbr} '{grad_year[-2:]}"
    else:
        nickname = f"{first_name} | {school_abbr}"

    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    if member:
        await member.edit(nick=nickname)
        # Assign roles based on school abbreviation
        role_ids = config['roles'].get(school_abbr, [])
        role_ids.append(MEMBER_ROLE_ID)  # Add the Member role ID
        roles_to_assign = []
        for role_id in role_ids:
            role = guild.get_role(role_id)
            if role:
                roles_to_assign.append(role)
        if roles_to_assign:
            await member.add_roles(*roles_to_assign)
        await interaction.response.send_message(
            f"Your nickname has been set to {nickname} and roles assigned.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Error: Could not find you in the server.", ephemeral=True
        )

# Command to send the join button in the channel
@bot.tree.command(name="sendjoinmessage", description="Sends the join button without any accompanying text.")
@app_commands.default_permissions(administrator=True)
async def send_join_message(interaction: discord.Interaction):
    """Sends the join button without any accompanying text."""
    await interaction.response.defer(ephemeral=True)
    view = JoinView()
    await interaction.channel.send(view=view)
    await interaction.followup.send("Join message sent.", ephemeral=True)

# Create 'add' command group
class AddGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name='add', description='Commands to add things', default_permissions=discord.Permissions(administrator=True))

add_group = AddGroup()

@add_group.command(name="school", description="Adds a new school to the list of selectable schools.")
@app_commands.describe(school_name="Name of the school", school_abbr="Abbreviation of the school")
async def add_school(interaction: discord.Interaction, school_name: str, school_abbr: str):
    """Adds a new school to the list of selectable schools."""
    # Check for duplicate school name
    if school_name in config['schools']:
        await interaction.response.send_message(f"School name '{school_name}' is already in use.", ephemeral=True)
        return
    # Check for duplicate school abbreviation
    for existing_info in config['schools'].values():
        if existing_info['abbreviation'] == school_abbr:
            await interaction.response.send_message(f"School abbreviation '{school_abbr}' is already in use.", ephemeral=True)
            return
    # Add the school
    school_type = 'College/University'  # Default type
    config['schools'][school_name] = {'abbreviation': school_abbr, 'type': school_type}
    save_config(config)
    await interaction.response.send_message(f"Added school {school_name} with abbreviation {school_abbr}.", ephemeral=True)

@add_group.command(name="role", description="Associates a role with a school abbreviation.")
@app_commands.describe(school_abbr="Abbreviation of the school", role="Role to assign")
async def add_role(interaction: discord.Interaction, school_abbr: str, role: discord.Role):
    """Associates a role with a school abbreviation."""
    # Check if the school abbreviation exists
    if not any(info['abbreviation'] == school_abbr for info in config['schools'].values()):
        await interaction.response.send_message(f"School abbreviation '{school_abbr}' not found. Please add the school first.", ephemeral=True)
        return
    if school_abbr not in config['roles']:
        config['roles'][school_abbr] = []
    role_id = role.id
    if role_id not in config['roles'][school_abbr]:
        config['roles'][school_abbr].append(role_id)
        save_config(config)
        await interaction.response.send_message(f"Added role {role.mention} to school {school_abbr}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Role {role.mention} is already associated with school {school_abbr}.", ephemeral=True)

bot.tree.add_command(add_group)

# Create 'remove' command group
class RemoveGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name='remove', description='Commands to remove things', default_permissions=discord.Permissions(administrator=True))

remove_group = RemoveGroup()

@remove_group.command(name="school", description="Removes a school from the list of selectable schools.")
@app_commands.describe(school_abbr="Abbreviation of the school to remove")
async def remove_school(interaction: discord.Interaction, school_abbr: str):
    """Removes a school from the list of selectable schools."""
    # Find the school name by abbreviation
    school_name = None
    for name, info in config['schools'].items():
        if info['abbreviation'] == school_abbr:
            school_name = name
            break
    if not school_name:
        await interaction.response.send_message(f"School with abbreviation '{school_abbr}' not found.", ephemeral=True)
        return
    # Remove the school
    del config['schools'][school_name]
    # Remove associated roles
    if school_abbr in config['roles']:
        del config['roles'][school_abbr]
    save_config(config)
    await interaction.response.send_message(f"Removed school with abbreviation {school_abbr} and associated roles.", ephemeral=True)

@remove_group.command(name="role", description="Removes a role associated with a school abbreviation.")
@app_commands.describe(school_abbr="Abbreviation of the school", role="Role to remove")
async def remove_role(interaction: discord.Interaction, school_abbr: str, role: discord.Role):
    """Removes a role associated with a school abbreviation."""
    if school_abbr in config['roles']:
        role_id = role.id
        if role_id in config['roles'][school_abbr]:
            config['roles'][school_abbr].remove(role_id)
            save_config(config)
            await interaction.response.send_message(f"Removed role {role.mention} from school {school_abbr}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Role {role.mention} is not associated with school {school_abbr}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"No roles are configured for school abbreviation '{school_abbr}'.", ephemeral=True)

bot.tree.add_command(remove_group)

# Create 'set' command group for setting configurations
class SetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name='set', description='Commands to set configurations', default_permissions=discord.Permissions(administrator=True))

set_group = SetGroup()

@set_group.command(name="notificationchannel", description="Sets the channel for new school notifications.")
@app_commands.describe(channel="Channel to send notifications to")
async def set_notification_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Sets the channel where notifications for new schools are sent."""
    config['notification_channel_id'] = channel.id
    save_config(config)
    await interaction.response.send_message(f"Notification channel set to {channel.mention}.", ephemeral=True)

bot.tree.add_command(set_group)

# Error handler for app commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    else:
        # Handle other errors or re-raise
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        raise error

# Sync the tree commands
@bot.event
async def on_ready():
    bot.add_view(JoinView())
    await bot.tree.sync()
    print(f'Logged in as {bot.user.name}')

bot.run(TOKEN)
