import os

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")


def generate_cover_letter(cv_text: str, job: dict, match: dict | None = None) -> str:
    """Generate a concise, job-specific cover letter from the submitted CV."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    match = match or {}
    skills = ", ".join(match.get("cv_keywords") or [])
    missing = ", ".join(match.get("missing_skills") or [])
    prompt = f"""
CV:
{cv_text[:10000]}

JOB TITLE: {job.get('title', '')}
COMPANY: {job.get('company', '')}
LOCATION: {job.get('location', '')}
CONTRACT: {job.get('contract', '')}
DESCRIPTION:
{job.get('description', '')[:6000]}

MATCHED CV SKILLS: {skills}
MISSING SKILLS: {missing}
"""
    system_prompt = (
        "Tu es un rédacteur de candidatures professionnel. Rédige une lettre de motivation "
        "personnalisée en français, fondée uniquement sur le CV et l'offre fournis. "
        "Format obligatoire : Objet, formule d'appel, 3 paragraphes courts, formule de clôture, "
        "puis le nom du candidat uniquement s'il est clairement présent dans le CV. "
        "Ne mets pas de Markdown, de titre comme 'Lettre de motivation', de placeholders, "
        "de coordonnées inventées, ni d'affirmations qui ne figurent pas dans le CV. "
        "Longueur cible : 180 à 280 mots."
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
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.45,
            "max_tokens": 700,
        },
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(
            f"OpenRouter request failed ({response.status_code}): {response.text[:500]}"
        )
    data = response.json()
    try:
        letter = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenRouter returned an invalid cover letter response") from exc
    if not letter:
        raise RuntimeError("OpenRouter returned an empty cover letter")
    return letter
