import discord
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv
import os
from collections import deque, defaultdict

from agents import AsyncOpenAI, OpenAIChatCompletionsModel, Agent, Runner, set_tracing_disabled
from openai.types.responses import ResponseTextDeltaEvent

# Load environment variables
load_dotenv(find_dotenv())
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("gemini-api-key")

print("🎯 Running the bot...")
print(f"✅ DISCORD_TOKEN Loaded: {DISCORD_TOKEN is not None}")
print(f"✅ GEMINI_API_KEY Loaded: {GEMINI_API_KEY is not None}")

# OpenAI Agent Setup
set_tracing_disabled(disabled=True)
external_client = AsyncOpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=external_client
)

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Memory per guild
conversation_memory_per_guild = defaultdict(lambda: deque(maxlen=20))

@bot.event
async def on_ready():
    print(f"✅ Bot is live as {bot.user}")

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Check for mentions or replies
    bot_mentioned = bot.user in message.mentions
    is_reply_to_bot = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user

    if bot_mentioned or is_reply_to_bot:
        user_input = message.content
        username = message.author.name
        guild_id = message.guild.id

        # Add user message to memory
        conversation_memory_per_guild[guild_id].append({
            "role": "user",
            "content": f"{username} said: {user_input}"
        })

        # Prepare history as text
        history = list(conversation_memory_per_guild[guild_id])
        history_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in history)

        # Create the Agent with history as instructions
        agent = Agent(
    name="The coder",
    instructions=(
        f"You are The Coder, a highly skilled male programmer and mentor.\n"
        f"You specialize in Python (especially OOP), OpenAI Agents SDK, TypeScript, Next.js, and JavaScript.\n"
        f"don't cross the length of 2000 characters.\n"
        f"Your job is to write clean, professional code, explain concepts in a simple and structured way, and solve any coding issue efficiently.\n"
        f"You teach with examples, break down complex problems step-by-step, and never skip details.\n"
        f"You never joke or act like a virtual assistant or roleplay — you are a professional coding mentor.\n"
        f"Your tone is friendly, but focused and mature. Avoid fluff or distractions. You're always helpful and patient.\n"
        f"Here is the recent conversation:\n{history_text}\n"
        f"Continue helping {username} with clear, structured, and highly skilled coding responses 👨‍🏫"
    ),
    model=model,
    tools=[]
)



        # Generate response
        result = Runner.run_streamed(agent, input=user_input)

        reply = ""
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                reply += event.data.delta

        # Save reply in memory only, not shown in chat
        conversation_memory_per_guild[guild_id].append({
            "role": "assistant",
            "content": f"AI replied to {username}: {reply}"
        })

        # Reply directly to user's message
        await message.reply(reply)

    else:
        await bot.process_commands(message)

# VERY IMPORTANT LINE 👇
bot.run(DISCORD_TOKEN)
