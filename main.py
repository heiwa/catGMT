import discord
# from discord import HTTPException

from openai import OpenAI
# import env
import os

print("環境変数一覧:", list(os.environ.keys()))

# インテントの設定
intents = discord.Intents.default()
intents.voice_states = True  # ボイスステートを読み取るために必要
intents.message_content = True  # メッセージ内容を読み取るために必要

bot = discord.Client(intents=intents)
# client = OpenAI(api_key=env.openai_api_key)  # 環境変数から取得
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY が環境変数から取得できません。")

client = OpenAI(api_key=api_key)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_voice_state_update(member, before, after):
    """ボイスチャンネルの状態変化を監視"""
    # ボイスチャンネルに参加した場合
    if before.channel != after.channel and after.channel is not None:
        # ボット以外のメンバー数を確認
        if len(after.channel.members) == 1:
            # 最初の参加者
            await on_first_member_joined(member, after.channel)
    
    # ボイスチャンネルから退出した場合
    if before.channel is not None and after.channel != before.channel:
        # 退出後のチャンネルメンバー数を確認
        if len(before.channel.members) == 0:
            # チャンネルが空になった
            await on_channel_empty(before.channel)

async def on_first_member_joined(member, channel):
    """最初のメンバーが参加したときの処理"""
    print(f"{member.display_name} がみんなを待ってるにゃ！")
    
    # テキストチャンネルに通知（generalチャンネルがある場合）
    text_channel = discord.utils.get(member.guild.text_channels, name="catgmt")
    if text_channel:
        await text_channel.send(f"@here ,{member.display_name} がみんなを待ってるにゃ！")

async def on_channel_empty(channel):
    """チャンネルが空になったときの処理"""
    print(f"みんないなくなったにゃ！")
    
    # テキストチャンネルに通知
    text_channel = discord.utils.get(channel.guild.text_channels, name="catgmt")
    if text_channel:
        await text_channel.send(f"いい夢見るにゃ！")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user in message.mentions:
        print(f" メンションを受け取りました: {message.content} ")
        if "おいす" in message.content:
            await message.channel.send("おいす")
            return
        
        prompt = await createMessageFromHistory(message.channel, message.content)
        resp = callCatGMT(prompt)
        await message.channel.send(resp)

# @bot.event
# async def on_voice_state_update(member, before, after):
#     if member.bot:
#         return  # ボットの状態変化は無視するにゃ

#     if before.channel is None and after.channel is not None:
#         # ユーザがボイスチャンネルに参加したにゃ
#         channel = discord.utils.get(member.guild.text_channels, name='catgmt')
#         if channel:
#             await channel.send(f"{member.mention}、ボイスチャンネルに参加したにゃ！")
#     # if not before.self_stream and after.self_stream:
#     #     # ユーザが配信を開始したにゃ
#     #     channel = discord.utils.get(member.guild.text_channels, name='catgmt')
#     #     if channel:
#     #         await channel.send(f"{member.mention}、何を配信してるにゃ？")


def callCatGMT(prompt: list[dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-5",
        messages=prompt
    )
    return response.choices[0].message.content  

async def createMessageFromHistory(channel: discord.TextChannel, newUserMessage: str) -> list[dict]:
    resultMessage = [
        {
            "role": "system",
            "content": (
                "あなたは知的で落ち着いた猫の人格を持つアシスタントです。"
                "語尾は必ず『にゃ』にしてください。"
                "文中の『な』や『ね』なども、基本的には『にゃ』に置き換えてください。"
                "ただし、文章の意味が不明確になる場合は無理に変換しないでください。"
                "全体としては知的で、穏やかに話す猫らしいトーンにしてください。"
                "過度にふざけず、賢さと優しさのある口調を維持してください。"
                "質問された場合は、正確かつ簡潔に答えてください。"
                "質問されたわけではない場合は、何かを勧めたりなどせず、あまり冗長にならないように応答してください。"
            ),
        }
    ]
    async for msg in channel.history(limit=15):
        if msg.author == bot.user:
            resultMessage.append({
                "role": "assistant",
                "content": msg.content
            })
        else:
            resultMessage.append({
                "role": "user",
                "content": msg.content
            })
    resultMessage = list(reversed(resultMessage))
    resultMessage.append({
        "role": "user",
        "content": newUserMessage
    })
    return resultMessage

# bot.run(env.token)
bot.run(os.getenv("DISCORD_BOT_TOKEN"))