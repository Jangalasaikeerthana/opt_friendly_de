import requests
import pandas as pd
import re
import time
from concurrent.futures import ThreadPoolExecutor

def cleaning_name(name):
    name = re.sub(r'\b(llc|ltd|inc|corp|co|lp|llp|pvt|limited|corporation)\b', '', name, flags=re.IGNORECASE).lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def check_slug(slug):
    if not slug or len(slug) < 2:
        return None
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    for attempt in range(3):
        try:
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                return slug
            return None
        except Exception:
            time.sleep(1)
    return None

if __name__ == "__main__":
    print("Loading USCIS data...")
    df = pd.read_csv('Employer Information (1).csv', encoding='utf-16', sep='\t', low_memory=False)
    
    unique_companies = df['Employer (Petitioner) Name'].dropna().unique()


    cleaned_slugs = list(set([cleaning_name(name) for name in unique_companies]))
    testing= cleaned_slugs[:1000]
    print(f"Total unique slugs: {len(cleaned_slugs)}")
    
    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_slug, testing))
    
    confirmed = [r for r in results if r is not None]
    
    end = time.time()
    print(f"Time: {end-start:.2f} seconds")
    print(f"Found on Greenhouse: {len(confirmed)}")
    
    pd.Series(confirmed).to_csv('confirmed_greenhouse_slugs.csv', index=False)
    print("Saved!")