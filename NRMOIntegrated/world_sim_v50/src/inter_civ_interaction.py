"""
Phase 11B: Inter-Civilization Interaction.

Each pair of civilizations interacts through 4 channels:
1. trade            — 双方の trade/assets 上昇
2. war              — shock 発生 (敵対側に大きい)
3. knowledge_diffusion — 受容側の edu/inst 上昇
4. disease_exchange — 双方に shock (Columbian-exchange型)

Interactions are gated by:
- era-dependent activity (ペアごとに era で active か否か)
- random per-generation triggering (probabilistic)
- intensity scaling

Historical examples encoded:
- Japan ↔ China: trade/knowledge_diffusion 主軸 (古代より深い)
- Japan ↔ Europe: war (戦国期鉄砲) → trade (南蛮貿易) → knowledge (蘭学)
- Europe ↔ Islamic: war (十字軍/レコンキスタ) + knowledge (アラビア科学)
- China ↔ Islamic: trade (シルクロード)
- Mongol shock (1260s): all civilizations
"""
import numpy as np


# Interaction event catalog: per-pair, per-era, per-channel intensity
# Format: {(civ_a, civ_b): {era_year_window: {channel: probability_per_year, intensity: 0-1}}}
INTERACTION_CATALOG = {
    # === Japan ↔ China ===
    ("Japan", "China"): [
        # year_start, year_end, channel, p_per_year, intensity
        (0, 700, "trade", 0.15, 0.5),
        (0, 700, "knowledge_diffusion", 0.20, 0.7),  # 仏教・漢字伝来
        (700, 1200, "trade", 0.12, 0.6),
        (700, 1200, "knowledge_diffusion", 0.10, 0.5),
        (1200, 1300, "war", 0.02, 0.8),               # 蒙古襲来 (1274/1281)
        (1300, 1600, "trade", 0.08, 0.4),
        (1600, 1850, "trade", 0.03, 0.3),             # 鎖国期
        (1850, 1945, "war", 0.05, 0.7),               # 日清戦争・日中戦争
        (1850, 1945, "knowledge_diffusion", 0.10, 0.4),
        (1945, 2021, "trade", 0.20, 0.6),
        (1945, 2021, "knowledge_diffusion", 0.10, 0.5),
    ],

    # === Japan ↔ Europe ===
    ("Japan", "Europe"): [
        (1500, 1640, "trade", 0.20, 0.5),             # 南蛮貿易
        (1500, 1640, "knowledge_diffusion", 0.15, 0.6),  # 蘭学・キリスト教
        (1500, 1640, "disease_exchange", 0.10, 0.3),
        (1640, 1850, "knowledge_diffusion", 0.05, 0.3), # 出島蘭学
        (1850, 1945, "knowledge_diffusion", 0.40, 0.9), # 明治近代化
        (1850, 1945, "trade", 0.30, 0.7),
        (1850, 1945, "war", 0.03, 0.8),               # 日露戦争・大戦
        (1945, 2021, "trade", 0.30, 0.6),
        (1945, 2021, "knowledge_diffusion", 0.20, 0.6),
    ],

    # === Japan ↔ Islamic ===
    ("Japan", "Islamic"): [
        (1500, 1700, "trade", 0.05, 0.2),             # 限定的接触
        (1850, 2021, "trade", 0.10, 0.3),
    ],

    # === China ↔ Europe ===
    ("China", "Europe"): [
        (0, 1200, "trade", 0.05, 0.3),                # シルクロード初期
        (1200, 1400, "trade", 0.08, 0.5),             # モンゴル時代の通商
        (1200, 1400, "disease_exchange", 0.20, 0.7),  # 黒死病経路
        (1400, 1800, "trade", 0.10, 0.5),             # 海路発見後
        (1800, 1945, "war", 0.05, 0.7),               # アヘン戦争・列強分割
        (1800, 1945, "knowledge_diffusion", 0.15, 0.5),
        (1945, 2021, "trade", 0.30, 0.7),
    ],

    # === China ↔ Islamic ===
    ("China", "Islamic"): [
        (0, 1500, "trade", 0.20, 0.6),                # シルクロード本流
        (0, 1500, "knowledge_diffusion", 0.10, 0.4),  # 製紙法等東伝
        (1500, 1900, "trade", 0.08, 0.3),
        (1900, 2021, "trade", 0.10, 0.4),
    ],

    # === Europe ↔ Islamic ===
    ("Europe", "Islamic"): [
        (700, 1100, "war", 0.10, 0.5),                # ウマイヤ・征服初期
        (700, 1100, "trade", 0.10, 0.4),
        (1100, 1300, "war", 0.20, 0.8),               # 十字軍
        (1100, 1300, "knowledge_diffusion", 0.25, 0.8),  # アラビア科学・古代復刻
        (1100, 1300, "disease_exchange", 0.05, 0.3),
        (1300, 1500, "war", 0.15, 0.7),               # レコンキスタ・ビザンツ陥落
        (1300, 1500, "trade", 0.15, 0.5),
        (1500, 1800, "war", 0.08, 0.5),               # オスマン勢力拡大
        (1500, 1800, "trade", 0.20, 0.6),             # 香料・絹貿易
        (1800, 1945, "war", 0.10, 0.6),               # 植民地化
        (1800, 1945, "knowledge_diffusion", 0.20, 0.5),
        (1945, 2021, "trade", 0.25, 0.5),
        (1945, 2021, "war", 0.05, 0.5),               # 中東紛争
    ],

    # === China ↔ Steppe (north Frontier) ===
    ("China", "Steppe"): [
        (0, 600, "war", 0.20, 0.6),                   # 匈奴・鮮卑との抗争
        (0, 600, "trade", 0.10, 0.4),
        (600, 1200, "war", 0.10, 0.5),                # 突厥・ウイグル
        (600, 1200, "knowledge_diffusion", 0.10, 0.4), # 仏教伝播 中央アジア経由
        (1200, 1368, "war", 0.30, 0.95),              # モンゴル征服 (元朝)
        (1200, 1368, "knowledge_diffusion", 0.20, 0.6),
        (1368, 1644, "war", 0.10, 0.5),               # 明朝の北辺防衛
        (1644, 1912, "war", 0.05, 0.4),               # 清の中央アジア支配
        (1644, 1912, "trade", 0.10, 0.3),
    ],

    # === Islamic ↔ Steppe ===
    ("Islamic", "Steppe"): [
        (700, 1200, "knowledge_diffusion", 0.15, 0.5), # イスラム伝播
        (700, 1200, "trade", 0.20, 0.6),               # シルクロード
        (1200, 1400, "war", 0.25, 0.8),                # モンゴル征服
        (1200, 1400, "knowledge_diffusion", 0.15, 0.6),
        (1400, 1700, "trade", 0.15, 0.5),              # ティムール朝
    ],

    # === Indic ↔ China ===
    ("China", "Indic"): [
        (0, 800, "knowledge_diffusion", 0.25, 0.7),    # 仏教伝来 (大) + 玄奘
        (0, 800, "trade", 0.10, 0.4),
        (800, 1500, "knowledge_diffusion", 0.15, 0.5),
        (800, 1500, "trade", 0.12, 0.4),
        (1500, 1900, "trade", 0.08, 0.3),              # 海上貿易減少
        (1900, 2021, "trade", 0.10, 0.4),
    ],

    # === Indic ↔ Islamic ===
    ("Indic", "Islamic"): [
        (700, 1200, "war", 0.10, 0.6),                 # アラブ侵攻 + ガズニ朝
        (700, 1200, "knowledge_diffusion", 0.15, 0.6), # 数学・天文学
        (1200, 1526, "war", 0.20, 0.8),                # スルタン朝 (デリー等)
        (1200, 1526, "knowledge_diffusion", 0.20, 0.7),
        (1526, 1757, "war", 0.05, 0.4),                # ムガル統治期 (内紛)
        (1526, 1757, "knowledge_diffusion", 0.15, 0.6), # ペルシア文化伝播
        (1526, 1757, "trade", 0.20, 0.5),
        (1947, 2021, "war", 0.05, 0.5),                # 印パ分離・紛争
    ],

    # === Indic ↔ Europe ===
    ("Europe", "Indic"): [
        (1500, 1757, "trade", 0.20, 0.6),              # 香料貿易
        (1757, 1947, "war", 0.10, 0.7),                # 英領インド支配
        (1757, 1947, "knowledge_diffusion", 0.30, 0.8), # 西洋教育・印刷術
        (1757, 1947, "disease_exchange", 0.05, 0.3),
        (1947, 2021, "trade", 0.20, 0.6),
    ],

    # === SubSaharan ↔ Islamic ===
    ("Islamic", "SubSaharan"): [
        (700, 1500, "trade", 0.20, 0.6),               # サハラ越え交易
        (700, 1500, "knowledge_diffusion", 0.15, 0.5), # イスラム伝播
        (1500, 1850, "trade", 0.15, 0.5),              # 奴隷貿易 (Africa→Arab)
        (1500, 1850, "war", 0.05, 0.4),
    ],

    # === SubSaharan ↔ Europe ===
    ("Europe", "SubSaharan"): [
        (1450, 1850, "trade", 0.20, 0.7),              # 大西洋奴隷貿易
        (1450, 1850, "war", 0.08, 0.5),
        (1450, 1850, "disease_exchange", 0.15, 0.6),   # 双方向疫病 (黄熱・天然痘)
        (1850, 1960, "war", 0.20, 0.8),                # 植民地分割・征服
        (1850, 1960, "knowledge_diffusion", 0.20, 0.6),
        (1850, 1960, "disease_exchange", 0.10, 0.5),
        (1960, 2021, "trade", 0.20, 0.5),
        (1960, 2021, "knowledge_diffusion", 0.15, 0.5),
    ],

    # === SubSaharan ↔ Indic (limited contact) ===
    ("Indic", "SubSaharan"): [
        (700, 1500, "trade", 0.10, 0.4),               # インド洋交易
        (1500, 1900, "trade", 0.05, 0.3),
    ],

    # === Polynesian ↔ Europe (Captain Cook etc.) ===
    ("Europe", "Polynesian"): [
        (1769, 1900, "knowledge_diffusion", 0.30, 0.8), # 接触・宣教
        (1769, 1900, "disease_exchange", 0.40, 0.95),   # 壊滅的疫病
        (1769, 1900, "war", 0.10, 0.6),
        (1900, 1970, "knowledge_diffusion", 0.20, 0.5), # 植民地統治
        (1900, 1970, "war", 0.10, 0.7),                 # 太平洋戦争
    ],

    # === IndigenousAmericas ↔ Europe (大破滅) ===
    ("Europe", "IndigenousAmericas"): [
        (1492, 1521, "disease_exchange", 0.95, 1.0),    # 接触初期 (天然痘等で90%死亡)
        (1492, 1521, "war", 0.50, 0.95),                # コンキスタドール征服
        (1521, 1700, "disease_exchange", 0.30, 0.9),    # 連続疫病
        (1521, 1700, "war", 0.20, 0.7),
        (1521, 1700, "knowledge_diffusion", 0.20, 0.5),
        (1700, 1900, "war", 0.15, 0.7),                 # 抵抗運動
        (1700, 1900, "knowledge_diffusion", 0.10, 0.4),
        (1900, 2021, "trade", 0.10, 0.4),
    ],

    # === IndigenousAmericas ↔ Africa (奴隷貿易経由) ===
    ("SubSaharan", "IndigenousAmericas"): [
        (1500, 1850, "trade", 0.05, 0.3),               # 奴隷経由の文化伝播
        (1500, 1850, "disease_exchange", 0.05, 0.3),
    ],

    # === Polynesian ↔ IndigenousAmericas (推測される接触) ===
    ("IndigenousAmericas", "Polynesian"): [
        (1000, 1500, "trade", 0.02, 0.3),               # サツマイモ伝播仮説等
    ],

    # === China ↔ Polynesian (限定的) ===
    ("China", "Polynesian"): [
        (1500, 2021, "trade", 0.05, 0.2),
    ],
}


# Channel effect specifications
CHANNEL_EFFECTS = {
    "trade": {
        # Both civs gain
        "trade_boost_self":   0.020,
        "trade_boost_other":  0.020,
        "asset_boost_both":   0.012,
        "shock_to_self":      0.0,
        "shock_to_other":     0.0,
    },
    "war": {
        # Aggressor minor shock, defender major
        # We treat both as receiving shock (no asymmetric here for simplicity)
        "shock_to_self":      0.06,
        "shock_to_other":     0.10,
        "trade_boost_self":   0.0,
        "trade_boost_other":  0.0,
        "asset_boost_both":   0.0,
    },
    "knowledge_diffusion": {
        # The 'self' is the source, 'other' is the recipient
        # Recipient gains knowledge
        "edu_boost_other":    0.015,
        "inst_boost_other":   0.010,
        "trade_boost_self":   0.0,
        "trade_boost_other":  0.0,
        "shock_to_self":      0.0,
        "shock_to_other":     0.0,
    },
    "disease_exchange": {
        # Both civs receive shock (no immunity transfer modelled)
        "shock_to_self":      0.05,
        "shock_to_other":     0.05,
        "trade_boost_self":   0.0,
        "trade_boost_other":  0.0,
    },
}


def get_pair_key(civ_a, civ_b):
    """Normalize civ pair (alphabetical order)."""
    if civ_a < civ_b:
        return (civ_a, civ_b)
    return (civ_b, civ_a)


def sample_interactions_for_year(year, year_window_size, rng,
                                   active_civs):
    """Sample which inter-civ interactions fire in this generation.

    Returns list of {pair, channel, intensity, year}.
    """
    interactions = []
    for i, civ_a in enumerate(active_civs):
        for civ_b in active_civs[i+1:]:
            # Try both key orderings
            entries = INTERACTION_CATALOG.get((civ_a, civ_b)) or \
                      INTERACTION_CATALOG.get((civ_b, civ_a))
            if entries is None:
                continue
            pair = get_pair_key(civ_a, civ_b)
            for entry in entries:
                year_start, year_end, channel, p_per_year, intensity = entry
                # Check overlap with current generation window
                gen_start = year
                gen_end = year + year_window_size
                if year_end <= gen_start or year_start >= gen_end:
                    continue
                # Compute geometric probability of at least 1 occurrence
                overlap = min(year_end, gen_end) - max(year_start, gen_start)
                if overlap <= 0:
                    continue
                p_at_least_one = 1 - (1 - p_per_year) ** overlap
                if rng.random() < p_at_least_one:
                    interactions.append({
                        "pair": pair,
                        "channel": channel,
                        "intensity": intensity,
                        "year": year + int(rng.uniform(0, year_window_size)),
                    })
    return interactions


def apply_interaction_effects(interaction, civ_states):
    """Apply interaction effects to per-civilization global state.

    civ_states is dict of {civ_name: {shock_add, trade_boost, asset_boost,
                                       edu_boost, inst_boost}}
    Returns updated civ_states (in-place).

    Convention for asymmetric channels:
    - knowledge_diffusion: civ_a is source (no gain), civ_b is recipient
      (For undirected pair (a,b), we apply both directions for fairness)
    - war: both sides get shock
    - trade: both gain
    - disease: both shock
    """
    pair = interaction["pair"]
    channel = interaction["channel"]
    intensity = interaction["intensity"]
    civ_a, civ_b = pair

    if channel not in CHANNEL_EFFECTS:
        return civ_states

    eff = CHANNEL_EFFECTS[channel]

    # Apply effects with intensity scaling
    if channel == "trade":
        civ_states[civ_a]["trade_boost"] += eff["trade_boost_self"] * intensity
        civ_states[civ_a]["asset_boost"] += eff["asset_boost_both"] * intensity
        civ_states[civ_b]["trade_boost"] += eff["trade_boost_other"] * intensity
        civ_states[civ_b]["asset_boost"] += eff["asset_boost_both"] * intensity

    elif channel == "war":
        civ_states[civ_a]["shock_add"] += eff["shock_to_self"] * intensity
        civ_states[civ_b]["shock_add"] += eff["shock_to_other"] * intensity

    elif channel == "knowledge_diffusion":
        # Bidirectional: both civs receive knowledge from the other
        civ_states[civ_a]["edu_boost"] += eff["edu_boost_other"] * intensity
        civ_states[civ_a]["inst_boost"] += eff["inst_boost_other"] * intensity
        civ_states[civ_b]["edu_boost"] += eff["edu_boost_other"] * intensity
        civ_states[civ_b]["inst_boost"] += eff["inst_boost_other"] * intensity

    elif channel == "disease_exchange":
        civ_states[civ_a]["shock_add"] += eff["shock_to_self"] * intensity
        civ_states[civ_b]["shock_add"] += eff["shock_to_other"] * intensity

    return civ_states


def empty_civ_state():
    """Return zero-initialized per-civ interaction state for one generation."""
    return {
        "shock_add": 0.0,
        "trade_boost": 0.0,
        "asset_boost": 0.0,
        "edu_boost": 0.0,
        "inst_boost": 0.0,
    }


def render_interaction_summary(interaction_log, n_generations):
    """Render a summary of interactions over the simulation."""
    lines = []
    lines.append("# Inter-Civilization Interaction Summary\n")
    lines.append(f"Total interactions: {len(interaction_log)}\n")
    lines.append("")

    # Per-channel counts
    by_channel = {}
    for ev in interaction_log:
        by_channel[ev["channel"]] = by_channel.get(ev["channel"], 0) + 1
    lines.append("## Channel Distribution")
    for ch in ["trade", "war", "knowledge_diffusion", "disease_exchange"]:
        c = by_channel.get(ch, 0)
        lines.append(f"- {ch}: {c}")
    lines.append("")

    # Per-pair counts
    by_pair = {}
    for ev in interaction_log:
        pair_str = f"{ev['pair'][0]} ↔ {ev['pair'][1]}"
        by_pair[pair_str] = by_pair.get(pair_str, 0) + 1
    lines.append("## Pair Distribution")
    for pair, c in sorted(by_pair.items(), key=lambda x: -x[1]):
        lines.append(f"- {pair}: {c} interactions")
    lines.append("")

    # Notable events (high intensity only)
    high_intensity = [ev for ev in interaction_log if ev["intensity"] >= 0.7]
    if high_intensity:
        lines.append(f"## Major Interactions (intensity ≥ 0.7) — {len(high_intensity)}")
        for ev in high_intensity[:30]:
            lines.append(f"- Year {ev['year']}: {ev['channel']} between "
                         f"**{ev['pair'][0]}** ↔ **{ev['pair'][1]}** "
                         f"(intensity {ev['intensity']:.1f})")
        if len(high_intensity) > 30:
            lines.append(f"- ... and {len(high_intensity) - 30} more")
        lines.append("")

    return "\n".join(lines)
