import os
import sys
from collections import defaultdict, deque
from pathlib import Path

from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
	ApiClient,
	Configuration,
	MessagingApi,
	ReplyMessageRequest,
	TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.gpt import callCatGMT, gomaProfile

channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not channel_access_token:
	raise ValueError("LINE_CHANNEL_ACCESS_TOKEN が環境変数から取得できません。")
if not channel_secret:
	raise ValueError("LINE_CHANNEL_SECRET が環境変数から取得できません。")

app = Flask(__name__)
handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

MAX_HISTORY = 20
conversation_histories: dict[str, deque[dict]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))


def is_bot_mentioned(event: MessageEvent) -> bool:
	mention = getattr(event.message, "mention", None)
	if not mention:
		return False

	mentionees = getattr(mention, "mentionees", None) or []
	bot_user_id = os.getenv("LINE_BOT_USER_ID")

	for mentionee in mentionees:
		if getattr(mentionee, "is_self", False):
			return True

		mentionee_user_id = getattr(mentionee, "user_id", None)
		if bot_user_id and mentionee_user_id == bot_user_id:
			return True

		if hasattr(mentionee, "to_dict"):
			mentionee_dict = mentionee.to_dict()
			if mentionee_dict.get("isSelf") is True:
				return True
			if bot_user_id and mentionee_dict.get("userId") == bot_user_id:
				return True

	return False


def should_reply(event: MessageEvent) -> bool:
	source_type = getattr(event.source, "type", "")
	if source_type == "user":
		return True
	if source_type in {"group", "room"}:
		return is_bot_mentioned(event)
	return False


def get_conversation_key(event: MessageEvent) -> str:
	source = event.source
	source_type = getattr(source, "type", "unknown")

	if source_type == "user":
		return f"user:{getattr(source, 'user_id', 'unknown')}"
	if source_type == "group":
		return f"group:{getattr(source, 'group_id', 'unknown')}"
	if source_type == "room":
		return f"room:{getattr(source, 'room_id', 'unknown')}"
	return "unknown:unknown"


def create_prompt_with_history(event: MessageEvent, user_text: str) -> tuple[str, list[dict]]:
	conversation_key = get_conversation_key(event)
	history = list(conversation_histories[conversation_key])
	prompt = [gomaProfile, *history, {"role": "user", "content": user_text}]
	return conversation_key, prompt


def reply_text(reply_token: str, text: str) -> None:
	with ApiClient(configuration) as api_client:
		line_bot_api = MessagingApi(api_client)
		line_bot_api.reply_message(
			ReplyMessageRequest(
				reply_token=reply_token,
				messages=[TextMessage(text=text[:1000])],
			)
		)


@app.route("/callback", methods=["POST"])
def callback():
	signature = request.headers.get("X-Line-Signature", "")
	body = request.get_data(as_text=True)

	try:
		handler.handle(body, signature)
	except InvalidSignatureError:
		abort(400)

	return "OK"


@app.route("/", methods=["GET"])
def health_check():
	return "LINE bot is running", 200


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
	if not should_reply(event):
		return

	user_text = event.message.text

	if user_text.strip().lower() in {"/ping", "ping"}:
		reply = "pong にゃ"
	else:
		conversation_key, prompt = create_prompt_with_history(event, user_text)
		reply = callCatGMT(prompt)
		conversation_histories[conversation_key].append({"role": "user", "content": user_text})
		conversation_histories[conversation_key].append({"role": "assistant", "content": reply})

	reply_text(event.reply_token, reply)


if __name__ == "__main__":
	port = int(os.getenv("PORT", "8000"))
	app.run(host="0.0.0.0", port=port)
