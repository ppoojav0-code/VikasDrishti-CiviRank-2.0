"""Optional Google Programmable Search lookup for public ward-representative records.
Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID. Results are leads, not verified facts."""
import os, json, urllib.parse, urllib.request

def search_representative(area, city='Bengaluru', ward=''):
    key, cx = os.getenv('GOOGLE_CSE_API_KEY',''), os.getenv('GOOGLE_CSE_ID','')
    if not key or not cx:
        return [], 'Online extraction is not configured. Set GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID for Google Programmable Search.'
    query = f'"{area}" {ward} corporator councillor ward representative {city} official'
    params = urllib.parse.urlencode({'key':key,'cx':cx,'q':query,'num':8})
    req = urllib.request.Request('https://www.googleapis.com/customsearch/v1?'+params, headers={'User-Agent':'VikasDrishti/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: payload=json.loads(r.read().decode('utf-8'))
        items=[{'title':x.get('title',''),'snippet':x.get('snippet',''),'link':x.get('link','')} for x in payload.get('items',[])]
        return items, ('Search results found. Confirm every name/contact against the official municipal source before saving.' if items else 'No results found. Try adding the ward number or municipal body.')
    except Exception as e: return [], f'Search request failed: {e}'
