# 🌐 intelligence-hub-mcp

> Multi-Domain Intelligence Intake, 80:20 Crossover Synthesis & Publishing MCP Server

異なる複数の先端分野（AI/バイブコーディング、合成生物学、神経科学、暗号資産、医療、リバースエンジニアリング）の最新動向を並行収集し、**80:20 パレート分離** ＆ **異分野交差点（Crossover）分析** を行って構造化インサイトを出力するインテリジェンス・ハブ MCP サーバー。

---

## 🏛️ Hermes エコシステム ＆ Tri-MCP アーキテクチャ

本 MCP サーバーは **Hermes AI Agent (Master Orchestrator)** の傘下で、学術深掘り（`ocr-mcp-server`）および自社メディア配信（`news-site-coral`）と対等なピアとして連携します。

```
                    ┌───────────────────────────────┐
                    │      🪐 Hermes AI Agent       │
                    │      (Master Orchestrator)    │
                    └───────┬───────────────┬───────┘
                            │               │
            ┌───────────────┴────┐     ┌────┴──────────────┐
            │ intelligence-hub-mcp│     │  ocr-mcp-server   │
            │  (80:20 Crossover) │     │ (Deep MAD Review) │
            └────────────────────┘     └───────────────────┘
                            │                   │
                            └─────────┬─────────┘
                                      ▼
                    ┌───────────────────────────────┐
                    │       news-site-coral         │
                    │  (WIRED Narrative Publishing) │
                    └───────────────────────────────┘
```

1. **多層インテーク (`intake/`)**:
   - **Type A (RSS/Atom)**: bioRxiv (SynthBio / Neuroscience), medRxiv, Zenn, Ethereum Research, Paradigm
   - **Type B (公開 API)**: Hacker News (Firebase API), arXiv (Atom API)
   - **Type C (ブラウザ/裏API)**: GitHub Trending (Phase 2)
   - **スマートスキップ**: `interval_hours` 判定により不要な頻回リクエストを自動防止
2. **知性化 & 永続化 (`storage/` & `analysis/`)**:
   - **LanceDB (PyArrow)**: `IntelligenceRecord` のメタデータ ＋ 768dim ベクトル埋め込み永続化
   - **80:20 パレート分析**: 定点観測 80% ＋ セレンディピティ飛び地 20%
   - **クロスオーバー抽出**: 異なるジャンル間の構造的アナロジーと相互応用可能性を LLM で抽出
3. **パブリッシュ & 連携 (`mcp/`)**:
   - 構造化データ（`CrossoverDigest`）に `suggested_themes` / `suggested_tags` を付与し、Hermes Agent を通じて **X (140字スレッド)** / **Note (エッセイ)** / **Coral Magazine (WIRED型3段構成HTML)** へマルチチャネル配信。

---

## 🚀 クイックスタート

### 依存関係の同期
```bash
uv sync --all-groups
```

### テストの実行
```bash
uv run pytest
```

### レイヤー境界検証 (Spaghetti Guard)
```bash
npx @naoya.k/spaghetti-guard check
```

### 定期収集 CLI の実行 (Cron / 一括実行)
```bash
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
