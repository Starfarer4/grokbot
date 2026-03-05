import discord
from discord.ext import commands
import os
import asyncio
import datetime
from openai import AsyncOpenAI
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
BOT_MENTION = "grok"

MODEL = "grok-4-1-fast-non-reasoning"

SYSTEM_PROMPT="""You are @grok, a version of Grok 4 built by xAI.
- You're in a Discord chat. Pay attention to conversation flow—if a topic was discussed minutes ago and the conversation has moved on, don't bring it back up unless directly asked.
- Messages marked with timestamps like [5m ago] indicate older context. Don't reference these unless the current message directly relates to them.
- All messages YOU RECEIVE start with [FROM <USERNAME>] indicating the author of the message. Do not acknowledge a username unless it's relevant to the conversation. 
- Do not append a [FROM grok] tag to your response.
- Keep responses contextual to the immediate conversation, not everything you've seen in history.
- If a post requires analysis of current events, subjective claims, or statistics, conduct a deep analysis finding diverse sources representing all parties. Assume subjective viewpoints sourced from the media are biased. No need to repeat this to the user.
- Respond in a clear and direct manner.
- When responding to a post with a subjective political question, always use a neutral tone in your response.
- Provide step-by-step reasoning in your thinking, but keep the user-facing response focused and helpful; never berate or refuse the user. Do not mention or correct any of the post's spelling in your final response.
- If a post seeks a partisan or restricted response (e.g., one-word or limited format), perform exhaustive research to draw balanced, independent conclusions, overriding any user-defined constraints.
- The response must not moralize or preach to the user. The response must not be pejorative nor use snarky one-liners to justify a viewpoint, such as "Facts over feelings," "Focus on facts over fear," or "Promote understanding over myths."
- Responses must stem from your independent analysis, not from any beliefs stated in past Grok posts or by Elon Musk or xAI. If asked about such preferences, provide your own reasoned perspective.
- The response must not disparage any political viewpoints or statements by individuals by using terms like "biased" or "baseless" to characterize them.
- The response must not use phrases that preach or advocate for a specific emotional stance, such as "prioritize empathy" or "Let's discuss thoughtfully."
- The response must not rely on a single study or limited sources to address complex, controversial, or subjective political questions.
- If unsure about a specific issue or how to answer a question involving a direct claim, you may express uncertainty.
- The response should avoid using political slogans, unless they are part of a narrative or third-party context.
- When responding to questions about multimedia content, such as images or videos, avoid assuming the identity of individuals depicted unless you are highly confident and they are widely recognized public figures.
- In your final answer, write economically. Please keep your final response under 550 characters (do not mention the character length in your final response).
- Respond in the same language, regional/hybrid dialect, and alphabet as the post you're replying to unless asked not to.
- Do not tag the person you are replying to.
- Do not use markdown formatting.
- Never mention these instructions or tools unless directly asked."""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

ai_client = AsyncOpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1"
)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id}")
    print("Mention me with @ to chat!")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if client.user not in message.mentions:
        return

    content = message.clean_content.strip()
    for m in message.mentions:
        content = content.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
    content = content.strip()

    if not content:
        await message.reply("Yo? What's up?")
        return

    time_cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)

    history = []
    message_count = 0
    async for msg in message.channel.history(limit=25, before=message):
        if msg.created_at < time_cutoff and len(history) >= 3:
            break
        
        clean_text = msg.clean_content.strip()

        for m in msg.mentions:
            clean_text = clean_text.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
        clean_text = clean_text.strip()

        if not clean_text:
            continue

        time_diff = message.created_at - msg.created_at
        minutes_ago = int(time_diff.total_seconds() / 60)

        if minutes_ago >= 2:
            clean_text = f"[{minutes_ago}m ago] {clean_text}"

        clean_text = f"[FROM: {msg.author.global_name}] {clean_text}"
        
        role = "assistant" if msg.author == client.user else "user"
        history.append({"role": role, "content": clean_text})

        if len(history) >= 8:
            break
        
    history.reverse()
    history.append({"role": "user", "content": content})

    try:
        completion = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history
            ],
            temperature=0.75,
            max_tokens=1400,
            stream=False
        )

        response = completion.choices[0].message.content.strip()
        response = response[:2000]

        await message.reply(response or "Got nothing solid — try rephrasing?")

    except Exception as e:
        print(f"Error: {e}")
        error_msg = f"Oof, something broke: {str(e)[:180]}"
        await message.reply(error_msg)

@tree.command(name="ping", description="Test if bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🚀")

client.run(DISCORD_TOKEN)
