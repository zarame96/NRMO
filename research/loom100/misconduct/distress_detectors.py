"""
不正会計・破綻リスクの検出指標（公開・査読済みモデルのみ）。
- Beneish M-Score (Beneish 1999 "The Detection of Earnings Manipulation"): 利益操作の兆候。
    M = -4.84 +0.920·DSRI +0.528·GMI +0.404·AQI +0.892·SGI +0.115·DEPI
        -0.172·SGAI +4.679·TATA -0.327·LVGI ;  M > -2.22 で操作の可能性。
    （コーネル大生がEnronを本指標で検出した実績）
- Altman Z-Score (Altman 1968): 倒産/ディストレス。
    Z = 1.2·X1 +1.4·X2 +3.3·X3 +0.6·X4 +1.0·X5 ; 危険 <1.81 / グレー 1.81-2.99 / 安全 >2.99
- 継続企業の前提(going concern)の赤信号。
※ 現存企業を「不正」と断定する道具ではない。過去事例に似た破滅前パターンを警告するための指標。
"""
def _safe(n, d):
    try: return n / d if d not in (0, 0.0, None) else 0.0
    except Exception: return 0.0

def beneish_m_score(prev, cur):
    bp, pp = prev["bs"], prev["pl"]; bc, pc = cur["bs"], cur["pl"]
    dsri = _safe(_safe(bc["ar"], pc["revenue"]), _safe(bp["ar"], pp["revenue"]))
    gm_p = _safe(pp["revenue"] - pp["cogs"], pp["revenue"]); gm_c = _safe(pc["revenue"] - pc["cogs"], pc["revenue"])
    gmi  = _safe(gm_p, gm_c)
    aq_c = 1 - _safe(bc["cur_assets"] + bc["net_ppe"], bc["total_assets"])
    aq_p = 1 - _safe(bp["cur_assets"] + bp["net_ppe"], bp["total_assets"])
    aqi  = _safe(aq_c, aq_p)
    sgi  = _safe(pc["revenue"], pp["revenue"])
    dp_p = _safe(pp.get("dep", 0.0), bp["net_ppe"] + pp.get("dep", 0.0)); dp_c = _safe(pc.get("dep", 0.0), bc["net_ppe"] + pc.get("dep", 0.0))
    depi = _safe(dp_p, dp_c)
    sgai = _safe(_safe(pc.get("opex", 0.0), pc["revenue"]), _safe(pp.get("opex", 0.0), pp["revenue"]))
    lvgi = _safe(_safe(bc["total_liab"], bc["total_assets"]), _safe(bp["total_liab"], bp["total_assets"]))
    tata = _safe(pc.get("ni", 0.0) - pc.get("cfo", 0.0), bc["total_assets"])
    m = (-4.84 + 0.920*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi + 0.115*depi
         - 0.172*sgai + 4.679*tata - 0.327*lvgi)
    return {"M": m, "manip_flag": m > -2.22,
            "DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi, "DEPI": depi, "SGAI": sgai, "LVGI": lvgi, "TATA": tata}

def altman_z(stmt, market_cap=None):
    bs, pl = stmt["bs"], stmt["pl"]; ta = bs["total_assets"] or 1.0
    x1 = _safe(bs["cur_assets"] - bs["cur_liab"], ta)
    x2 = _safe(bs["retained"], ta)
    x3 = _safe(pl.get("op_income", 0.0), ta)
    mve = market_cap if market_cap else bs["equity"]
    x4 = _safe(mve, bs["total_liab"])
    x5 = _safe(pl.get("revenue", 0.0), ta)
    z = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
    zone = "safe" if z > 2.99 else ("grey" if z >= 1.81 else "distress")
    return {"Z": z, "zone": zone, "X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5}

def going_concern_flags(stmt):
    bs, pl = stmt["bs"], stmt["pl"]; f = []
    if bs["equity"] < 0: f.append("債務超過")
    if pl.get("op_income", 0.0) < 0: f.append("営業赤字")
    if pl.get("cfo", 0.0) < 0: f.append("営業CFマイナス")
    if bs["cash"] < bs["cur_liab"] * 0.10: f.append("手元流動性が薄い")
    if stmt.get("going_concern_doubt"): f.append("継続企業の前提に重要な疑義")
    au = str(stmt.get("audit", ""))
    if au and not any(k in au for k in ("無限定適正", "unqualified", "適正意見")):
        if any(k in au for k in ("不適正", "限定", "不表明", "qualified", "adverse", "disclaimer")):
            f.append(f"監査意見:{au}")
    return f
