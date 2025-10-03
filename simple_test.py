from app.services.utils import parse_ai_analysis_to_query

ai_analysis = {
    'intent': 'proforma',
    'product': 'HOSO',
    'size': '30/40',
    'glaseo_factor': None
}

result = parse_ai_analysis_to_query(ai_analysis)
print(f"glaseo_factor: {result.get('glaseo_factor') if result else None}")