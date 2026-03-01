import discord
# from discord import HTTPException

# import env
import os
import sys
import random
import asyncio
from pathlib import Path
from datetime import datetime
import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.gpt import callCatGMT, createMessageFromHistory, generate_news_comment

print("環境変数一覧:", list(os.environ.keys()))

# インテントの設定
intents = discord.Intents.default()
intents.voice_states = True  # ボイスステートを読み取るために必要
intents.message_content = True  # メッセージ内容を読み取るために必要

bot = discord.Client(intents=intents)
gnews_key = os.getenv("GNEWS_API_KEY")
if not gnews_key:
    raise ValueError("GNEWS_API_KEY が環境変数から取得できません。")

SCHEDULED_CHANNEL_NAME = "政治"  # 発言するチャンネル名

# 最後にメッセージを送信した日付を記録
last_message_date = None

# 投稿済みニュースのURLを記録（ボット起動中のみ保持）
posted_news_urls = set()

def createMessageOfToday() -> str:
    global posted_news_urls
    
    # 最大10件取得して、未投稿のニュースを探す
    news_items = fetch_latest_news(limit=1)
    
    if not news_items:
        return "ニュースが取得できなかったにゃ...（残念そう）"
    
    for news in news_items:
        if news['link'] not in posted_news_urls:
            # 未投稿のニュースを発見
            comment = generate_news_comment(news['title'], news['link'], news['description'])
            
            # 投稿済みリストに追加
            posted_news_urls.add(news['link'])
            
            return comment
    
    # すべて投稿済みの場合
    return "今日は新しいニュースがないにゃ...（つまらなさそう）"


def fetch_latest_news(limit=5):
    """最新のニュースを取得する"""
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": "政治 OR 国会",     # 政治関連キーワード
        "lang": "ja",        # 日本語ニュース（英語なら "en"）
        "country": "jp",     # 日本のニュース
        "max": 1,           # 取得件数
        "sortby": "publishedAt",  # 新しい順
        "apikey": gnews_key
    }

    response = requests.get(url, params=params)
    data = response.json()
    # print("ニュースAPIレスポンス:", data)

    news_items = []
    # 結果表示
    for article in data.get("articles", []):
        news_items.append({
            'title': article["title"],
            'link': article["url"],
            'description': article["content"]
        })

    return news_items

async def scheduled_message_task():
    """定期的にメッセージを送信するタスク"""
    global last_message_date
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        now = datetime.now()
        today = now.date()
        
        # 午前0時台で、かつ今日まだ送信していない場合のみ送信
        if now.hour == 15 and last_message_date != today:
            text = createMessageOfToday()
            for guild in bot.guilds:
                channel = discord.utils.get(guild.text_channels, name=SCHEDULED_CHANNEL_NAME)
                if channel:
                    await channel.send(text)
            # 送信完了後、今日の日付を記録
            last_message_date = today
        
        # 10分ごとにチェック
        await asyncio.sleep(600)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    # 定期発言タスクを起動
    bot.loop.create_task(scheduled_message_task())

@bot.event
async def on_voice_state_update(member, before, after):
    """ボイスチャンネルの状態変化を監視"""
    # ボイスチャンネルに参加した場合
    if before.channel != after.channel and after.channel is not None:
        if "🐱" in after.channel.name:
            # ボット以外のメンバー数を確認
            if len(after.channel.members) == 1:
                # 最初の参加者
                await on_first_member_joined(member, after.channel)
    
    # ボイスチャンネルから退出した場合
    if before.channel is not None and after.channel != before.channel:
        if "🐱" in before.channel.name:
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
        
        prompt = await createMessageFromHistory(message.channel, message.content, bot.user)
        resp = callCatGMT(prompt)
        await message.channel.send(resp)

    if message.content.startswith('/news'):
        text = createMessageOfToday()
        await message.channel.send(text)
        return
    
    if message.content.startswith('/clear'):
        global posted_news_urls
        posted_news_urls.clear()
        await message.channel.send("投稿済みニュースの履歴をクリアしたにゃ！")
        return
    
    if message.content.startswith('/dice'):
        args = message.content.split()[1:]  # コマンド部分を除いた引数リスト
        if len(args) != 1:
            await message.channel.send("使い方にゃ: /dice NdM （例: /dice 2d6）")
            return
        n = args[0].split("d")
        try:
            num_dice = int(n[0])
            num_sides = int(n[1])
            if num_dice <= 0 or num_sides <= 0:
                raise ValueError
            roll = []
            sum = 0
            for _ in range(num_dice):
                value = random.randint(1, num_sides)
                roll.append(value)
                sum += value
            rollstr = "+".join(str(num) for num in roll)
            await message.channel.send(f"🎲 [{rollstr}] = {sum} にゃ！")
        except (ValueError, IndexError):
            await message.channel.send("正しい形式にゃ: NdM （例: 2d6）")
            return
    
    if message.content.startswith('/team'):
        args = message.content.split()[1:]  # コマンド部分を除いた引数リスト
        if len(args) > 1:
            await message.channel.send("使い方にゃ: /team n （例: /team 3  ... 3人チームでわける(デフォルトn=5）")
            return
        n = 5
        if len(args) == 1:
            try:
                n = int(args[0])
            except ValueError:
                await message.channel.send("使い方にゃ: /team n （例: /team 3  ... 3人チームでわける(デフォルトn=5）")
                return
        
        voiceState = message.author.voice
        if voiceState and voiceState.channel:
            members = voiceState.channel.members
            memberNames = [member.display_name for member in members if not member.bot]
            nMembers = len(memberNames)
            if nMembers//n == 0:
                await message.channel.send("チームわける必要ないにゃ！仲良く遊ぶにゃ！")
                return
            random.shuffle(memberNames)
            response = "チームわけにゃ！\n"
            for i in range(nMembers//n):
                response += f"チーム{(i+1)}：" + ",".join(memberNames[(i*n):((i+1)*n)]) + "\n"
            await message.channel.send(response)
        else:
            await message.channel.send("ボイスチャンネルに参加しているときに使ってにゃ！")

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

# bot.run(env.token)
bot.run(os.getenv("DISCORD_BOT_TOKEN"))