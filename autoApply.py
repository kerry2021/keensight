from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
#from gpt4all import GPT4All
from bs4 import BeautifulSoup
import time
import json

def safe_find_element(driver, by, value):
    try:
        return driver.find_element(by, value)
    except NoSuchElementException:
        return None  # Return None if the element is not found
    
# Extract input tags from the HTML
def extract_input_tags(page_source: str):
    soup = BeautifulSoup(page_source, 'html.parser')
    input_tags = soup.find_all('input')
    label_tags = soup.find_all('label')

    label_fields = []
    for label_tag in label_tags:
        # Extract useful attributes such as id, name, type, etc.
        label_info = {
            'for': label_tag.get('for', 'N/A'),
            'text': label_tag.text,
        }
        label_fields.append(label_info)

    # Collecting the input tags and their relevant attributes
    input_fields = []
    for input_tag in input_tags:
        # Try to locate labels for the input fields
        label_text = 'N/A'
        for label in label_fields:
            if label['for'] == input_tag.get('id'):
                label_text = label['text']
        
        # Extract useful attributes such as id, name, type, etc.        
        input_info = {
            'id': input_tag.get('id', 'N/A'),            
            'type': input_tag.get('type', 'N/A'),
            'label': label_text,
        }
        input_fields.append(input_info)

    return input_fields


# Initialize the browser
driver = webdriver.Chrome()
#model = GPT4All("Meta-Llama-3-8B-Instruct.Q4_0.gguf")

with open('tagtoID.json', 'r') as file:
    tagtoID = json.load(file)

with open('exampleInfo.json', 'r') as file:
    personalInfo = json.load(file)

 # Open the job application page
driver.get("https://job-boards.greenhouse.io/affirm/jobs/6257629003?gh_src=689c81d53us")
driver.execute_script("""
    window.clicked = false;
    document.body.addEventListener('click', function() {
    console.log('Clicked!');
        window.clicked = true;
    });
""")
source = driver.page_source
inputTags = extract_input_tags(source)
idStr = ""
for tag in inputTags:
    if tag['id'] != 'N/A':
        idStr += "(id: " + tag['id'] + ", "
    if tag['type'] != 'N/A':
        idStr += "type: " + tag['type'] + ", "
        idStr += "label: " + tag['label'] + ") "
        
print(idStr)
#with model.chat_session():
    #print(model.generate("In this list, output the tags most relevent to a job application, output results directly with no explaination and in comma seperated format: \n" + idStr, max_tokens=1024))

# Fill in fields
for field in personalInfo:
    possibleIDs = tagtoID[field]
    for ID in possibleIDs:
        if safe_find_element(driver, By.ID, ID) != None:
            safe_find_element(driver, By.ID, ID).send_keys(personalInfo[field])
            break


# Upload resume
#driver.find_element(By.ID, "resume-upload").send_keys("path_to_resume.pdf")

# Submit the form
#driver.find_element(By.ID, "submit-button").click()

# Wait for confirmation

while not driver.execute_script("return window.clicked;"):
        
    time.sleep(0.1)
print("Clicked!")

input("Press Enter to quit the browser...")
driver.quit()