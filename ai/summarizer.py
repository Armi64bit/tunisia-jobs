# ai/summarizer.py  ── version OpenRouter
import os
import json
import pandas as pd
import requests
from datetime import date
from dotenv import load_dotenv
from database.db_manager import DBManager

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL", "openrouter/free"
)


def build_context(db: DBManager) -> str:
    """Rassemble les dernières stats depuis la DB et les formate pour le prompt."""
    top_skills  = db.get_top_skills(20)
    top_sectors = db.get_top_sectors(10)
    salary_data = db.get_salary_summary()
    growth_data = db.get_monthly_growth(3)   # 3 derniers mois

    context = f"""
Date d'analyse : {date.today().isoformat()}

TOP 20 COMPÉTENCES DEMANDÉES:
{json.dumps(top_skills, ensure_ascii=False, indent=2)}

TOP 10 SECTEURS (nombre d'offres):
{json.dumps(top_sectors, ensure_ascii=False, indent=2)}

STATISTIQUES SALARIALES (TND/mois):
{json.dumps(salary_data, ensure_ascii=False, indent=2)}

ÉVOLUTION DES 3 DERNIERS MOIS:
{json.dumps(growth_data, ensure_ascii=False, indent=2)}
"""
    return context


def _generate_summary(context: str) -> tuple[str, int]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    system_prompt = (
        "Tu es un expert du marché de l'emploi tunisien. "
        "Analyse les données fournies et rédige un résumé "
        "professionnel en français (max 300 mots) couvrant : "
        "1) tendances clés des compétences, "
        "2) secteurs en croissance, "
        "3) fourchettes salariales, "
        "4) recommandations pour les candidats."
    )

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            "temperature": 0.3,
            "max_tokens": 600,
        },
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(
            f"OpenRouter request failed ({response.status_code}): "
            f"{response.text[:500]}"
        )
    data = response.json()
    return (
        data["choices"][0]["message"]["content"],
        data.get("usage", {}).get("completion_tokens", 0),
    )


def _save_summary(db: DBManager, summary_text: str, tokens_used: int) -> dict:
    result = {
        "summary": summary_text,
        "generated_at": date.today().isoformat(),
        "model": OPENROUTER_MODEL,
        "tokens_used": tokens_used,
    }

    db.save_ai_summary(result)

    export_dir = os.getenv("EXPORT_DIR", "exports")
    os.makedirs(export_dir, exist_ok=True)
    pd.DataFrame([result]).to_csv(f"{export_dir}/ai_summary.csv", index=False)

    return result


def summarize_market() -> dict:
    db      = DBManager()
    context = build_context(db)
    summary_text, tokens_used = _generate_summary(context)
    return _save_summary(db, summary_text, tokens_used)
