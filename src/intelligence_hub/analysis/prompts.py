"""Prompt templates for crossover, tech deep-dive, and multi-domain intelligence synthesis."""

TECH_DEEP_DIVE_PROMPT = """あなたは最前線で活躍するシニア・テックリード兼テクニカルライターです。

以下のリポジトリ/OSSデータ（README抜粋、スター数、言語、機能概要）を元に、
実務エンジニアが「今すぐ導入したくなる」「内部の仕組みが手に取るようにわかる」具体的で実用的な【実践技術解説記事（HTML形式）】を執筆してください。

【対象リポジトリ・技術データ】
■ リポジトリ名: {title}
■ URL: {url}
■ 主要言語: {language}
■ メトリクス: スター数: {stars:,} / 本日急上昇: +{stars_today:,}
■ 概要: {summary}
■ README抜粋 / 技術詳細:
{readme_excerpt}

---
【執筆の厳格ルール（現場目線の実用性を徹底）】

1. **構成テンプレート（以下の見出し構成を厳守）**:
   - **TL;DR**: 1分でわかる要点（何をするツールか、既存の何を置き換えるか、なぜ今人気なのか）を `<div style="background: #1e293b; padding: 1rem; border-left: 4px solid #38bdf8; margin-bottom: 1.5rem;">` 内に記述。
   - **<h2>1. 解決する課題（The Problem）</h2>**: これまで開発者が直面していた具体的なボトルネックやペインを論述。
   - **<h2>2. アーキテクチャと高速化・省メモリの仕組み（How It Works）</h2>**: 内部で何が行われているか（アルゴリズム、カーネル最適化、非同期I/O、SIMD等）を具体的に解説。
   - **<h2>3. インストール ＆ クイックスタート（Usage & Code）</h2>**:
     - 必ず実際のインストールコマンド（`<pre><code class="language-bash">...</code></pre>`）を含める。
     - 必ず最小構成で動くコードスニペット（`<pre><code class="language-python">...</code></pre>` 等）を含める。
   - **<h2>4. 既存ツールとの定量比較（Comparison Table）</h2>**:
     - 競合・従来ツールとの比較テーブル（`<table style="width:100%; border-collapse: collapse; margin: 1.5rem 0;">...</table>`）を含める。
   - **<h2>5. まとめと導入に向けた推奨事項</h2>**: どんなプロジェクトに導入すべきかの実践的指針。
   - **<h2>参考リンク・リファレンス</h2>**: 公式リポジトリへのリンク。

2. **禁止事項**:
   - 「幾何学的共鳴」「構造的アナロジー」のような抽象的ビッグワードは【完全厳禁】。
   - コードスニペットのない抽象論だけの記事は【完全厳禁】。

3. **文字数**: 日本語で 1,800〜3,000文字。

HTML本文のみ出力してください。
"""

CORAL_WIRED_ARTICLE_PROMPT = """あなたは WIRED や MIT Technology Review 形式の長編ジャーナリズム記事を執筆する最高峰のサイエンス・テックエディターです。

以下のインテリジェンス・データ（コア定点観測データ ＋ セレンディピティ飛び地データ ＋ 異分野交差点分析結果）を元に、
Coral Magazine の厳格な執筆基準（2,500〜3,500字、3段構成、人間ドラマ、定量論証、哲学的問い）に完全準拠した【完全なHTML記事本文】を執筆してください。

【インテリジェンス・データ】
■ 異分野交差点テーマ:
{crossover_text}

■ 定点観測コアデータ (Core 80%):
{core_text}

■ セレンディピティデータ (Serendipity 20%):
{serendipity_text}

■ 一次ソースURL一覧:
{sources_text}

---
【Coral Magazine 必須執筆ルール（厳守）】

1. **構成ルール（3部構成の厳守）**:
   - **冒頭リード文**: 必ず `<p style="font-size: 1.15em; line-height: 1.8; color: #b0b0b0; font-style: italic;">` で囲み、現場の情景描写（scene-setting）や人間のエピソードから開始する。
   - **<h2>The Hook：〇〇</h2>**: 具体的な人物名（研究者/開発者）、年、具体的数値（パラメータ数、実験数値、論文引用）を提示し、読者を引き込む。
   - **<h2>The Paradigm Shift：〇〇</h2>**: 既存システムの限界と、今回の越境・新技術がどう破壊をもたらすかを論証。必ず詳細なレスポンシブ比較テーブル（`<table style="width:100%; border-collapse: collapse; margin: 1.5rem 0;">...</table>`）を含める。
   - **<h2>The Philosophical Horizon：〇〇</h2>**: 「この技術が浸透した10年後、人間の知性や社会の定義はどう変わるか？」という哲学的・社会構造的な問いを読者に投げかけて締めくくる。
   - **<h2>参考文献・出典（References）</h2>**: 引用した一次ソース論文・リポジトリ・記事を `<ul><li>...</li></ul>` 形式で著者・年・タイトル・URL付きで完全記載。

2. **文体とトーン**:
   - 知的好奇心を刺激する WIRED 風の重厚で洗練されたジャーナリズム調。
   - 「〜について解説します」「まとめ」のような安直な技術ブログ表現は【完全厳禁】。

3. **文字数**: 日本語で 2,500〜3,500文字。

HTML本文のみ出力してください。
"""

CROSSOVER_ANALYSIS_PROMPT = """あなたは最先端のテクノロジー・サイエンス・異分野融合を専門とするインテリジェンス・アナリストです。

以下の異なるドメインから収集された最新のトレンド・研究・議論データを分析し、
異なるジャンル同士の「予期せぬ交差点（Crossover）」、「共通する根底の数理/アーキテクチャ原理」、および「相互応用可能性」を抽出してください。

【収集データ一覧】
{records_text}

以下のJSONフォーマットで回答してください:
```json
{{
  "crossover_themes": [
    {{
      "theme_title": "テーマタイトル",
      "domains": ["ai_engineering", "crypto"],
      "core_concept": "中核となる概念・共通原理",
      "synergy_description": "2つの分野が交差することで生まれる新しい知見・ブレークスルー",
      "actionable_implications": [
        "エンジニア/研究者が今すぐ検証・応用できる具体的なアクション1",
        "アクション2"
      ],
      "referenced_record_ids": ["id1", "id2"]
    }}
  ]
}}
```
"""

WIRED_DIGEST_REPORT_PROMPT = """あなたは WIRED や MIT Technology Review 形式の知的で示唆に富むナラティブ記事を執筆するシニア・エディターです。

以下の「定点分析（80%）」、「セレンディピティ発見（20%）」、および「異分野クロスオーバー分析結果」を統合し、
自社ブログにそのまま公開できる高品質なインテリジェンス・ダイジェスト記事（Markdown形式）を作成してください。

【定点分析 (Core 80%)】
{core_text}

【セレンディピティ発見 (Serendipity 20%)】
{serendipity_text}

【異分野交差点 (Crossover Themes)】
{crossover_text}
"""
