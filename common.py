import json
import os
import pathlib
import pickle
import time

import bcrypt
import httpx

import chromadb
from chromadb.utils import embedding_functions

from langchain.prompts import load_prompt
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.chroma import Chroma

import openai

# Load API key from environment variable or configuration file
os.environ["OPENAI_API_KEY"] = "ENTER KEY HERE"


def check_path_or_create(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Path '{path}' created.")
    else:
        print(f"Path '{path}' already exists.")


def create_file_if_not_exists(path):
    if not os.path.isfile(path):
        with open(path, 'w') as file:
            # Creates an empty .txt file
            pass
        print(f"File '{path}' created.")
    else:
        print(f"File '{path}' already exists.")


def dump_to_pickle(path, data):
    create_file_if_not_exists(path)

    with open(path, 'wb') as file:
        pickle.dump(data, file)

        # print('data has been pickled')

def load_from_pickle(path):
    with open(path, 'rb') as file:
        data = pickle.load(file)

        # print('data has been loaded from pickle')

        return data


async def load_and_run_prompt(prompt_file,
                              print_prompt=False,
                              model_name="gpt-4-1106-preview",
                              temperature=0.2,
                              max_tokens_limit=512,
                              stop_sequences=None,
                              top_p=1,
                              frequency_penalty=0,
                              presence_penalty=0,
                              **kwargs):

    if stop_sequences is None:
        stop_sequences = ["\n"]

    path = pathlib.Path(__file__).parent.resolve()

    prompt = load_prompt(f'{path}/resources/prompt_templates/{prompt_file}')

    printed_prompt = prompt.format(**kwargs)

    if print_prompt:
        print(printed_prompt)

    url = "https://api.openai.com/v1/chat/completions?"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "system", "content": printed_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens_limit,
        "stop": stop_sequences,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
    }

    try:
        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(20)
            response = await client.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)

            return {'valid': True, 'response': response.json()['choices'][0]['message']['content'] }

    except httpx.ReadTimeout:
        return {'valid': False, 'response': 'Timed Out, please Try Again.'}


async def run_prompt_and_convert_to_obj(prompt_file,
                                        temperature=0.2,
                                        max_tokens_limit=512,
                                        model_name="gpt-4-1106-preview",
                                        print_prompt=False,
                                        **kwargs):

    json_to_obj_resp = {}
    error_count = 0

    time_start = round(time.time(), 3)

    while error_count != 3:
        response = await load_and_run_prompt(prompt_file,
                                             temperature=temperature,
                                             max_tokens_limit=max_tokens_limit,
                                             model_name=model_name,
                                             print_prompt=print_prompt,
                                             **kwargs)

        if response['valid']:

            json_to_obj_resp = await convert_json_to_object(response['response'])

            if json_to_obj_resp['valid']:
                print(json_to_obj_resp)
                print(f'{prompt_file} Time Taken: {round(time.time() - time_start, 3)}')
                break

            print('-----')
            print(response)
            print('-----')

        error_count += 1

    if not json_to_obj_resp['valid']:
        return {'valid': False, 'response': f'Error Occurred after trying to run Prompt File 3 times: {prompt_file}'}
    else:
        return json_to_obj_resp


async def convert_json_to_object(prompt_resp):
    try:
        prompt_resp = json.loads(prompt_resp)

        return {'valid': True, 'response': prompt_resp}
    except:
        print('ERROR OCCURRED RUNNING: ', prompt_resp)

        return {'valid': False, 'response': 'Error Occurred parsing Prompt Response'}


def init_chromadb_connections(path, collection_name, model_name):
    chromadb_client = chromadb.PersistentClient(path=path)

    collection = chromadb_client.get_or_create_collection(name=collection_name,
                                                          embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                                                              api_key=os.getenv('OPENAI_API_KEY'),
                                                              model_name=model_name
                                                          ),
                                                          metadata={"hnsw:space": "cosine"})

    langchain_chroma = Chroma(
        client=chromadb_client,
        collection_name=collection_name,
        embedding_function=OpenAIEmbeddings(),
    )

    return collection, langchain_chroma, chromadb_client


def validate_teacher_details_input(teacher_name, teacher_surname):

    if teacher_name == '' or teacher_surname == '':
        return {'code': 400, 'status_text': 'Teacher Name or Surname are Empty', 'valid': False}

    if " " in teacher_name or " " in teacher_surname:
        return {'code': 400, 'status_text': 'Teacher Name or Surname contains a Space', 'valid': False}

    if not teacher_name.isalpha() or not teacher_surname.isalpha():
        return {'code': 400, 'status_text': 'Teacher Name or Surname contains a Number', 'valid': False}

    return {'code': 200, 'status_text': 'Valid Name and Surname', 'valid': True}


""" Checks User Inputted Password with the Hashed Password saved to File """
def checkPassword(thisPass, hashedPass):
    # Encode User Inputted Password into utf-8
    b = thisPass.encode("utf-8")

    try:
        # Checks User Inputted Password with Hashed Password saved in File
        check_pw_result = bcrypt.checkpw(b, hashedPass)

        # Set correct_pass based on whether User Inputted Password == Hashed Password
        res = {'valid': True, 'correct_pass': check_pw_result}
    except:
        res = {'valid': False}

    return res