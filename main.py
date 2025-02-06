import datetime
import json
import telebot
from telebot import types
import pytz
from dotenv import load_dotenv
import os
import threading

# Load environment variables from .env file
load_dotenv()

# Get the token from the environment variable
TOKEN = os.getenv("TOKEN")

# Create a Telegram bot object
bot = telebot.TeleBot(TOKEN)

current_station = ""

# Function to load subscribed users from a file
def load_subscribed_users():
    if os.path.exists("subscribed_users.txt"):
        with open("subscribed_users.txt", "r") as file:
            return [line.strip() for line in file.readlines()]
    return []

# Function to send a message to all subscribed users
def notify_subscribed_users(message):
    subscribed_users = load_subscribed_users()
    for user_id in subscribed_users:
        try:
            msg = bot.send_message(user_id, message)
            # Schedule the message to be deleted after 10 seconds
            threading.Timer(10, bot.delete_message, args=(user_id, msg.message_id)).start()
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

# Notify all subscribed users when the bot starts
notify_subscribed_users("Service Started! You can now check the Train Schedule using /start")

# Handle '/start' command
@bot.message_handler(commands=['start'])
def start_command(message):
    global init_msg
    global user
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton(text="Timetable", callback_data="back"))
    keyboard.add(types.InlineKeyboardButton(text="GitHub Repository", url="https://github.com/Owais5514/Dhaka-MRT-Timetable"))
    init_msg = bot.send_message(message.chat.id, "Welcome to Dhaka MRT 6!", reply_markup=keyboard)
    user = message.from_user.first_name
    print(f"User: {user} executed /start command")
    # Add user to subscribed users list
    with open("subscribed_users.txt", "a") as file:
        file.write(f"{message.chat.id}\n")

# Handle '/help' command
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "Welcome to Dhaka MRT 6 Bot!\n\n"
        "Available commands:\n"
        "/start - Start the bot and display the main menu\n"
        "/help - Display this help message\n"
        "/unsubscribe - Unsubscribe from notifications\n"
        "/schedule - Get the current train schedule\n"
        "/station - Get information about stations\n"
    )
    bot.send_message(message.chat.id, help_text)
    print(f"User: {message.from_user.first_name} executed /help command")

@bot.message_handler(commands=['unsubscribe'])
def unsubscribe_command(message):
    user_id = str(message.chat.id)
    subscribed_users = load_subscribed_users()
    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        with open("subscribed_users.txt", "w") as file:
            for user in subscribed_users:
                file.write(f"{user}\n")
        bot.send_message(message.chat.id, "You have been unsubscribed from notifications.")
    else:
        bot.send_message(message.chat.id, "You are not subscribed to notifications.")

# Handle button clicks
@bot.callback_query_handler(func=lambda call: True)
def button_click_handler(call):
    global current_station

    button_data = call.data
    current_station = button_data
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if current_station == "back":
        # Create a ReplyKeyboardMarkup object
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        # Add buttons to the keyboard
        stations = ["Uttara North", "Agargoan", "Uttara Center", "Bijoy Sarani", "Uttara South", "Farmgate", "Pallabi", "Karwan Bazar", "Mirpur 11", "Shahbag", "Mirpur 10", "Dhaka University", "Kazipara", "Bangladesh Secretariat", "Sewrapara", "Motijheel"]
        for i in range(0, len(stations), 2):
            keyboard.add(types.InlineKeyboardButton(text=stations[i], callback_data=stations[i]),
                         types.InlineKeyboardButton(text=stations[i+1], callback_data=stations[i+1]))
        # Send the keyboard to the user
        bot.edit_message_text("Choose your current station:", chat_id, message_id, reply_markup=keyboard)
    else:
        input_time = datetime.datetime.now(pytz.timezone('Asia/Dhaka')).strftime("%H:%M")
        input_datetime = datetime.datetime.strptime(input_time, '%H:%M')

        # Get the current day in Dhaka timezone
        current_day = datetime.datetime.now(pytz.timezone('Asia/Dhaka')).strftime("%A")

        # Determine the correct file to open based on the current day
        if current_day == 'Saturday':
            file_path = '/workspaces/Dhaka-MRT-Timetable/mrt-6-sat.json'
        elif current_day == 'Friday':
            file_path = '/workspaces/Dhaka-MRT-Timetable/mrt-6-fri.json'
        else:
            file_path = '/workspaces/Dhaka-MRT-Timetable/mrt-6.json'

        with open(file_path) as f:
            data = json.load(f).get(str(current_station))

        next_closest_times_1 = sorted(data.get("Motijheel"), key=lambda x: (datetime.datetime.strptime(x, '%H:%M') - input_datetime).total_seconds() if datetime.datetime.strptime(x, '%H:%M') > input_datetime else float('inf'))[:3]
        next_closest_times_2 = sorted(data.get("Uttara North"), key=lambda x: (datetime.datetime.strptime(x, '%H:%M') - input_datetime).total_seconds() if datetime.datetime.strptime(x, '%H:%M') > input_datetime else float('inf'))[:3]

        # Create a new inline keyboard
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        # Add inline buttons to the keyboard
        keyboard.add(types.InlineKeyboardButton(text=f"Platform 1 : {', '.join(next_closest_times_1)}", callback_data="back"))
        keyboard.add(types.InlineKeyboardButton(text=f"Platform 2 : {', '.join(next_closest_times_2)}", callback_data="back"))
        # Add the Back button to the bottom of the keyboard
        keyboard.add(types.InlineKeyboardButton(text="Select Station", callback_data="back"))

        # Send the inline keyboard to the user
        bot.edit_message_text(f"Upcoming Trains at {current_station}\n(Time:{input_time})\n ", chat_id, message_id, reply_markup=keyboard)

        print(f"Chat ID: {call.message.chat.id}")
        print(f"Current Station: {current_station}")
        # print(f"Platform 1 : {', '.join(next_closest_times_1)}")
        # print(f"Platform 2 : {', '.join(next_closest_times_2)}")

# Create a handler for text messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_response = message.text
    with open("responses.txt", "a") as file:
        file.write(f"{message.from_user.username}: {user_response}\n")
    bot.reply_to(message, "Your response has been recorded.")

# Start the Telegram bot
bot.infinity_polling()