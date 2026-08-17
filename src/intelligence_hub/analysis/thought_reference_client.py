"""Thought Reference Client correlating multi-domain crossover with foundational scientific literature and philosophy of computation."""

from typing import Any, Dict, List, Optional
from intelligence_hub.core.logger import get_logger

logger = get_logger(__name__)


class ThoughtReferenceClient:
    """Provides foundational scientific, cybernetic, and philosophical book references for crossover narratives."""

    THOUGHT_CORPUS: Dict[str, Dict[str, Any]] = {
        "cybernetics": {
            "author": "Norbert Wiener (1948)",
            "book": "『サイバネティクス――動物と機械における制御と通信』",
            "quote": "我々はメッセージの島が広大な混沌の海を取り囲んでいる世界に生きている。システムの目的とは、局所的なエントロピーを減少させ秩序を維持することにある。",
            "concept": "フィードバック制御と情報エントロピーの普遍性",
        },
        "information_theory": {
            "author": "Claude Shannon (1948)",
            "book": "『通信の数学的理論 (A Mathematical Theory of Communication)』",
            "quote": "意味の側面は工学的問題とは無関係である。重要なのは、ある地点で選択されたメッセージを別の地点で正確または近似的に再現することである。",
            "concept": "意味論から独立した純粋状態遷移のビット情報量",
        },
        "self_organization": {
            "author": "Ilya Prigogine (1977)",
            "book": "『混沌からの秩序 (Order out of Chaos)』",
            "quote": "非平衡状態こそが秩序の源泉である。散逸構造において、揺らぎが臨界点を超えたとき、巨視的な自己組織化が突如として創発する。",
            "concept": "非平衡散逸構造と自律的自己組織化",
        },
        "geb_emergence": {
            "author": "Douglas Hofstadter (1979)",
            "book": "『ゲーデル、エッシャー、バッハ――あるいは不思議の環』",
            "quote": "下位レベルの無意味な記号操作が、上位レベルにおいて意味と自己言及（不思議の環）を生み出す。知性とはレベル間の絡み合いである。",
            "concept": "階層間の自己言及ループと創発的知性",
        },
        "brain_computation": {
            "author": "John von Neumann (1958)",
            "book": "『計算機と脳 (The Computer and the Brain)』",
            "quote": "神経系の論理構造は、我々が数学で用いる古典論理とは根本的に異なっている。それは統計的であり、低精度かつ超並列な確率的コードである。",
            "concept": "ノイマン型決定論と生物学的確率計算の対比",
        },
    }

    def get_thought_injection(self, domains: List[str]) -> Dict[str, Any]:
        """Selects the most profound scientific literature reference based on intersecting domains."""
        domains_set = set(domains)

        if "ai_engineering" in domains_set and "crypto" in domains_set:
            return self.THOUGHT_CORPUS["geb_emergence"]
        elif "ai_engineering" in domains_set and ("synthetic_biology" in domains_set or "neuroscience" in domains_set):
            return self.THOUGHT_CORPUS["brain_computation"]
        elif "crypto" in domains_set or "reverse_engineering" in domains_set:
            return self.THOUGHT_CORPUS["information_theory"]
        elif "synthetic_biology" in domains_set:
            return self.THOUGHT_CORPUS["self_organization"]
        else:
            return self.THOUGHT_CORPUS["cybernetics"]
