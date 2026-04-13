import math
import datetime

# ------------------------------------------------------------------------------
# CONFIGURACIÓN DE PESOS (Inspirado en Polyseer)
# ------------------------------------------------------------------------------
TYPE_CAPS = {"A": 1.0, "B": 0.6, "C": 0.3, "D": 0.2}
WEIGHTS = {"v": 0.45, "r": 0.25, "c": 0.15, "t": 0.15} # 'c' = Consistency
LOGIT_MAX = 0.9999
LOGIT_MIN = 0.0001

def clamp(x, lo, hi):
    return min(hi, max(lo, x))

def logit(p):
    if p >= 1: p = LOGIT_MAX
    if p <= 0: p = LOGIT_MIN
    return math.log(p / (1 - p))

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def recency_score(published_at_str):
    """Calcula un score de recencia basado en días de antigüedad."""
    if not published_at_str:
        return 0.5
    try:
        # Formato esperado: YYYY-MM-DD
        dt = datetime.datetime.strptime(published_at_str[:10], "%Y-%m-%d")
        now = datetime.datetime.now()
        days = max(0, (now - dt).days)
        half_life = 120
        score = 1 / (1 + days / half_life)
        return clamp(score, 0, 1)
    except (ValueError, TypeError, AttributeError):
        return 0.5

def r_from_corroborations(k, k0=1.0):
    return 1 - math.exp(-k0 * max(0, k))

def calculate_log_lr(evidence_item):
    """
    Calcula el Log Likelihood Ratio de una pieza de evidencia.
    evidence_item: {
        'type': 'A'|'B'|'C'|'D',
        'verifiability': 0-1,
        'consistency': 0-1,
        'corroborations': int,
        'polarity': 1 (FOR) or -1 (AGAINST),
        'publishedAt': 'YYYY-MM-DD'
    }
    """
    e_type = evidence_item.get('type', 'C')
    cap = TYPE_CAPS.get(e_type, 0.3)
    
    ver = clamp(evidence_item.get('verifiability', 0.5), 0, 1)
    cons = clamp(evidence_item.get('consistency', 0.5), 0, 1)
    r = r_from_corroborations(evidence_item.get('corroborations', 0))
    t = recency_score(evidence_item.get('publishedAt'))
    
    polarity = evidence_item.get('polarity', 1)
    
    val = polarity * cap * (WEIGHTS['v']*ver + WEIGHTS['r']*r + WEIGHTS['c']*cons + WEIGHTS['t']*t)
    return clamp(val, -cap, cap)

def calculate_bayesian_probability(p_market, evidence_list):
    """
    Calcula la probabilidad final combinando el precio de mercado con la evidencia recolectada.
    """
    l = logit(p_market)
    
    for ev in evidence_list:
        l += calculate_log_lr(ev)
    
    p_final = sigmoid(l)
    return p_final

def get_bayesian_summary(p_market, p_final):
    diff = p_final - p_market
    sentiment = "NEUTRAL"
    if diff > 0.05: sentiment = "BULLISH (Argo ve oportunidad)"
    if diff < -0.05: sentiment = "BEARISH (Mercado sobrevalorado)"
    
    return {
        "score": round(p_final, 3),
        "edge": round(diff, 3),
        "sentiment": sentiment
    }
