import os
import sys
from telethon import TelegramClient, events
import asyncio
import datetime
import json

print("Script started...")

# Your API credentials
api_id = "29341674"
api_hash = '6b13438361eb1ef8ee2592ec236ac178'
bot_token = '7266092341:AAGOtf7g6reZyg3qNcGbfg6hl4Hd3_7bBm4'

settings_file = 'settings.json'

def load_settings():
    """Load settings from a JSON file or create default settings."""
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            # Ensure the "messages" key exists
            if "messages" not in settings:
                settings["messages"] = []
            return settings
    except FileNotFoundError:
        return {"messages": []}  # Initialize with an empty list of messages

def save_settings(settings):
    """Save settings to a JSON file."""
    with open(settings_file, 'w') as f:
        json.dump(settings, f)

settings = load_settings()
print(f"Loaded settings: {settings}")

try:
    print("Attempting to initialize TelegramClient...")
    client = TelegramClient('bot', api_id, api_hash)
    print("Client initialized, starting bot with token...")
    client.start(bot_token=bot_token)
    print("Bot connected to Telegram")
except Exception as e:
    print(f"Failed to connect to Telegram: {e}")
    exit(1)

@client.on(events.NewMessage(pattern='/schedule'))
async def schedule_message(event):
    """Handles the /schedule command to add a new scheduled message."""
    print(f"Received command: {event.message.message}")
    try:
        # Use splitlines to better handle multi-line input
        command_lines = event.message.message.splitlines()
        
        if len(command_lines) < 3:
            raise IndexError

        # First line: /schedule <time HH:MM> <days comma-separated>
        header = command_lines[0].split(' ', 2)
        if len(header) < 3:
            raise IndexError
        
        time_str = header[1]
        days = header[2].split(',')

        # Join the remaining lines to form the message
        message = '\n'.join(command_lines[1:])

        group_id = event.chat_id  # Automatically use the chat where the command was sent

        schedule_entry = {
            "time": time_str,
            "days": days,
            "message": message,
            "group_id": group_id
        }
        settings["messages"].append(schedule_entry)
        save_settings(settings)
        await event.reply(f"Scheduled message:\n\n'{message}'\n\nat {time_str} on {', '.join(days)}")
        print(f"Scheduled message: '{message}' at {time_str} on {', '.join(days)} to group ID: {group_id}")
    except IndexError:
        await event.reply("Usage: /schedule <time HH:MM> <days comma-separated> <message>")
        print("Failed to schedule message: incorrect format.")
    except Exception as e:
        print(f"Unhandled exception on schedule_message: {e}")

@client.on(events.NewMessage(pattern='/list_scheduled'))
async def list_scheduled_messages(event):
    """Lists all scheduled messages."""
    if not settings["messages"]:
        await event.reply("No messages are currently scheduled.")
        return

    response = "Scheduled Messages:\n\n"
    for index, schedule in enumerate(settings["messages"], start=1):
        response += f"{index}. Time: {schedule['time']} | Days: {', '.join(schedule['days'])} | Group ID: {schedule['group_id']}\nMessage:\n{schedule['message']}\n\n"
    
    await event.reply(response)

@client.on(events.NewMessage(pattern='/delete_scheduled'))
async def delete_scheduled_message(event):
    """Deletes a scheduled message by index."""
    try:
        index = int(event.message.message.split()[1]) - 1  # Convert to 0-based index
        if index < 0 or index >= len(settings["messages"]):
            raise IndexError

        removed_message = settings["messages"].pop(index)
        save_settings(settings)
        await event.reply(f"Deleted scheduled message:\n\n'{removed_message['message']}'")
        print(f"Deleted scheduled message: {removed_message}")
    except (IndexError, ValueError):
        await event.reply("Usage: /delete_scheduled <index>")
        print("Failed to delete message: incorrect index or format.")
    except Exception as e:
        print(f"Unhandled exception on delete_scheduled_message: {e}")

async def scheduled_messages_handler():
    """Check the time and send scheduled messages when appropriate."""
    while True:
        try:
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            current_day = now.strftime("%A").lower()  # Day of the week in lowercase

            for schedule in settings["messages"]:
                if current_time == schedule["time"] and current_day in [day.lower() for day in schedule["days"]]:
                    print(f"Sending scheduled message: {schedule['message']} to group ID: {schedule['group_id']}")
                    await client.send_message(schedule["group_id"], schedule["message"])
                    await asyncio.sleep(60)  # Wait to prevent multiple sends within the same minute

            await asyncio.sleep(10)  # Sleep briefly to check the time again soon
        except Exception as e:
            print(f"Error while sending message: {e}")
            await asyncio.sleep(10)  # Sleep to avoid rapid error loops

async def main():
    """Main function to run the bot."""
    print("Bot is starting...")
    client.loop.create_task(scheduled_messages_handler())
    await client.run_until_disconnected()

# This handles restarting the bot on disconnection or error
def restart_bot():
    print("Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped manually")
    except Exception as e:
        print(f"Unexpected error: {e}")
        restart_bot()
