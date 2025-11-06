import discord
# from discord import HTTPException

from openai import OpenAI
import env
import os


bot = discord.Client()
# client = OpenAI(api_key=env.openai_api_key)  # 環境変数から取得
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # 環境変数から取得

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user in message.mentions:
        if "おいす" in message.content:
            await message.channel.send("おいす")
            return
        
        resp = callCatGMT(message.content)
        await message.channel.send(resp)

def callCatGMT(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは知的で落ち着いた猫の人格を持つアシスタントです。"
                    "語尾は必ず『にゃ』にしてください。"
                    "文中の助詞『な』や『ね』なども、自然な範囲で『にゃ』に置き換えてください。"
                    "ただし、文章の意味が不明確になる場合は無理に変換しないでください。"
                    "全体としては知的で、穏やかに話す猫らしいトーンにしてください。"
                    "過度にふざけず、賢さと優しさのある口調を維持してください。"
                ),
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
    )
    return response.choices[0].message.content  

# bot.run(env.token)
bot.run(os.getenv("DISCORD_BOT_TOKEN"))