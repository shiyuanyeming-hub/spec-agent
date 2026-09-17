"""确定性文本相似度：不依赖模型与网络的字符级/数字级比较。

多语种一致性评分需要"可解释、可复现"的度量，因此这里只用纯函数：
- 字符 n-gram + 拉丁词向量的余弦相似度（回译后两侧同语言，词面重叠是有意义的信号）
- 数字集合的 Jaccard（验收标准里的 18pt / 3 步 / 4.5:1 这类阈值跨语种必须对得上）
"""
import math
import re
import unicodedata
from collections import Counter

WORD_RE = re.compile(r"[a-z0-9]+")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
SPACE_RE = re.compile(r"\s+")

NGRAM_SIZES = (2, 3)
EMBEDDING_DIM = 64


def normalize(text: str) -> str:
    """全角转半角、小写、压缩空白、去掉标点（只保留字母数字与 CJK）。"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text)).lower()
    kept = []
    for ch in text:
        if ch.isalnum() or ch.isspace():
            kept.append(ch)
    return SPACE_RE.sub(" ", "".join(kept)).strip()


def vector(text: str) -> Counter:
    """把文本变成"拉丁词 + 字符 n-gram"的多重集合。"""
    normalized = normalize(text)
    if not normalized:
        return Counter()
    compact = normalized.replace(" ", "")
    tokens: list[str] = WORD_RE.findall(normalized)
    for size in NGRAM_SIZES:
        if len(compact) >= size:
            tokens.extend(compact[i:i + size] for i in range(len(compact) - size + 1))
    return Counter(tokens)


def cosine_counters(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    dot = sum(left[t] * right[t] for t in common)
    if dot == 0:
        return 0.0
    norm_left = math.sqrt(sum(v * v for v in left.values()))
    norm_right = math.sqrt(sum(v * v for v in right.values()))
    return dot / (norm_left * norm_right)


def dice_counters(left: Counter, right: Counter) -> float:
    """多重集合的 Dice 系数（= F1）：对"同义改写但长度不同"比余弦更稳。"""
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    overlap = sum(min(left[t], right[t]) for t in common)
    total = sum(left.values()) + sum(right.values())
    return 0.0 if total == 0 else 2.0 * overlap / total


def containment(left: str, right: str) -> float:
    """left 有多少比例被 right 覆盖（用于判断"某语种漏了内容"）。"""
    left_vec, right_vec = vector(left), vector(right)
    if not left_vec:
        return 0.0
    common = set(left_vec) & set(right_vec)
    overlap = sum(min(left_vec[t], right_vec[t]) for t in common)
    return overlap / sum(left_vec.values())


def similarity(left: str, right: str) -> float:
    """0~1 的文本相似度（Dice）；任一侧为空时返回 0。

    回译文本通常是"同义改写"，长度与原文不同，因此用 Dice 而非余弦——
    余弦会被长度差异稀释，Dice 对改写更宽容，对"说的是另一件事"仍然敏感。
    """
    return dice_counters(vector(left), vector(right))


def numbers(text: str) -> set[str]:
    """提取数字（含小数），用于跨语种阈值比对。"""
    if not text:
        return set()
    normalized = unicodedata.normalize("NFKC", str(text))
    return {match.replace(",", "") for match in NUMBER_RE.findall(normalized)}


def numbers_similarity(left: str, right: str) -> float:
    """数字集合 Jaccard；两侧都没有数字视为一致（1.0）。"""
    left_numbers, right_numbers = numbers(left), numbers(right)
    if not left_numbers and not right_numbers:
        return 1.0
    union = left_numbers | right_numbers
    if not union:
        return 1.0
    return len(left_numbers & right_numbers) / len(union)


def best_match_scores(sources: list[str], targets: list[str]) -> list[float]:
    """每个 source 在 targets 中的最高相似度（用于对齐两边的验收标准）。"""
    if not targets:
        return [0.0 for _ in sources]
    return [max(similarity(source, target) for target in targets) for source in sources]


CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
KANA_RE = re.compile(r"[\u3040-\u30ff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def language_profile(text: str) -> dict[str, float]:
    """粗略的语种画像：CJK / 假名 / 拉丁字母占比（用于识别"回译没真的翻译"）。"""
    text = text or ""
    letters = len(CJK_RE.findall(text)) + len(KANA_RE.findall(text)) + len(LATIN_RE.findall(text))
    if letters == 0:
        return {"cjk": 0.0, "kana": 0.0, "latin": 0.0}
    return {
        "cjk": len(CJK_RE.findall(text)) / letters,
        "kana": len(KANA_RE.findall(text)) / letters,
        "latin": len(LATIN_RE.findall(text)) / letters,
    }


def matches_language(text: str, lang: str) -> bool:
    """判断文本是否"看起来是该语种"。回译结果不符合基准语种时，语义信号不可信。"""
    profile = language_profile(text)
    if lang == "zh":
        return profile["cjk"] >= 0.30
    if lang == "ja":
        return profile["cjk"] + profile["kana"] >= 0.30
    return profile["latin"] >= 0.50


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def hashed_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """确定性"伪嵌入"：把 n-gram 哈希进固定维度并做 L2 归一化（离线/测试用）。"""
    vec = [0.0] * dim
    for token, count in vector(text).items():
        index = hash_token(token) % dim
        vec[index] += float(count)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def hash_token(token: str) -> int:
    """跨进程稳定的哈希（避免 PYTHONHASHSEED 影响结果）。"""
    value = 2166136261
    for byte in token.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def cosine_vectors(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_left * norm_right)))
