"""
Phase 11A: Cultural Module Abstraction

Each civilization has:
- occupations (職業): culture-specific occupation set
- regions (地域): geographic regions
- region_init_probs (地域初期分布)
- inheritance: rule for collateral_success modifier
- shock_response: how the culture absorbs shock
- base_strategy_dist: default decision theory mix
- base_failure_rate: civilization-specific era multiplier

A simulation can run multiple Cultural Modules in parallel,
with inter-civilization interaction (Phase 11B).
"""
import numpy as np


class CulturalModule:
    """Abstract base class for a civilization's cultural parameters."""
    name = "Abstract"
    label_jp = "抽象文明"

    # Occupation set (11 categories used; ordering must match BASE_OCC matrix)
    occupations = ["agrarian", "rural_notable", "temple_clerk", "warrior",
                   "craft_trade", "merchant", "urban_wage", "industrial",
                   "company_skilled", "education_public", "professional"]

    # Number of regions
    n_regions = 6
    region_names = []
    region_init_probs = None

    # Era boundaries (year_start, year_end, base_failure, collateral_success)
    eras = []

    # Inheritance pattern: "primogeniture" / "partible" / "communal"
    inheritance = "partible"

    # Distribution boost factor (collateral chance multiplier)
    distribution_boost = 1.0

    # Default strategy distribution (decision theory mix)
    base_strategy_dist = {
        "NRMO_vNext": 0.30,
        "Adaptive_OmegaFull": 0.10,
        "ExpectedValueMax": 0.20,
        "RiskAdjustedUtility": 0.20,
        "Faith": 0.10,
        "Drift": 0.10,
    }

    # Faith subdivision (which sub-faiths exist)
    faith_subdist = {
        "Faith_Buddhist": 0.30,
        "Faith_Communal": 0.30,
        "Faith_Calvinist": 0.10,
        "Faith_Charismatic": 0.10,
        "Faith_Ascetic": 0.10,
        "Faith_Militant": 0.10,
    }

    # Tech and religion baselines
    tech_acceleration = 1.0
    tech_inflection_year = 1868
    religion_strength_initial = 0.5
    faith_shock_buffer_max = 0.10

    # Region transition stability (per era)
    region_stability_curve = [0.92, 0.90, 0.88, 0.80, 0.85, 0.75, 0.70]


# ============================================================
# JAPAN MODULE (existing)
# ============================================================

class JapanModule(CulturalModule):
    name = "Japan"
    label_jp = "日本"

    region_names = ["North_Kyushu", "Kinai", "Setouchi_Kibi", "Tokai_Nobi",
                    "Kanto_Inland", "South_Tohoku"]
    region_init_probs = np.array([.30, .20, .20, .15, .10, .05])
    n_regions = 6

    eras = [
        ("Yayoi_Kofun_Early", 0, 400, 0.14, 0.96),
        ("Kofun_Late_Nara",   400, 800, 0.12, 0.965),
        ("Heian_Estate",      800, 1200, 0.10, 0.97),
        ("Kamakura_Sengoku",  1200, 1600, 0.18, 0.965),
        ("Edo",               1600, 1868, 0.08, 0.98),
        ("Meiji_WW2",         1868, 1945, 0.11, 0.975),
        ("Postwar_Modern",    1945, 2021, 0.04, 0.985),
    ]

    inheritance = "primogeniture"  # 嫡長子相続 (本家)
    distribution_boost = 1.10      # 分家・養子で boost (本家+分家+養子先)

    base_strategy_dist = {
        "NRMO_vNext": 0.25,
        "Adaptive_OmegaFull": 0.10,
        "ExpectedValueMax": 0.20,
        "RiskAdjustedUtility": 0.20,
        "Faith": 0.15,           # 仏教+神道+儒教共存
        "Drift": 0.10,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.50,    # 仏教は日本で支配的
        "Faith_Communal": 0.30,    # 儒教・神道
        "Faith_Calvinist": 0.02,   # ほぼなし
        "Faith_Charismatic": 0.05, # 新興宗教
        "Faith_Ascetic": 0.10,     # 出家僧
        "Faith_Militant": 0.03,    # 一向宗・天台僧兵
    }


# ============================================================
# CHINA MODULE
# ============================================================

class ChinaModule(CulturalModule):
    name = "China"
    label_jp = "中華"

    region_names = ["Yellow_River_North", "Yangtze_Lower", "Yangtze_Middle",
                    "South_Coast", "Sichuan_Basin", "Northwest_Frontier"]
    region_init_probs = np.array([.30, .25, .15, .15, .10, .05])
    n_regions = 6

    # China has different era boundaries
    eras = [
        ("Han_Era",          0, 220, 0.13, 0.965),       # 漢朝
        ("Three_Kingdoms",   220, 580, 0.16, 0.96),       # 三国南北朝
        ("Tang_Era",         580, 907, 0.09, 0.975),      # 隋唐 (peak)
        ("Song_Yuan",        907, 1368, 0.13, 0.97),      # 宋元
        ("Ming",             1368, 1644, 0.10, 0.975),    # 明
        ("Qing_Republic",    1644, 1949, 0.14, 0.97),     # 清・民国
        ("Modern_China",     1949, 2021, 0.05, 0.985),    # 現代
    ]

    inheritance = "partible"          # 諸子均分
    distribution_boost = 1.20         # 宗族 (大家族) 強い

    base_strategy_dist = {
        "NRMO_vNext": 0.20,
        "Adaptive_OmegaFull": 0.08,
        "ExpectedValueMax": 0.25,     # 商業繁栄
        "RiskAdjustedUtility": 0.22,
        "Faith": 0.18,                # 仏道儒の三教
        "Drift": 0.07,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.30,       # 仏教
        "Faith_Communal": 0.50,       # 儒教 (中国の中核)
        "Faith_Calvinist": 0.01,
        "Faith_Charismatic": 0.05,    # 道教神秘主義
        "Faith_Ascetic": 0.12,        # 道士・僧侶
        "Faith_Militant": 0.02,       # 義和団等
    }

    religion_strength_initial = 0.55
    tech_acceleration = 1.05          # 中世まで技術先進、後から下降
    tech_inflection_year = 1900       # 共和革命以降


# ============================================================
# EUROPE MODULE
# ============================================================

class EuropeModule(CulturalModule):
    name = "Europe"
    label_jp = "西欧"

    region_names = ["Italy_Mediterranean", "Iberia", "France_Gaul",
                    "British_Isles", "Germanic_Central", "Scandinavia"]
    region_init_probs = np.array([.30, .15, .20, .12, .15, .08])
    n_regions = 6

    eras = [
        ("Roman_Era",         0, 400, 0.11, 0.97),         # ローマ帝国
        ("Migration_Period",  400, 800, 0.16, 0.955),      # 民族移動期 (calibrated)
        ("Carolingian_Mediev", 800, 1200, 0.12, 0.965),    # カロリング・中世初期
        ("High_Medieval",     1200, 1500, 0.13, 0.965),    # 中世盛期 (Black Death)
        ("Renaissance_Reform", 1500, 1700, 0.14, 0.96),    # ルネサンス・宗教戦争
        ("Industrial_Era",    1700, 1945, 0.10, 0.97),     # 産業革命・大戦
        ("Postwar_EU",        1945, 2021, 0.04, 0.985),
    ]

    inheritance = "primogeniture"
    distribution_boost = 0.95

    base_strategy_dist = {
        "NRMO_vNext": 0.20,
        "Adaptive_OmegaFull": 0.10,
        "ExpectedValueMax": 0.25,      # 商業ブルジョワ
        "RiskAdjustedUtility": 0.18,
        "Faith": 0.20,                 # キリスト教中心
        "Drift": 0.07,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.00,
        "Faith_Communal": 0.20,        # カトリック共同体・救貧
        "Faith_Calvinist": 0.30,       # プロテスタント (16C 以降)
        "Faith_Charismatic": 0.05,     # 神秘主義者
        "Faith_Ascetic": 0.20,         # 修道院 (大量)
        "Faith_Militant": 0.25,        # 十字軍・宗教戦争
    }

    religion_strength_initial = 0.65
    tech_acceleration = 1.20           # 近代に大きく加速
    tech_inflection_year = 1700        # 産業革命


# ============================================================
# ISLAMIC MODULE
# ============================================================

class IslamicModule(CulturalModule):
    name = "Islamic"
    label_jp = "イスラム圏"

    region_names = ["Arabian_Peninsula", "Levant_Egypt", "Maghreb",
                    "Persia", "Anatolia", "Central_Asia"]
    region_init_probs = np.array([.20, .25, .15, .20, .10, .10])
    n_regions = 6

    eras = [
        ("Pre_Islamic",       0, 622, 0.16, 0.95),        # ジャーヒリーヤ
        ("Caliphate_Rashidun", 622, 750, 0.10, 0.97),     # 正統カリフ・ウマイヤ朝
        ("Abbasid_Golden",    750, 1258, 0.09, 0.975),    # アッバース朝・黄金期
        ("Mongol_Aftermath",  1258, 1500, 0.18, 0.96),    # モンゴル余波
        ("Ottoman_Safavid",   1500, 1800, 0.10, 0.97),    # オスマン・サファヴィー
        ("Colonial_Decline",  1800, 1945, 0.13, 0.97),    # 植民地化
        ("Postcolonial",      1945, 2021, 0.07, 0.98),    # 独立後
    ]

    inheritance = "partible"           # シャリーアによる分割相続
    distribution_boost = 1.15          # ワクフ・拡大家族

    base_strategy_dist = {
        "NRMO_vNext": 0.20,
        "Adaptive_OmegaFull": 0.08,
        "ExpectedValueMax": 0.22,      # 隊商交易
        "RiskAdjustedUtility": 0.18,
        "Faith": 0.25,                 # イスラム支配的
        "Drift": 0.07,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.00,
        "Faith_Communal": 0.55,        # ウンマ (信徒共同体) + ワクフ
        "Faith_Calvinist": 0.05,       # サラフィー主義 (経典回帰)
        "Faith_Charismatic": 0.10,     # スーフィズム
        "Faith_Ascetic": 0.10,         # 隠遁者
        "Faith_Militant": 0.20,        # ジハード
    }

    religion_strength_initial = 0.75   # 強い宗教世界
    tech_acceleration = 0.95           # 中世先進、近代以降減速
    tech_inflection_year = 1950        # 近代化遅れ


# ============================================================
# INDIC MODULE (インド亜大陸)
# ============================================================

class IndicModule(CulturalModule):
    name = "Indic"
    label_jp = "印度"

    region_names = ["Indus_Plain", "Gangetic_Plain", "Deccan_North",
                    "Deccan_South", "Bengal_Delta", "Kerala_Coast"]
    region_init_probs = np.array([.20, .30, .15, .15, .15, .05])
    n_regions = 6

    eras = [
        ("Mauryan_Era",       0, 320, 0.13, 0.965),     # マウリヤ朝
        ("Gupta_Classical",   320, 600, 0.10, 0.975),   # グプタ朝古典期
        ("Early_Medieval",    600, 1200, 0.13, 0.97),   # 中世初期
        ("Sultanate_Era",     1200, 1526, 0.16, 0.96),  # スルタン朝
        ("Mughal_Era",        1526, 1757, 0.11, 0.97),  # ムガル帝国
        ("Colonial_British",  1757, 1947, 0.13, 0.97),  # 英領インド
        ("Independent_India", 1947, 2021, 0.06, 0.985), # 独立後
    ]

    inheritance = "partible"           # ヒンドゥー法分割相続
    distribution_boost = 1.25          # ジョイントファミリー (拡大家族)

    base_strategy_dist = {
        "NRMO_vNext": 0.18,
        "Adaptive_OmegaFull": 0.07,
        "ExpectedValueMax": 0.20,      # 商人カースト
        "RiskAdjustedUtility": 0.15,
        "Faith": 0.30,                 # 宗教多元性 (ヒンドゥー・仏教・ジャイナ・イスラム)
        "Drift": 0.10,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.25,        # 仏教 (発祥地)
        "Faith_Communal": 0.30,        # ヒンドゥー共同体・カースト
        "Faith_Calvinist": 0.02,
        "Faith_Charismatic": 0.10,     # バクティ運動・シーク教
        "Faith_Ascetic": 0.25,         # サドゥー・ジャイナ僧 (極めて多い)
        "Faith_Militant": 0.08,        # シーク戦士・イスラム王朝
    }

    religion_strength_initial = 0.85   # 強い宗教世界
    tech_acceleration = 0.95
    tech_inflection_year = 1947


# ============================================================
# SUB-SAHARAN AFRICAN MODULE
# ============================================================

class SubSaharanModule(CulturalModule):
    name = "SubSaharan"
    label_jp = "サハラ以南"

    region_names = ["West_Sahel", "West_Coast", "East_Highlands",
                    "Congo_Basin", "South_Plateau", "Horn_Region"]
    region_init_probs = np.array([.20, .25, .20, .15, .15, .05])
    n_regions = 6

    eras = [
        ("Iron_Age_Kingdoms",  0, 800, 0.16, 0.96),     # 鉄器時代諸王国
        ("Trans_Saharan_Trade", 800, 1450, 0.13, 0.97), # サハラ越え交易
        ("Atlantic_Slave_Trade", 1450, 1850, 0.30, 0.88), # 大西洋奴隷貿易期 — strengthened (人口流出)
        ("Colonial_Scramble",  1850, 1960, 0.25, 0.90), # 植民地分割 — strengthened
        ("Postcolonial",       1960, 2021, 0.12, 0.95), # 独立後 (内戦多発)
    ]

    inheritance = "communal"
    distribution_boost = 1.10          # 大家族 (ただし奴隷貿易で削がれる)

    base_strategy_dist = {
        "NRMO_vNext": 0.15,
        "Adaptive_OmegaFull": 0.05,
        "ExpectedValueMax": 0.15,
        "RiskAdjustedUtility": 0.20,   # リスク回避が強い (環境厳しい)
        "Faith": 0.30,                 # アニミズム・イスラム・キリスト教
        "Drift": 0.15,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.00,
        "Faith_Communal": 0.50,        # アニミズム共同体・氏族崇拝
        "Faith_Calvinist": 0.05,       # 福音派キリスト教
        "Faith_Charismatic": 0.25,     # ペンテコステ・憑霊信仰
        "Faith_Ascetic": 0.05,         # 隠遁
        "Faith_Militant": 0.15,        # ジハード・部族戦争
    }

    religion_strength_initial = 0.80
    tech_acceleration = 0.85           # 技術発展遅い
    tech_inflection_year = 1960
    region_stability_curve = [0.95, 0.92, 0.85, 0.80, 0.75]  # 5 era


# ============================================================
# POLYNESIAN / OCEANIA MODULE
# ============================================================

class PolynesianModule(CulturalModule):
    name = "Polynesian"
    label_jp = "ポリネシア"

    region_names = ["Western_Polynesia", "Central_Polynesia",
                    "Eastern_Polynesia", "Hawaii_Cluster",
                    "Aotearoa", "Marquesas"]
    region_init_probs = np.array([.30, .20, .20, .10, .15, .05])
    n_regions = 6

    eras = [
        ("Lapita_Expansion",   0, 1200, 0.13, 0.965),    # ラピタ拡張期 (calibrated)
        ("Classical_Polynesian", 1200, 1769, 0.10, 0.97),
        ("Contact_Era",        1769, 1900, 0.35, 0.86),  # 接触・疫病 (Marquesas 90%減; calibrated)
        ("Colonial_Period",    1900, 1970, 0.16, 0.94),
        ("Modern_Pacific",     1970, 2021, 0.08, 0.97),
    ]

    inheritance = "primogeniture"
    distribution_boost = 0.95

    base_strategy_dist = {
        "NRMO_vNext": 0.20,
        "Adaptive_OmegaFull": 0.08,
        "ExpectedValueMax": 0.10,
        "RiskAdjustedUtility": 0.25,   # 海洋リスクへの保守性
        "Faith": 0.27,                 # マナ信仰
        "Drift": 0.10,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.00,
        "Faith_Communal": 0.50,        # マナ・タプー・共同体儀礼
        "Faith_Calvinist": 0.10,       # 19世紀宣教師
        "Faith_Charismatic": 0.15,
        "Faith_Ascetic": 0.10,
        "Faith_Militant": 0.15,        # 戦士伝統
    }

    religion_strength_initial = 0.75
    tech_acceleration = 0.90
    tech_inflection_year = 1900
    region_stability_curve = [0.85, 0.85, 0.70, 0.80, 0.75]  # 5 era


# ============================================================
# STEPPE NOMADIC MODULE
# ============================================================

class SteppeNomadicModule(CulturalModule):
    name = "Steppe"
    label_jp = "中央アジア遊牧"

    region_names = ["West_Steppe", "Central_Steppe", "East_Steppe",
                    "Mongol_Plateau", "Tarim_Basin", "Kazakh_Plain"]
    region_init_probs = np.array([.20, .25, .15, .20, .10, .10])
    n_regions = 6

    eras = [
        ("Scythian_Era",       0, 400, 0.16, 0.95),    # スキタイ・サルマタイ
        ("Turkic_Khanates",    400, 1200, 0.14, 0.96), # 突厥・ウイグル
        ("Mongol_Empire",      1200, 1400, 0.10, 0.975), # モンゴル帝国 (peak)
        ("Post_Mongol",        1400, 1700, 0.16, 0.95),  # ティムール・アイルク
        ("Russian_Qing",       1700, 1900, 0.18, 0.94),  # 露清併合期
        ("Modern_Sedentary",   1900, 2021, 0.10, 0.97),  # 定住化
    ]

    inheritance = "partible"           # ウルス継承 (分割)
    distribution_boost = 1.10

    base_strategy_dist = {
        "NRMO_vNext": 0.20,
        "Adaptive_OmegaFull": 0.10,
        "ExpectedValueMax": 0.30,      # 略奪・交易の高利得志向
        "RiskAdjustedUtility": 0.10,
        "Faith": 0.20,                 # シャーマニズム + 後イスラム
        "Drift": 0.10,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.20,        # チベット仏教 (モンゴル)
        "Faith_Communal": 0.20,        # 氏族祖先崇拝
        "Faith_Calvinist": 0.00,
        "Faith_Charismatic": 0.20,     # シャーマン
        "Faith_Ascetic": 0.10,
        "Faith_Militant": 0.30,        # 騎兵戦士集団 (高比率)
    }

    religion_strength_initial = 0.65
    tech_acceleration = 0.95
    tech_inflection_year = 1900


# ============================================================
# INDIGENOUS AMERICAS MODULE
# ============================================================

class IndigenousAmericasModule(CulturalModule):
    name = "IndigenousAmericas"
    label_jp = "先住アメリカ"

    region_names = ["Mesoamerica", "Andes_High", "Caribbean_Coast",
                    "Amazonia", "Plains_North", "Pacific_NW"]
    region_init_probs = np.array([.30, .25, .10, .15, .10, .10])
    n_regions = 6

    eras = [
        ("Classic_Civilization",  0, 900, 0.13, 0.96),    # マヤ古典・テオティワカン
        ("Postclassic",           900, 1521, 0.15, 0.96),  # アステカ・インカ・トルテカ
        ("Conquest_Catastrophe",  1521, 1700, 0.65, 0.75), # 大破滅 (90%人口消失) — strengthened
        ("Colonial_Mestizo",      1700, 1810, 0.20, 0.92),  # 植民地圧
        ("Independence_Era",      1810, 1950, 0.15, 0.95),
        ("Modern_Indigenous",     1950, 2021, 0.10, 0.97),
    ]

    inheritance = "partible"
    distribution_boost = 0.85          # Conquest で氏族構造崩壊

    base_strategy_dist = {
        "NRMO_vNext": 0.18,
        "Adaptive_OmegaFull": 0.07,
        "ExpectedValueMax": 0.15,
        "RiskAdjustedUtility": 0.20,
        "Faith": 0.30,                 # 強い宗教共同体
        "Drift": 0.10,
    }

    faith_subdist = {
        "Faith_Buddhist": 0.00,
        "Faith_Communal": 0.45,        # 共同体・アイユ・カルプリ
        "Faith_Calvinist": 0.05,
        "Faith_Charismatic": 0.20,     # シャーマン・幻視伝統
        "Faith_Ascetic": 0.10,
        "Faith_Militant": 0.20,        # 戦士階級・人身御供
    }

    religion_strength_initial = 0.85
    tech_acceleration = 0.80           # 接触前は高度、接触後激減
    tech_inflection_year = 1900


# ============================================================
# Module registry (拡張版)
# ============================================================
CULTURAL_MODULES = {
    "Japan":   JapanModule(),
    "China":   ChinaModule(),
    "Europe":  EuropeModule(),
    "Islamic": IslamicModule(),
    "Indic":   IndicModule(),
    "SubSaharan": SubSaharanModule(),
    "Polynesian": PolynesianModule(),
    "Steppe":  SteppeNomadicModule(),
    "IndigenousAmericas": IndigenousAmericasModule(),
}


def get_cultural_module(name):
    return CULTURAL_MODULES[name]


def list_cultural_modules():
    return list(CULTURAL_MODULES.keys())
