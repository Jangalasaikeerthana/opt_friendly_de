
import requests
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

def get_data_jobs(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return []
        jobs_list = res.json()['jobs']
        matches = []
        us_keywords = ['usa', 'united states', 'united states of america', 'remote']
        for i in jobs_list:
            if 'data' in i['title'].lower():
                location = i['location']['name']
                if any(kw in location.lower() for kw in us_keywords):
                    matches.append({
                        'company': slug,
                        'title': i['title'],
                        'location': location,
                        'url': i['absolute_url']
                    })
        return matches
    except Exception as e:
        print(f"Error fetching {slug}: {e}")
        return []

def fetch_and_save(slug):
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    jobs = get_data_jobs(slug)
    cursor = conn.cursor()
    for job in jobs:
        cursor.execute("""
            INSERT INTO jobs (company, title, location, url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE SET
                is_active = TRUE,
                last_seen = CURRENT_TIMESTAMP
        """, (job['company'], job['title'], job['location'], job['url']))
    conn.commit()
    cursor.close()
    conn.close()
    return len(jobs)

if __name__ == "__main__":
    confirmed = pd.read_csv('confirmed_greenhouse_slugs.csv')['0'].tolist()
    print(f"Scraping {len(confirmed)} companies...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_and_save, confirmed))

    print(f"Done! Total jobs saved: {sum(results)}")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    df = pd.read_sql("SELECT * FROM jobs WHERE is_active = TRUE", conn)
    df.to_csv('jobs.csv', index=False)
    conn.close()
    print("CSV exported!")
