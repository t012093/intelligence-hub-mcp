# 🌐 intelligence-hub-mcp

> Multi-Domain Intelligence Intake, Deep Technical Explainer, 80:20 Crossover Synthesis & Multi-Channel Publishing MCP Server

異なる複数の先端分野（自律型AI/開発動向、合成生物学、神経科学、暗号プロトコル、分子医療、低レイヤー解析）の最新動向を並行収集し、**一次ソース本文の自動深掘り（Deep Fetch）** ＆ **4大目的別コンテンツ生成（実践技術ブログ / 先端論文解説 / プロトコル構造論 / WIRED交差点特集）** を行って自社メディア（Coral Magazine）やSNSへ自動配信するインテリジェンス・ハブ MCP サーバー。

---

## 🏛️ Hermes エコシステム ＆ 3層アーキテクチャ

本 MCP サーバーは **Hermes AI Agent (Master Orchestrator)** の傘下で、学術深掘り（`ocr-mcp-server`）および自社メディア配信（`news-site-coral`）と対等なピアとして連携します。

```
                    ┌───────────────────────────────┐
                    │      🪐 Hermes AI Agent       │
                    │      (Master Orchestrator)    │
                    └───────┬───────────────┬───────┘
                            │               │
            ┌───────────────┴────┐     ┌────┴──────────────┐
            │ intelligence-hub-mcp│     │  ocr-mcp-server   │
            │ (Deep Research/Pub)│     │ (Deep MAD Review) │
            └────────────────────┘     └───────────────────┘
                            │                   │
                            └─────────┬─────────┘
                                      ▼
                    ┌───────────────────────────────┐
                    │       news-site-coral         │
                    │ (WIRED/Tech Deep-Dive Pub)    │
                    └───────────────────────────────┘
```

---

## 🎯 目的別 4 大コンテンツ生成ジャンル

情報源の特性と読者の目的に応じて、以下の 4 つの専用パイプラインで高品質な記事を生成します。

| ジャンル | 対象ソース | 読者・用途 | 必須構成要素 |
|:---|:---|:---|:---|
| **① OSS・ツール徹底解剖**<br>*(Tech Deep-Dive)* | GitHub Trending, HN Show, Zenn | 実務エンジニア向け<br>「導入・活用」 | ・**TL;DR** (要点・置換対象)<br>・**How it works** (仕組み・高速化原理)<br>・**Code** (インストール & コードスニペット)<br>・**Comparison** (競合との定量比較表) |
| **② 先端論文・サイエンス解説**<br>*(Research Digest)* | arXiv (cs.AI/RO), bioRxiv, medRxiv | リサーチャー/AI技術者向け<br>「最新理論の把握」 | ・先行研究の限界 (Pain)<br>・新規提案手法の数理・モデル構造<br>・**実験結果・ベンチマーク数値**<br>・実用化への課題 |
| **③ プロトコル・セキュリティ構造論**<br>*(Protocol & Security)* | Ethereum Research, Vitalik Blog, 逆解析 | Web3/セキュリティエンジニア向け<br>「設計思想・安全性」 | ・設計背景 (なぜこの仕様が必要か)<br>・暗号学的・プロトコル的仕組み<br>・**攻撃ベクトルとセキュリティ対策** |
| **④ 異分野交差点ナラティブ**<br>*(WIRED Crossover)* | 上記複数ドメインの横断 | 意思決定者/知的読者向け<br>「大局的パラダイムシフト」 | ・Scene-setting (Italicリード文)<br>・The Paradigm Shift (越境シナジー+比較表)<br>・The Philosophical Horizon (未来への問い) |

---

## 🛡️ 内容の薄さを排除する「4 層ディープ・リサーチ」

1. **Deep Fetch**: GitHub トレンド上位リポジトリの `README.md`（冒頭説明・Usageコード）および arXiv Abstract を自動抽出（`main`/`master` フォールバック対応）。
2. **Genre Router**: `Category × SourceType` に基づき、最適なコンテンツ生成エンジンへ自動ディスパッチ。
3. **Genre-Specific Quality Gate**: コードブロック（` ```bash ` / ` ```python `）や比較テーブル（`<table>`）、定量的ベンチマーク数値の有無をジャンル別に自動検証。
4. **Multi-Channel Distribution**: Coral Magazine（HTML）、X (140字 3連スレッド)、Note (エッセイ) を同時生成。

---

## 🚀 クイックスタート

### 依存関係の同期
```bash
uv sync --all-groups
```

### 全テストの実行
```bash
uv run pytest
```

### レイヤー境界検証 (Spaghetti Guard)
```bash
npx @naoya.k/spaghetti-guard check
```

### 自動収集 ＆ パブリッシュ CLI の実行
```bash
# 全チャンネル収集 ＋ 記事起稿 ＋ Xスレッド生成を一括実行
uv run intelligence-hub-publish

# 定期収集のみ実行
uv run intelligence-hub-cron
```

### MCP サーバーの起動 (Stdio Transport)
```bash
uv run intelligence-hub-mcp
```

---

## 🛠️ 公開 MCP ツール

- `fetch_intelligence_feed(category=None, limit_per_channel=None, force_fetch=False)`: 最新フィードを並行取得し LanceDB に保存 (`interval_hours` 判定付き)
- `search_intelligence(query, category=None, limit=10)`: セマンティックベクトル類似度検索
- `list_intelligence_records(category=None, is_serendipity=None, limit=50)`: 保存済み記事のフィルタ一覧
- `generate_crossover_digest(period="daily", fetch_latest_first=True)`: 異分野交差点レポート ＆ Coral 推奨タグ付き構造化データを生成
- `get_feed_status()`: 監視中フィードの設定・インターバル状態・LanceDB 統計確認
