from datetime import datetime
import time
import os
import csv 

import openai
import pandas as pd
import numpy as np
from products import product, other_products, cheap_products, general_product
from dotenv import load_dotenv
from openai.embeddings_utils import cosine_similarity

from colors import pr_cyan,pr_bot_response
from debug_utils import debug_steps,debug, debug_attribute
from constants import GENERAL_QUERY,SYMPTOM_QUERY,PRODUCT_QUERY,PROGRAM_QUERY,GENERAL_PRODUCT_QUERY,davinci,turbo,SEPARATORS
from utils import get_db_connection,get_props_from_message

# Insert your API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# constants
DEBUG_CSV = "debug_4.csv"

RESPONSE_FOR_INVALID_QUERY = "I am a Resmed chatbot, I can't help with that"
UNABLE_TO_FIND_PRODUCTS_IN_DB = "Unable to find products in DB"

YES = "Yes"
NO = "No"

VERBOSE = os.getenv('VERBOSE')
EXPECTED_SIMILARITY = 0.85

conn,cur = get_db_connection()
# constants

outputs = []

# Zero shot learning
def call_chat_completion_api(row,message_log,level):
    debug("Let's ask Chat completion API to answer user query") 
    PROMPT,MODEL,TOKENS,TEMPERATURE = message_log,turbo,150,0
    # bot_response=""
    response = openai.ChatCompletion.create(
            model=MODEL,
            messages = PROMPT,
            max_tokens=TOKENS,
            temperature=TEMPERATURE
            # stream=True
        )
    

    # TODO: Once everything works fine then switch back to stream
    # pr_bot_response("",end="")
    # for chunk in response:
    #     if "content" in chunk.choices[0].delta.keys():
    #         bot_response+=chunk.choices[0].delta.content
    #         pr_cyan(f"{chunk.choices[0].delta.content}",end="")
    # print()
    
    # Query type is {query_type} / similarity {highest_similarity*100} less than {EXPECTED_SIMILARITY*100}
    debug_steps(row,f'{level} - {call_chat_completion_api.__name__} - {response}, Additional information: Model-{MODEL}, Tokens-{TOKENS}, TEMPERATURE-{TEMPERATURE}, PROMPT-{PROMPT}"',level)
    response_text = response.choices[0].message.content.strip()
    response_tokens = response.usage['total_tokens']
    return response_text, response_tokens

def get_answer_from_gpt(row,prompt,level):
    # Multi shot learning
    TOKENS,TEMPERATURE,MODEL,STOP = 200,0,davinci,[" Human:", " Bot:"]
    response = openai.Completion.create(
    model=MODEL,
    prompt=prompt,
    temperature=TEMPERATURE,
    max_tokens=TOKENS,
    stop=STOP
    )

    
    debug_steps(row,f"{level} - {get_answer_from_gpt.__name__} - {response}, Additional information: Model-{MODEL},Tokens-{TOKENS}, TEMPERATURE-{TEMPERATURE},STOP-{STOP},PROMPT-{prompt}",level)
    
    response_text = response.choices[0].text.strip()
    response_token = response.usage['total_tokens']
    return response_text, response_token

def find_what_user_expects(row,user_input,level):
    # Multi shot learning
    PROMPT,TOKENS,TEMPERATURE,MODEL,STOP = f"Find what user expects from the chatbot system Expected Responses are {SYMPTOM_QUERY},{PRODUCT_QUERY} H: I forget a lot and not able to concentrate A:{SYMPTOM_QUERY} H: I have Mood disruptions, especially anxiety, depression and irritability A:{SYMPTOM_QUERY} H:What is the price of CPAP mask A:{PRODUCT_QUERY} H:{user_input} A:",10,0,davinci,[" H:", " A:"]
    response = openai.Completion.create(
    model=MODEL,
    prompt=PROMPT,
    temperature=TEMPERATURE,
    max_tokens=TOKENS,
    stop=STOP
    )
    
    debug_steps(row,f"{level} - {find_what_user_expects.__name__} - {response}, Additional information: Model-{MODEL},Tokens-{TOKENS}, TEMPERATURE-{TEMPERATURE},STOP-{STOP},PROMPT-{PROMPT}",level)
    
    response_text = response.choices[0].text.strip()
    response_tokens = response.usage['total_tokens']
    return response_text, response_tokens

def show_products(output):
    prod_response = '\n'
    if(len(output)>0):
        items = output[0]
        output = output if len(output)==1 else output[0:2]
        debug_attribute("DB Output",output)
        if(len(items)==3):
            pr_cyan(f"Here are some products, which matches your search {output}")
            for prod, url,price in output:
                products = prod + " - " + url + " - $" + str(price)
                prod_response += products + "\n"
    return prod_response

def product_query(row,entity,user_input,level):
    output, response_token_product = general_product(row,entity,user_input,level)

    if len(output) == 0:
        bot_response = UNABLE_TO_FIND_PRODUCTS_IN_DB
    else:
        bot_response = show_products(output)
    return bot_response

def identify_symptom(user_input):
    TOKENS = 100
    # Multi shot learning
    response = openai.Completion.create(
    model="text-davinci-003",
    prompt=f"Snoring, sleep apnea, and insomnia are all different sleep disorders with distinct symptoms and causes. Here are some differences that may help you differentiate between the three:Snoring:Characterized by loud, rhythmic breathing sounds during sleep,Usually harmless, although it can still disrupt your sleep or your partner's sleep Typically caused by a partial obstruction in the airway, often due to relaxed muscles in the throat or nasal congestion,Usually associated with pauses in breathing or gasping sensations during sleep,Change in the level of attention, concentration, or memory.Sleep apnea:Characterized by pauses in breathing or shallow breaths during sleep,Often accompanied by loud snoring and gasping or choking sensations during sleep,Can lead to excessive daytime sleepiness,Being Overweight(adds fat around the neck and airway),Having inflamed tonsils and adenoids,Having blocked nose due to allergy or cold,Structural problem with shape of the nose, neck or jaw,Frequently urinating at night,Waking up with night sweats,High blood pressure,Mood swings,Impotence and reduced sex drive.Insomnia:A sleep disorder characterized by difficulty falling asleep,staying asleep,or waking up too early in the morning,Often associated with anxiety, stress, or other psychological factors, as well as medical conditions or medications,Can lead to excessive daytime sleepiness, fatigue, irritability, difficulty concentrating, and other health problems,Making more mistakes or having accidents,Feel tired or sleepy during the day.Extract Sleep disorder from user input.Q: Sore throat on awakening A: Snoring Q: Excessive daytime sleepiness A: Snoring Q:I have fever A: Not a sleep disorder Q: Mood Swings A: Sleep Apnea Q: Difficulty staying asleep A: Insomnia Q:{user_input} A:",
    max_tokens=TOKENS,
    temperature=0,
    )
    print("->>>>>>",response)
    response_text = response.choices[0].text.strip()
    response_token_symptom = response.usage['total_tokens']
    return response_text, response_token_symptom
    


def get_products(row,query_type,user_input,entity):
    prod_response=""
    debug_steps(row,f"{query_type}",level=3)
    if "cheap" in user_input or "cheapest" in user_input:
        if len(outputs)==0:
            output,response_token_product = cheap_products(row,user_input,level=3)
        else:
            output,response_token_product = cheap_products(row,outputs[-1],level=3)
        prod_response += show_products(output)
    else:

        prod_response += product_query(row,entity,user_input,level=3)
    return prod_response


def query_to_resmed(row,query_type,user_input,response_from_gpt):
    response,intent,entity,product_suggestion = get_props_from_message(response_from_gpt)
    product_suggestion=product_suggestion.lower().replace("resmed","")
    debug_attribute("Response",response)
    debug_attribute("intent",intent)
    debug_attribute("entity",entity)
    debug_attribute("product_suggestion",product_suggestion)
    bot_response = ""
    
    if PRODUCT_QUERY==query_type:
        prod_response, response_token_product=get_products(row,query_type,user_input,entity)
        print("->>>>>> Check here",prod_response)
        bot_response = response + prod_response
    elif(SYMPTOM_QUERY==query_type):
        symptom = identify_symptom(user_input)
        debug_attribute("Identify symptom",symptom)
        found_symptom = symptom=="Sleep Apnea" or symptom=="Insomnia" or symptom=="Snoring"
        if (SYMPTOM_QUERY in query_type):
            if(found_symptom):
                debug_steps(row,f"{SYMPTOM_QUERY},found symptom & suggest products",level=5)
                MSG = f"This appears to be a condition called {symptom}.It is a fairly common condition, which can be addressed. We recommend you take an assessment and also speak to a Doctor."
                SLEEP_ASSESSMENT_INFO="For more information please visit'\033]8;;https://info.resmed.co.in/free-sleep-assessment\aSleep Assessment\033]8;;\a'"
                pr_cyan(SLEEP_ASSESSMENT_INFO)
                bot_response= f"{MSG}\n{SLEEP_ASSESSMENT_INFO}"
                output = product(row,symptom,level=6)
                prod_response = show_products(output)
                bot_response += prod_response
            elif(symptom=="common"):
                debug_steps(row,f"{SYMPTOM_QUERY}, Symptoms are common",level=5)
                bot_response = "Your symptoms are more common to define the exact syndrome. can you please provide more detail:"
    else:
        bot_response = response
    return bot_response
  
def write_to_db(db,user_input,bot_response,probability,response_accepted,response_time,time_stamp,source):
    if db:
        query = f"INSERT INTO chatbot_datas (prompt,completion,probability,response_accepted,response_time,time_stamp,source) VALUES('{user_input}','{bot_response}','{probability}','{response_accepted}',{response_time},'{time_stamp}','{source}');"
        debug(f"Query to execute - {query}")
        cur.execute(query)
        conn.commit()
        debug("Data added successfully")
    else:
        debug("DB insert is disabled")
     
def write_logs_to_csv(mode,fields,row,max_columns,bot_response):
    if VERBOSE=="True":
        debug(f"Writing the logs in {DEBUG_CSV}")
        with open(DEBUG_CSV, mode) as csvfile: 
            # creating a csv writer object 
            csvwriter = csv.writer(csvfile) 
                
            if mode=='w':
                # writing the fields 
                csvwriter.writerow(fields) 
                
            row_length = len(row)
            if(row_length!=max_columns-1):
                dummy_rows_to_add = max_columns-row_length-2
                row.extend(('-'*dummy_rows_to_add).split('-'))
            # writing the data rows 
            row[1] = bot_response
            csvwriter.writerows([row])
  
def resmed_chatbot(user_input,message_log,db=True):
    MODE = 'w'
    fields = ["user_input","bot_response","level1","level2","level3","level4","level5","level6","level7","level8","cost"]
    MAX_COLUMNS = len(fields)
    row = [""] * MAX_COLUMNS
    row[0] = user_input
    
    debug_steps(row,f"Message log - {message_log}",level=7)
    
    if os.path.exists(DEBUG_CSV):
        MODE='a'
    
    # Append user_input 
    prompt=f"{message_log}Human:{user_input}\nAI:"
    prompt = prompt.replace(SEPARATORS,'')
    
    debug_steps(row,f"Prompt - {prompt}",level=8)
    
    # Append question mark at end of user_input
    # user_input += "?"
    # If user types single word input then system gets confused so adding what is as a prefix
    if (len(user_input.split(' '))==1):
        user_input = f"What is {user_input}"
            
    time_stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    response_accepted = True
    bot_response = ""
    
    response_time = 0
    probability = 0
    source = ""
    query_type = ""

    start_time = time.time()
        
    
    response_from_gpt, response_token = get_answer_from_gpt(row,prompt,level=1)
    query_type,response_tokens = find_what_user_expects(row,user_input,level=2)
    query_type = query_type.strip()
    debug_attribute("query_type - ",query_type)  
    debug_steps(row,f"Resmed response - {response_from_gpt}",level=7)
    
    # and query_type!=PRODUCT_QUERY and query_type!=GENERAL_PRODUCT_QUERY 
    if("sorry" in response_from_gpt and query_type!="" and "Resmed chatbot" in response_from_gpt):
        bot_response=response_from_gpt
    else:
        bot_response = query_to_resmed(row,query_type,user_input,response_from_gpt)
    
    if((not bot_response or len(bot_response)<10) and bot_response!=RESPONSE_FOR_INVALID_QUERY):
        bot_response = response_from_gpt

        
    response_time = time.time() - start_time
    
    # Bot response may include single quotes when we pass that with conn.execute will return syntax error
    # So, let's replace single quotes with double quotes
    # Reference: https://stackoverflow.com/questions/12316953/insert-text-with-single-quotes-in-postgresql
    # TODO: Find smart way to replace single quote to all string columns
    user_input = user_input.replace("'","''")[:500]
    bot_response = bot_response.replace("'", "''")[:999]
    source = source.replace("'", "''")
    
    write_to_db(db,user_input,bot_response,probability,response_accepted,response_time,time_stamp,source)

    #symptom,response_token_cost = identify_symptom(user_input)
    token_calculation = response_token + response_tokens + response_token_symptom + response_token_product
    cost_of_davinci = 0.024
    cost = (token_calculation * cost_of_davinci) / 1000
    
    debug_steps(row,f"total cost - {cost}",level="cost")
    #debug(f"cost - {cost}")

    debug(f"Response time in seconds - {response_time}")

    

    write_logs_to_csv(MODE,fields,row,MAX_COLUMNS,bot_response)
    
    # Add the chatbot's response to the conversation history and print it to the console
    if response_from_gpt!=RESPONSE_FOR_INVALID_QUERY and response_from_gpt!=UNABLE_TO_FIND_PRODUCTS_IN_DB and "sorry" not in response_from_gpt and "Resmed chatbot" not in response_from_gpt:
        print("Inside if")
        # User asked an invalid query to our system so, let's remove their query from message logs
        message_log+=f"Human:{user_input}\nBot:{bot_response}{SEPARATORS}"
    else:
        print("Inside else ->>>>>>>>>")
        pr_cyan(response_from_gpt)

    pr_bot_response(bot_response)
    return bot_response,message_log
