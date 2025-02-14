from jobspy import scrape_jobs
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
from openai import OpenAI
import json

IMPORTANCE_TO_WEIGHT = {"explicitly required":1, "inferred required":0.9, "transferable to Required skills":0.8, "good to have":0.5, "maybe helpful":0.2, "irrelevent":0}

def nan_to_none(value):
    if pd.isna(value):
        return None
    return value

def initialize_llm(model, client):
    prompt = """
    I want you to help me evaluate the experience requirements and relevance to the posting for specific skills based on the job description, you should follow these guidelines:
    1.Identify Required Skills: Carefully review the job description and list related skills mentioned.
    2.Determine Minimum Requirements: For each skill identified, check if there is an explicitly stated minimum number of years of experience required. Note this information accurately.
    3.Assign Equivalent Experience:
        -If a specific minimum requirement is given (e.g., 3 years of SQL experience), use that figure to estimate the equivalent experience.
        -If no explicit minimum is provided, check if any other skills are a subskill of the current skill, and consider how it might contribute to the skill mentioned. When none is relevant, set the equivalent experience to 0
    4.Consider how relevent this skill is to the posting overall, I will ask later.
    """
    print("Prompt: " + prompt)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt}
        ],       
        max_tokens=800
    )    
    print("setup finished")
    return 


def update_job_description(model, client, job_description):
    prompt = "Process this job description based on previous instructions:\n" + job_description
    print("Prompt: " + prompt)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],       
        max_tokens=800
    )    
    return

def extract_skill_details(model, client, skillname):
    prompt = "What is the equivalence experience required for " + skillname + ", and how important is it to the job:\n"
    print("Prompt: " + prompt)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "equivalent_experience",
                "strict": "true",
                "schema": {
                "type": "object",
                "properties": {
                    "years_of_experience_required": {
                        "type": "integer"
                    },
                    "importance":{
                        "type": "string",
                        "enum": ["explicitly required", "inferred required", "transferable to Required skills", "good to have", "maybe helpful", "irrelevent"],
                        "description": "The importance level of the skill"
                    }
                },
                "required": ["years_of_experience_required", "importance"]
                }
            }
        },
        max_tokens=800
    )
    answer = json.loads(response.choices[0].message.content)
    print("Response:")
    print(answer)
    return (answer["years_of_experience_required"], IMPORTANCE_TO_WEIGHT[answer["importance"]])   
    

#Recursively use LLM to evaluate skills needed and enter them into the database
#Assumes that the LLM was already given the job description
#Check skilltree_impl.docx for details
def fill_skills_with_llm(cursor, skill_id, job_id, model, client):
    #find the name of the skill
    cursor.execute(
        """
        SELECT name FROM skilltree_hierachy WHERE id = %s
        """,
        (skill_id,)
    )
    skill_name = cursor.fetchone()[0]
    skill_experience_level, weight = extract_skill_details(model, client, skill_name)    

    #insert the skill into the database
    cursor.execute(
        """
        INSERT INTO posting_skills (job_id, skill_id, level_required, weight)
        VALUES (%s, %s, %s, %s)
        """,
        (job_id, skill_id, skill_experience_level, weight)
    )     

    #find ids and names of children of the skill
    cursor.execute(
        """
        SELECT id FROM skilltree_hierachy WHERE parent_id = %s
        """,
        (skill_id,)
    )
    children = cursor.fetchall()
    for child in children:
        print("repeating with skillID: " + str(child[0]))
        fill_skills_with_llm(cursor, child[0], job_id, model, client)


jobs = scrape_jobs(
    site_name=["glassdoor", "google"],
    search_term="software engineer",
    google_search_term="software engineer jobs near San Francisco, CA since yesterday",
    location="San Francisco, CA",
    results_wanted=1,
    hours_old=24,
    country_indeed='USA',
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
client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
MODEL = "mistral-small-24b-instruct-2501"
initialize_llm(MODEL, client)

for _, row in df.iterrows():
    for key in row.keys():
        row[key] = nan_to_none(row[key])  
    #check if job with same title, company and url already exists
    cursor.execute(
        """
        SELECT * FROM job_postings WHERE title = %s AND company = %s AND job_url = %s
        """,
        (row["title"], row["company"], row["job_url"])
    )
    
    #print a message if the job already exists
    if cursor.fetchone():
        print(f"Job {row['title']} at {row['company']} already exists in the database")
    else:
        #insert the job into the database
        cursor.execute(
            """
            INSERT INTO job_postings (title, company, location, job_type, salary_min, salary_max, job_url, description, date, salary_interval, company_logo_url, company_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id
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
        job_id = cursor.fetchone()[0]
        update_job_description(MODEL, client, row["description"])
        fill_skills_with_llm(cursor, 1, job_id, MODEL, client)

conn.commit()
cursor.close()
conn.close()

