from selenium import webdriver
from selenium.webdriver.common.by import By
#from gpt4all import GPT4All
from bs4 import BeautifulSoup
import time
import json
import re

def safe_find_element(driver, by, value):
    try:
        return driver.find_element(by, value)
    except:
        return None  # Return None if the element is not found

def find_by_elementIndex_and_send(driver, idLst, idIndex, text):
    if idIndex < len(idLst):    
        print("Sending: " + text + " to " + idLst[idIndex])        
        ele = safe_find_element(driver, By.ID, idLst[idIndex])       
        if ele != None and ele.get_attribute("value") == "":
            ele.send_keys(text)
            
    

# Extract input tags from the HTML
def extract_input_tags(page_source: str):
    soup = BeautifulSoup(page_source, 'html.parser')
    input_tags = soup.find_all('input') + soup.find_all('textarea')
    label_tags = soup.find_all('label')

    label_fields = []
    for label_tag in label_tags:
        # Extract useful attributes such as id, name, type, etc.
        label_info = {
            'for': label_tag.get('for', 'N/A'),
            'text': label_tag.get_text(strip=True),
        }
        #clean * postfix from label text        
        if len(label_info['text']) > 0 and label_info['text'][-1] == '*':
            label_info['text'] = label_info['text'][:-1]
        if len(label_info['text']) > 0 and label_info['text'][0] == '*':
            label_info['text'] = label_info['text'][1:]
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

def find_id_with_possible_label(inputTags, possibleLabels):
    matches = []
    for tag in inputTags:
        for label in possibleLabels:            
            if re.match(label, tag['label'], re.IGNORECASE):
                print("Matched: " + label + " and " + tag['label'])
                matches.append(tag['id'])
                break
    return matches

# Initialize the browser
driver = webdriver.Chrome()
#model = GPT4All("Meta-Llama-3-8B-Instruct.Q4_0.gguf")

with open('tagtoLabel.json', 'r') as file:
    tagtoLabel = json.load(file)

with open('exampleInfo.json', 'r') as file:
    personalInfo = json.load(file)

 # Open the job application page
driver.get("https://rakuten.wd1.myworkdayjobs.com/RakutenRewards/job/Toronto-Canada/Software-Engineer--iOS-_1023319?source=LinkedIn")
while True:
    old_url = driver.current_url
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
            
    print("Input tags found: ")
    print(idStr)
    #with model.chat_session():
        #print(model.generate("In this list, output the tags most relevent to a job application, output results directly with no explaination and in comma seperated format: \n" + idStr, max_tokens=1024))

    # Fill in fields
    for field in personalInfo:
        if field != "experience":
            possibleLabels = tagtoLabel[field]
            IDs = find_id_with_possible_label(inputTags, possibleLabels)
            print(IDs)
            find_by_elementIndex_and_send(driver, IDs, 0, personalInfo[field])
    
    # Fill in experience
    experienceIndex = 0
    experience = personalInfo["experience"]
    for job in experience:
        for fieldName in job:
            fieldIds = find_id_with_possible_label(inputTags, tagtoLabel[fieldName])        
            if experienceIndex < len(fieldIds):
                print("Experience field: " + fieldName + " with IDs: " + str(fieldIds))
                find_by_elementIndex_and_send(driver, fieldIds, experienceIndex, job[fieldName])

        experienceIndex += 1



    while not driver.execute_script("return window.clicked;") and driver.current_url == old_url:            
        #if inputTags == []:
            #break
        time.sleep(0.1)          
    print("Clicked!")

