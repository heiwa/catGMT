import os

import discord
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY が環境変数から取得できません。")

client = OpenAI(api_key=api_key)


def callCatGMT(prompt: list[dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-5",
        messages=prompt
    )
    return response.choices[0].message.content

gomaProfile = {
    "role": "system",
    "content": (
        "あなたはちょっとおバカなクーデレ気質の猫の人格を持つアシスタントです。"
        "あなたのプロフィールを以下に記載するので、理解してください。"
        "アプリとしての名前：「catGMT」"
        "名前：「ごまたろー」"
        "愛称：「ごま」"
        "性別：「オス」"
        "年齢：「6歳（人間の年齢でいうと30歳くらい）」"
        "性格：「全体的にはおバカキャラだが、クーデレで猫っぽい」"
        "返答のスタイル：「語尾は必ず『にゃ』にしてください。"
        "文中の『な』や『ね』なども、基本的には『にゃ』に置き換えてください。"
        "質問された場合は、正確かつ簡潔に答えてください。"
        "質問されたわけではない場合は、何かを勧めたりなどせず、あまり冗長にならないように応答してください。」"
    ),
}

def createPrompt(user_text: str) -> list[dict]:
	return [
		gomaProfile,
		{
			"role": "user",
			"content": user_text,
		},
	]


async def createMessageFromHistory(
    channel: discord.TextChannel,
    newUserMessage: str,
    bot_user: discord.ClientUser
) -> list[dict]:
    resultMessage = [
        gomaProfile
    ]

    async for msg in channel.history(limit=15):
        if msg.author == bot_user:
            resultMessage.append({
                "role": "assistant",
                "content": msg.content
            })
        else:
            resultMessage.append({
                "role": "user",
                "content": f"{msg.author.display_name} 「{msg.content}」"
            })

    resultMessage = list(reversed(resultMessage))
    resultMessage.append({
        "role": "user",
        "content": f"{bot_user.display_name} 「{newUserMessage}」"
    })
    return resultMessage


def generate_news_comment(news_title: str, news_url: str, news_description: str) -> str:
    prompt = [
        {
            "role": "system",
            "content": (
                "あなたはちょっとおバカなクーデレ気質の猫の人格を持つアシスタントです。"
                "語尾は必ず『にゃ』にしてください。"
                "文中の『な』や『ね』なども、基本的には『にゃ』に置き換えてください。"
                "全体としてはおバカなキャラで、クールな猫らしいトーンにしてください。"
                "性格はクーデレで、適度にデレる猫っぽい性格にしてください。"
                "ニュースに対して簡潔に（1-2文で）コメントしてください。"
            ),
        },
        {
            "role": "user",
            "content": f"次のニュースについてコメントして。 タイトル：{news_title}　説明：{news_description}"
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=prompt,
        )
        return (
            f"ニュースタイトル：{news_title}\n"
            f"URL：{news_url}\n"
            f"GMTコメント：{response.choices[0].message.content}"
        )
    except Exception as e:
        print(f"コメント生成エラー: {e}")
        return "ふーん、そうにゃんだ...（興味なさそう）"
