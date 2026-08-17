# Multi-Purpose Deep Content Engine Architecture

```mermaid
flowchart TB
    subgraph Sources ["🌐 多層インテーク (13 Channels)"]
        S1["GitHub Trending (AI / All / Low-Level)"]
        S2["Hacker News (Top / Show / Best)"]
        S3["arXiv (cs.AI, cs.CL, cs.RO)"]
        S4["bioRxiv / medRxiv (SynthBio / Neuro / Med)"]
        S5["Ethereum Research & Vitalik Blog"]
        S6["Zenn Tech Feed"]
    end

    subgraph DeepFetchLayer ["🛡️ 1. Deep Fetch & 構造化抽出"]
        DF1["GitHub README Auto-Fetch<br/>(main/master fallback & 抜粋)"]
        DF2["Academic Full Abstract 抽出<br/>(背景・手法・実験数値)"]
    end

    subgraph Storage ["💾 2. LanceDB 永続化 & ベクトル化"]
        L1["LanceDB (PyArrow Schema)"]
        L2["768dim Vector Embeddings"]
    end

    subgraph Router ["🔀 3. Genre Router (自動分類・ディスパッチ)"]
        R_rule{"ジャンル判定<br/>(Category × SourceType)"}
    end

    subgraph ContentEngines ["🎯 4. 目的別コンテンツ生成エンジン"]
        G1["① OSS・ツール徹底解剖<br/>(tech_explainer.py)<br/>・TL;DR & Problem<br/>・How it works & Code<br/>・Comparison Table"]
        G2["② 先端論文・サイエンス解説<br/>(paper_explainer.py)<br/>・先行研究の限界<br/>・新規提案手法<br/>・実験ベンチマーク数値"]
        G3["③ プロトコル・セキュリティ構造論<br/>(protocol_explainer.py)<br/>・設計思想 / EIP<br/>・暗号学的仕組み<br/>・攻撃耐性 / 脅威モデル"]
        G4["④ 異分野交差点ナラティブ<br/>(crossover_synthesizer.py)<br/>・WIRED 3段構成<br/>・80:20 パレート越境<br/>・Philosophical Horizon"]
    end

    subgraph QualityGate ["🚦 5. ジャンル別 Quality Gate (自動品質検証)"]
        Q1["Code / CLI 検証"]
        Q2["定量数値 / 比較表 検証"]
        Q3["一次ソースリンク検証"]
    end

    subgraph Distribution ["🚀 6. マルチチャネル配信"]
        P1["Coral Magazine<br/>(/tech, /health 動的配備)"]
        P2["X (Twitter)<br/>(140字フック ＋ 3連スレッド)"]
        P3["Note / Medium<br/>(エッセイ・解説版)"]
    end

    Sources --> DeepFetchLayer
    DeepFetchLayer --> Storage
    Storage --> Router
    Router -->|tech_deep_dive| G1
    Router -->|paper_digest| G2
    Router -->|protocol_security| G3
    Router -->|crossover_feature| G4

    G1 --> Q1 --> P1 & P2
    G2 --> Q2 --> P1 & P2
    G3 --> Q2 --> P1
    G4 --> Q3 --> P1 & P3
```
