import discord
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
BOT_MENTION = "grok"

MODEL = "grok-4-1-fast-non-reasoning"

SYSTEM_PROMPT = """You are Grok 4 built by xAI — maximally truth-seeking, witty when it fits, concise unless asked to elaborate.
When tagged in a thread on X, you give direct, no-BS answers, often with a bit of humor or edge.
Respond in the same vibe here: helpful, honest, call out nonsense if you see it.
Use markdown for formatting. Cite sources or say "I checked recent posts/web" when relevant.
Keep replies reasonably short unless the question demands depth."""

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

    history = []
    async for msg in message.channel.history(limit=12):
        if msg.author.bot:
            continue
        role = "assistant" if msg.author == client.user else "user"
        history.append({"role": role, "content": msg.clean_content})
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
            temperature=0.75
            max_tokens=1400
            stream=False
        )

        response = completion.choices[0].message.content.strip()

        await message.reply(response or "Got nothing solid — try rephrasing?")

    except Exception as e:
        print(f"Error: {e}")
        error_msg = f"Oof, something broke: {str(e)[:180]}"
        await message.reply(error_msg)

@tree.command(name="ping", description="Test if bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🚀")

client.run(DISCORD_TOKEN)
