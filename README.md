# catGMT (LINE + Discord on Railway)

このリポジトリは、Railway上で LINE Bot と Discord Bot を**別サービス**として分離デプロイできます。

## 分離デプロイ手順（推奨）

1. Railway で `New Project` → `Deploy from GitHub Repo` を選択
2. このリポジトリを接続
3. 同一プロジェクト内にサービスを2つ作成
   - `catgmt-line`（Web Service）
   - `catgmt-discord`（Worker Service）

## サービス別設定

### 1) LINEサービス（Web）

- Start Command: `python line_bot/main.py`
- 変数（例は `.env.line.example`）
  - `LINE_CHANNEL_ACCESS_TOKEN`
  - `LINE_CHANNEL_SECRET`
  - `OPENAI_API_KEY`
  - `PORT`（Railway側で自動注入されるため通常は未設定でも可）

デプロイ後、発行URLをLINE Developersに設定:

- Webhook URL: `https://<line-service-domain>/callback`
- `Use webhook` を有効化

### 2) Discordサービス（Worker）

- Start Command: `python discord_bot/main.py`
- 変数（例は `.env.discord.example`）
  - `DISCORD_BOT_TOKEN`
  - `OPENAI_API_KEY`
  - `GNEWS_API_KEY`

## 参考テンプレート

- `railway.line.json`（LINE向け設定例）
- `railway.discord.json`（Discord向け設定例）

※ Railwayの `railway.json` はリポジトリ全体に1つしか適用されるため、分離構成では各サービス設定画面で Start Command を個別指定する運用を推奨します。
