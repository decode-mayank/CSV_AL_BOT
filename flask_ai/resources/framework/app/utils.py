import re

from ..debug_utils import debug_attribute, debug_steps
from .constants import SLEEP_ASSESSMENT_HTML_RESPONSE, SLEEP_ASSESSMENT_RAW_RESPONSE, UNABLE_TO_FIND_PRODUCTS_IN_DB, OUTPUTS
from .products import product, cheap_products, general_product, other_products


def show_products(output, html_response):
    prod_response = '\n'
    raw_prod_response = "\n"
    if (len(output) > 0):
        items = output[0]
        output = output if len(output) == 1 else output[0:4]
        debug_attribute("DB Output", output)
        if (len(items) == 3):
            for prod, url, price in output:
                prod_response += f'</br><a href="{url}" target="_blank">{prod}</a> - $ {price}\n </br>' if html_response else f"{prod} - {url} - $ {str(price)}\n"
                raw_prod_response += f'{prod}-{url}\n'
    return prod_response, raw_prod_response


def get_general_product(row, user_input, query_to_db, html_response, level):
    output, response_token_product = general_product(
        row, user_input, query_to_db, level)

    if len(output) == 0:
        prod_response = UNABLE_TO_FIND_PRODUCTS_IN_DB
    else:
        prod_response, raw_prod_response = show_products(output, html_response)
    return prod_response, raw_prod_response, response_token_product


def get_products(row, user_input, query_to_db, html_response):
    prod_response = ""
    raw_prod_response=""
    if "cheap" in user_input or "cheapest" in user_input:
        if "Product" in query_to_db and OUTPUTS != []:
            output, response_token_product = cheap_products(
                row, OUTPUTS[-2], query_to_db, level=3)
        else:
            output, response_token_product = cheap_products(
                row, user_input, query_to_db, level=3)
        prod_response, raw_prod_response = show_products(output, html_response)
    elif "Load More" in query_to_db:
        output, response_token_product = other_products(
            row, OUTPUTS[-2], level=3)
        prod_response, raw_prod_response = show_products(output, html_response)
    else:
        prod_response, raw_prod_response, response_token_product = get_general_product(
            row, user_input, query_to_db, html_response, level=3)
    return prod_response, raw_prod_response, response_token_product


def search_product(row, props,user_input, response_from_gpt, html_response):
    response, symptom, suggest, intent, entity, product_suggestion, price_range, product_type = props
    query_to_db = ""
    if "None" in price_range:
        query_to_db = f"{entity}"
    else:
        price_range = price_range.replace("$", "")
        query_to_db = f"{entity},{product_suggestion},{price_range}"
    debug_attribute("query_to_db", query_to_db)
    prod_response, raw_prod_response, response_token_product = get_products(
        row, user_input, query_to_db, html_response)
    tokens = response_token_product
    if "$" in response:
        # What is the price of BongoRx Starter Kit
        response = ""
        raw_response = ""
    bot_response = response + prod_response
    raw_response = response_from_gpt + raw_prod_response

    return bot_response, raw_response, tokens


def chatbot_logic(row,props, user_input, response_from_gpt, html_response):
    response, symptom, suggest, intent, entity, product_suggestion, price_range, product_type = props
    product_suggestion = product_suggestion.lower().replace("resmed", "")
    debug_attribute("Response", response)
    debug_attribute("Symptom", symptom)
    debug_attribute("Show products", suggest)
    debug_attribute("intent", intent)
    debug_attribute("entity", entity)
    debug_attribute("product_suggestion", product_suggestion)
    debug_attribute("price_range", price_range)
    debug_attribute("product_type", product_type)
    raw_response = ""
    bot_response = ""
    tokens = 0
    OUTPUTS.append(entity)

    if intent.lower().strip() == "symptom query":
        MSG = f"{response} \n We recommend you take an assessment and also speak to a Doctor."
        bot_response = f"{MSG}\n{SLEEP_ASSESSMENT_HTML_RESPONSE if html_response else SLEEP_ASSESSMENT_RAW_RESPONSE}"
        raw_response = f"{MSG}\n{SLEEP_ASSESSMENT_RAW_RESPONSE}"

        output, prod_tokens = product(row, symptom, level=4)
        prod_response,raw_prod_response = show_products(output, html_response)

        # Add product response to bot_response, raw_response
        bot_response += prod_response
        raw_response+=raw_prod_response
        tokens += prod_tokens
    elif not intent and not entity:
        '''
        suggest humidifier
        can you explain me on what scenarios does the above two product work?
        '''
        bot_response = response
    else:
        if suggest.lower() == 'false' or product_suggestion.lower() == 'none' or entity.lower() == 'product':
            bot_response = response
        else:
            bot_response, raw_response, tokens = search_product(
                row, props,user_input, response_from_gpt, html_response)
            
                
    if (not bot_response or len(bot_response) < 10):
        bot_response = response

    return bot_response, raw_response, tokens


def extract_data(pattern, message):
    results = re.search(pattern, message)
    return results.group(1) if results else ""


def get_props_from_message(message):
    '''
    Sample Input:
    Symptom: Sleep apnea, Suggest: True, Intent: Symptom, Entity: Sleep apnea, Product Suggestion: Sleep apnea, Price Range: None, Type: None, Response: It is possible that you may be suffering from sleep apnea. Sleep apnea is a condition where your breathing is interrupted during sleep, causing you to wake up with a sore throat. We recommend consulting a physician to get a proper diagnosis and treatment plan. ResMed offers a range of products to help treat sleep apnea, including CPAP machines, masks, and accessories.

    Sample Output:
    (It is possible that you may be suffering from sleep apnea. Sleep apnea is a condition where your breathing is interrupted during sleep, causing you to wake up with a sore throat. We recommend consulting a physician to get a proper diagnosis and treatment plan. ResMed offers a range of products to help treat sleep apnea, including CPAP machines, masks, and accessories.,Sleep apnea,true,Symptom,
    ,sleep apnea,None,None
    '''
    message = message.strip()
    intent, entity, product_suggestion, price_range = "", "", "", ""
    # Extracting the symptom
    symptom = extract_data(r'Symptom: (.*) Suggest:', message).capitalize().replace(",","")
    # Extracting the suggest
    suggest_product = extract_data(
        r'Suggest: (.*) Intent', message).lower().replace(",", "")
    # Extracting the Intent
    intent = extract_data(r'Intent: (.*), Entity', message)
    # Extracting the Entity
    entity = extract_data(r'Entity: (.*), Product Suggestion', message)
    # Extracting the Product Suggestion
    product_suggestion = extract_data(
        r'Product Suggestion: (.*), Price Range', message)
    # Extract price range
    price_range = extract_data(r'Price Range:\s*(.*), Type', message)
    # Extract type
    product_type = extract_data(r'Type: (.*) Response:', message)
    # Response
    response = extract_data(r'Response: (.*)', message)
    return response, symptom,suggest_product, intent, entity, product_suggestion, price_range, product_type
