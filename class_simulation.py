import asyncio
import os
import pathlib
import time
from typing import Dict

import cattrs
import yaml

from chat_log import ChatLog
from common import check_path_or_create, dump_to_pickle
from persona import Persona
from student_agent import SimAgent

os.environ["OPENAI_API_KEY"] = "ENTER KEY HERE"


class Simulation:
    def __init__(self, collection, langchain_chroma, teacher_gender, student_year):
        self.collection = collection
        self.langchain_chroma = langchain_chroma

        self.agents: Dict[str, SimAgent] = {}

        self.general_chat_history: [Dict[int, list]] = {}
        self.general_agent_data: Dict[int, Dict[str, object]] = {}
        self.new_general_agent_data: Dict[int, Dict[str, object]] = {}

        self.difficulty = ''

        self.teacher_gender = teacher_gender

        self.curr_tick = 0

        self.class_year = student_year
        self.student_age = self.primary_year_check(student_year)

    """ Loads the necessary Persona Data from YAML files given Difficulty """
    def load(self, difficulty='easy'):
        # Define Parent Path
        curr_path = pathlib.Path(__file__).parent.resolve()

        self.difficulty = difficulty

        # Define Path of Personas to Load
        personas_path = f'{curr_path}/resources/personas/{difficulty}_personas.yaml'

        # Open Persona File
        with open(personas_path, 'r') as f:
            # Load each Persona Data from YAML file
            for persona_data in yaml.load(f, Loader=yaml.FullLoader):
                # Structure it into a Persona Object
                persona = cattrs.structure(persona_data, Persona)

                # Set Student Age based on Class Chosen before starting Class Simulation
                persona.age = self.student_age

                # Create Student Agent
                agent = SimAgent(persona.id(), self.collection, self.langchain_chroma, self.class_year)
                # Assign Persona to Student Agent
                agent.persona = persona

                # Save Student Agent in List of Agents
                self.agents[persona.id()] = agent

                # Check Characteristics
                self.agents[persona.id()].characteristics_check()

        list_of_agent_guids = [agent.persona.guid for agent in self.agents.values()]

        # Define list of Emoticons
        self.agent_emoticons = [None] * len(list_of_agent_guids)

        self.general_agent_data = {}

    """ Progresses the Class Simulation, takes in an input by the User and goes through the Student Agent to generate a Response """
    async def tick(self, user_input: str, user_input_time: float, chat_analysis_resp: object, question_suitability_resp: object):

        tick_start_time = round(time.time(), 3)

        # Process Agents and get Generated Responses
        process_agents_resp = await self.process_agents(user_input,
                                                        chat_analysis_resp,
                                                        question_suitability_resp)

        process_agents_end = round(time.time(), 3)

        # If not valid response, then show error to User
        if not process_agents_resp['valid']:
            return process_agents_resp

        # Get Responses from Agents
        new_text = process_agents_resp['response']

        self.agent_emoticons = []

        # Get Current Emoticons for each Agent
        for agent in self.agents.values():
            self.agent_emoticons.append(agent.curr_emoticon)

        """ --------------------------- Append to General Chat Histories --------------------------- """
        # Initialise Chat Log for Current Tick
        self.general_chat_history[self.curr_tick] = []

        # Append User Input to Chat Log
        self.general_chat_history[self.curr_tick].append(ChatLog(person_type='user',
                                                                 guid='teacher',
                                                                 text=f'Teacher: {user_input}',
                                                                 tick=self.curr_tick,
                                                                 timestamp=user_input_time,
                                                                 agent_emoticons=self.agent_emoticons,
                                                                 chat_analysis_resp=chat_analysis_resp,
                                                                 question_suitability_resp=question_suitability_resp))

        # Loop through and append Generated Responses to Chat Log
        for i in new_text:
            self.general_chat_history[self.curr_tick].append(ChatLog(person_type='agent',
                                                                     guid=i['agent_guid'],
                                                                     text=i['text'],
                                                                     tick=self.curr_tick,
                                                                     timestamp=process_agents_end))
        """ --------------------------- Append to General Chat Histories --------------------------- """

        """ --------- Add memories of responses to each student which isn't distracted. --------- """
        # Loop through Student Agents, and add Memories based on whether agent was distracted or not
        for agent in self.agents.values():
            if agent.curr_action != agent.distracted:
                for i in new_text:
                    # If generated response of agent is not of its own, then add it to its memory
                    if i['agent_guid'] != agent.guid:
                        agent.memories.append(i['text'])
        """ --------- Add memories of responses to each student which isn't distracted. --------- """

        tick_finish_time = round(time.time(), 3)

        self.general_agent_data[self.curr_tick] = {}

        # Loop through Agents and adjust Current Tick Values
        for i in self.agents.values():
            # Set tick of Current Tick Data
            i.curr_tick_data.tick = self.curr_tick

            # Set Finishing time of Current Tick Data
            i.curr_tick_data.tick_finish_timestamp = tick_finish_time

            # Append the current tick to the General Agent Data
            self.general_agent_data[self.curr_tick][i.guid] = i.curr_tick_data.to_obj()

        # Increment Tick for next Tick Activation
        self.curr_tick += 1

        # Return valid Generated Responses
        return {'valid': True, 'response': new_text}

    """ Process Student Agents, Creates Asynchronous Tasks to process Student Agents asynchronously """
    async def process_agents(self, user_input, chat_analysis_resp, question_suitability_resp):
        tasks = []
        # Loops through Student Agents and Creates Async Task to Process Agent
        for agent in self.agents.values():
            task = asyncio.create_task(self.process_agent(agent, user_input, chat_analysis_resp, question_suitability_resp))
            tasks.append(task)

        # Gathers Responses once all tasks are finished
        results = await asyncio.gather(*tasks)

        fin_results = []

        # Loops through Responses, if a non-valid response is received, then show to User
        for result in results:
            if result != None:
                if not result['valid']:
                    return result
                # Else, add it to list of responses
                else:
                    fin_results.append(result['response'])

        # Return list of Responses
        return {'valid': True, 'response': fin_results}

    """ Processes Specific Student Agent; Goes through the entire pipeline of activating a Student Agent """
    async def process_agent(self, agent, user_input, chat_analysis_resp, question_suitability_resp):
        # Use User Input and Response from Analysis Models to make Student Agent choose an action
        returned_data = await agent.choose_action(user_input, self.teacher_gender, chat_analysis_resp, question_suitability_resp)

        # If error occurred some time during choosing an action, then show it to User
        if not returned_data['valid']:
            return returned_data

        # Carry out Action
        agent_resp = await agent.curr_action

        # If error occurred some time during choosing an action, then show it to User
        if not agent_resp['valid']:
            return agent_resp

        # Get Generated Response from finished Action
        agent_text = agent_resp['response']

        # If not None, then return the response
        if agent_text is not None:
            return agent_resp

    """ Saves the Simulation Data to Pickle Files """
    async def save_data(self, folder_name):
        # Define the Folder Path to save to
        folder_path = f'./logger/{folder_name}'

        # Check if Path exists, if it doesn't then create
        check_path_or_create(folder_path)

        """ ------------------------- Save ChromaDB Data ------------------------- """
        # Get all Vectors in Collection
        collection_data = self.collection.get()

        # Dump Data into Pickle
        dump_to_pickle(f'{folder_path}/chromadb_data.pickle', collection_data)
        """ ------------------------- Save ChromaDB Data ------------------------- """

        """ ------------------------- Save Agent Data ------------------------- """
        student_final_data = {}

        # Loop through Student Agents in List of Agents
        for key, value in self.agents.items():
            # Convert Student Agent Object into Dictionary for Saving
            student_final_data[key] = value.to_obj_for_saving()

            # Convert Persona Object into Dictionary for Saving
            student_final_data[key]['persona'] = student_final_data[key]['persona'].to_obj()

        # Save Student Agent Final to File
        dump_to_pickle(f'{folder_path}/student_final_data.pickle', student_final_data)

        # Save Student Agent Past Data to File
        dump_to_pickle(f'{folder_path}/student_past_data.pickle', self.general_agent_data)
        """ ------------------------- Save Agent Data ------------------------- """

        """ ------------------------- Save Chat History Data ------------------------- """
        converted_chat_history = {}

        # Loop through Chat Logs in General Chat History
        for key, chat_log_list in self.general_chat_history.items():
            # Convert each ChatLog object in the list using its to_obj() method
            converted_chat_history[key] = [chat_log_obj.to_obj() for chat_log_obj in chat_log_list]

        # Save Converted Chat Logs to File
        dump_to_pickle(f'{folder_path}/general_chat_history.pickle', converted_chat_history)
        """ ------------------------- Save Chat History Data ------------------------- """

    """ Converts Class chosen to Age to be assigned to the Student Agents  """
    def primary_year_check(self, primary_year):
        if primary_year == "Year 5":
            return 10
        elif primary_year == "Year 6":
            return 11
