# imports
import openai
import os
import psycopg2
from colorama import Fore, Back, Style
from dotenv import load_dotenv
import sqlparse


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
# constants
EMBEDDING_MODEL = "text-embedding-ada-002"


def debug(msg):
    verbose=os.getenv('VERBOSE')
    if verbose=="True":
        print(msg)  

conn = psycopg2.connect(
        host="localhost",
        database=os.getenv('DB'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'))

def product(text):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt="Given an input question, respond with syntactically correct PostgreSQL. Be creative but the query must be correct. Only use table called product. The product table has columns: category (character varying), sku (character varying), product (character varying), description (character varying), price (character varying), breadcrumb (character varying), product_url (character varying), money_back (BOOLEAN), rating (FLOAT), total_reviews (INTEGER). Give a Select query for product, product_url and price, where the category matches to the input question. Format the query in the correct format. Use Order_by command to order the rating in Descending order and list top 3 items. Where category can be Sleep Apnea, Snoring or Insomnia, any other Keyword attached with these words can be truncated." + text,
        temperature=0.3,
        max_tokens=60,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    query = response['choices'][0]['text']
    debug(query)
    sqlparse.format(query, reindent=True, keyword_case='upper')
    cur = conn.cursor()
    cur.execute(query)
    output = cur.fetchall()
    return(output)

def other_products(text):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt="Given an input question, respond with syntactically correct PostgreSQL. Be creative but the query must be correct. Only use table called product. The product table has columns: category (character varying), sku (character varying), product (character varying), description (character varying), price (character varying), breadcrumb (character varying), product_url (character varying), money_back (BOOLEAN), rating (FLOAT), total_reviews (INTEGER). Give a Select query for product, product_url and price, where the category matches to the input question. Format the query in the correct format. Use Order_by command to order the rating in Ascending order and list top 3 items. Where category can be Sleep Apnea, Snoring or Insomnia, any other Keyword attached with these words can be truncated." + text,
        temperature=0.3,
        max_tokens=60,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    query = response['choices'][0]['text']
    debug(query)
    sqlparse.format(query, reindent=True, keyword_case='upper')
    cur = conn.cursor()
    cur.execute(query)
    output = cur.fetchall()
    return(output)


def cheap_products(text):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt="Given an input question, respond with syntactically correct PostgreSQL. Be creative but the query must be correct. Only use table called product. The product table has columns: category (character varying), sku (character varying), product (character varying), description (character varying), price (character varying), breadcrumb (character varying), product_url (character varying), money_back (BOOLEAN), rating (FLOAT), total_reviews (INTEGER). Give a Select query for product, product_url and price, where the category matches to the input question. Format the query in the correct format. Use Order_by command to order the price in Ascending order and list top 1 items. Where category can be Sleep Apnea, Snoring or Insomnia, any other Keyword attached with these words can be truncated." + text,
        temperature=0.3,
        max_tokens=60,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    query = response['choices'][0]['text']
    debug(query)
    sqlparse.format(query, reindent=True, keyword_case='upper')
    cur = conn.cursor()
    cur.execute(query)
    output = cur.fetchall()
    return(output)


def general_product(text):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt="Given an input question, respond with syntactically correct PostgreSQL. Be creative but the query must be correct. Only use table called product. The product table has columns: category (character varying), sku (character varying), product (character varying), description (character varying), price (character varying), breadcrumb (character varying), product_url (character varying), money_back (BOOLEAN), rating (FLOAT), total_reviews (INTEGER). Give a Select query for product, product_url and price, by understanding the input question. Format the query in the correct format. Suggest any 2 product as per user Query." + text,
        temperature=0.3,
        max_tokens=60,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    query = response['choices'][0]['text']
    start = "SELECT"
    end = ";"
    start_pos = query.find(start)
    end_pos = query.find(end)
    query = query[(start_pos-1):(end_pos+1)].strip()
    debug(query)
    sqlparse.format(query, reindent=True, keyword_case='upper')
    cur = conn.cursor()
    cur.execute(query)
    output = cur.fetchall()
    return(output)