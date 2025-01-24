from jobspy import scrape_jobs
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

def nan_to_none(value):
    if pd.isna(value):
        return None
    return value

jobs = scrape_jobs(
    site_name=["indeed", "linkedin", "zip_recruiter", "glassdoor", "google"],
    search_term="software engineer",
    google_search_term="software engineer jobs near San Francisco, CA since yesterday",
    location="San Francisco, CA",
    results_wanted=20,
    hours_old=24,
    country_indeed='USA',
    
    # linkedin_fetch_description=True # gets more info such as description, direct job url (slower)
    # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
)


df = pd.DataFrame(jobs)

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)

cursor = conn.cursor()

for _, row in df.iterrows():
    print(row.keys())
    print(row['date_posted'])  
    for key in row.keys():
        row[key] = nan_to_none(row[key])  
    cursor.execute(
        """
        INSERT INTO job_postings (title, company, location, job_type, salary_min, salary_max, job_url, description, date, salary_interval, company_logo_url, company_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            row["title"],
            row["company"],
            row["location"],
            row["job_type"],
            row["min_amount"],
            row["max_amount"],
            row["job_url"],
            row["description"],
            row["date_posted"],
            row["interval"],
            row["company_logo"],
            row["company_url"]
        )
    )

conn.commit()
cursor.close()
conn.close()

