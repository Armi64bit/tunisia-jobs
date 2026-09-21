import re
from pathlib import Path


CV_KEYWORDS = [
    'developer', 'software engineer', 'software developer', 'web developer',
    'frontend developer', 'backend developer', 'full stack developer',
    'developpeur', 'ingenieur logiciel',
    'data analyst', 'data scientist', 'data engineer', 'business intelligence',
    'devops', 'cloud engineer', 'fullstack', 'frontend', 'backend',
    'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'php',
    'django', 'flask', 'node.js', 'node', 'sql', 'postgresql', 'mysql',
    'mongodb', 'docker', 'kubernetes', 'aws', 'azure', 'git', 'rest api',
    'mobile developer', 'flutter', 'android', 'ios', 'cybersecurity',
    'network engineer', 'system administrator', 'machine learning',
    'artificial intelligence', 'chef de projet', 'project manager',
    'product manager', 'program manager', 'comptable', 'auditeur', 'finance',
    'accountant', 'financial analyst', 'commercial', 'sales', 'sales manager',
    'business developer', 'marketing', 'community manager', 'digital marketing',
    'ressources humaines', 'recrutement', 'ingenieur', 'technicien',
    'quality engineer', 'responsable qualite', 'human resources', 'recruiter',
    'banque', 'assurance', 'telecom', 'industrie', 'logistique',
]


def extract_cv_text(path: str) -> str:
    """Read a plain-text or PDF CV and return its searchable text."""
    cv_path = Path(path)
    if not cv_path.is_file():
        raise FileNotFoundError(f'CV not found: {cv_path}')

    if cv_path.suffix.lower() in {'.txt', '.md'}:
        return cv_path.read_text(encoding='utf-8', errors='ignore')

    if cv_path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError('PDF CV support requires the pypdf package') from exc
        text = '\n'.join(page.extract_text() or '' for page in PdfReader(str(cv_path)).pages)
        if not text.strip():
            raise ValueError(
                'No selectable text found in the PDF. Use a text-based PDF, '
                'not a scanned image-only PDF.'
            )
        return text

    raise ValueError('CV format not supported. Use .txt, .md, or .pdf.')


def keywords_from_cv(text: str, limit: int = 10) -> list[str]:
    """Return the most relevant supported search terms found in CV text."""
    normalized = re.sub(r'[^a-z0-9]+', ' ', text.casefold()).strip()
    normalized = f' {normalized} '
    matches = [
        keyword for keyword in CV_KEYWORDS
        if f" {re.sub(r'[^a-z0-9]+', ' ', keyword.casefold()).strip()} " in normalized
    ]
    if not matches:
        raise ValueError('No recognized skills or roles were found in the CV.')
    return matches[:limit]