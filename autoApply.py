from selenium import webdriver
from selenium.webdriver.common.by import By
#from gpt4all import GPT4All
from bs4 import BeautifulSoup
import time
import json

def safe_find_element(driver, by, value):
    try:
        return driver.find_element(by, value)
    except:
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
            'text': label_tag.get_text(strip=True),
        }
        #clean * postfix from label text        
        if len(label_info['text']) > 0 and label_info['text'][-1] == '*':
            label_info['text'] = label_info['text'][:-1]
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

with open('tagtoLabel.json', 'r') as file:
    tagtoLabel = json.load(file)

with open('exampleInfo.json', 'r') as file:
    personalInfo = json.load(file)

 # Open the job application page
driver.get("https://clio.wd3.myworkdayjobs.com/en-US/ClioCareerSite/job/Vancouver/Software-Developer_REQ-1532?source=Linkedin")

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
        possibleLabels = tagtoLabel[field]
        for label in possibleLabels:
            #find the id of the label
            ID = 'N/A'
            for tag in inputTags:                
                if tag['label'] == label:
                    ID = tag['id']
                    break
            ele = safe_find_element(driver, By.ID, ID)
            if ele != None and id != 'N/A' and ele.get_attribute("value") == "":                
                ele.send_keys(personalInfo[field])
                break

    while not driver.execute_script("return window.clicked;") and driver.current_url == old_url:            
        if inputTags == []:
            break
        time.sleep(0.1)          
    print("Clicked!")

input("Press Enter to quit the browser...")
driver.quit()