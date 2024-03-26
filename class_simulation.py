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

    def load(self, difficulty='easy'):
        """Load the simulation data from the YAML files."""
        curr_path = pathlib.Path(__file__).parent.resolve()

        self.difficulty = difficulty

        personas_path = f'{curr_path}/resources/personas/{difficulty}_personas.yaml'

        with open(personas_path, 'r') as f:
            for persona_data in yaml.load(f, Loader=yaml.FullLoader):

                persona = cattrs.structure(persona_data, Persona)

                persona.age = self.student_age

                agent = SimAgent(persona.id(), self.collection, self.langchain_chroma, self.class_year)
                agent.persona = persona

                self.agents[persona.id()] = agent

                self.agents[persona.id()].characteristics_check()

        '''self.list_of_agent_names = [agent.persona.name for agent in self.agents.values()]'''
        list_of_agent_guids = [agent.persona.guid for agent in self.agents.values()]

        self.agent_emoticons = [None] * len(list_of_agent_guids)

        self.general_agent_data = {}

    async def tick(self, user_input: str, user_input_time: float, chat_analysis_resp: object, question_suitability_resp: object):

        tick_start_time = round(time.time(), 3)

        process_agents_resp = await self.process_agents(user_input,
                                                        chat_analysis_resp,
                                                        question_suitability_resp)

        process_agents_end = round(time.time(), 3)

        print('Process Agents Time: ', round(process_agents_end-tick_start_time, 3))

        if not process_agents_resp['valid']:
            return process_agents_resp

        new_text = process_agents_resp['response']

        print('Successfully processed All Agents')

        self.agent_emoticons = []

        for agent in self.agents.values():
            self.agent_emoticons.append(agent.curr_emoticon)

        """ --------------------------- Append to General Chat Histories --------------------------- """

        self.general_chat_history[self.curr_tick] = []

        self.general_chat_history[self.curr_tick].append(ChatLog(person_type='user',
                                                                 guid='teacher',
                                                                 text=f'Teacher: {user_input}',
                                                                 tick=self.curr_tick,
                                                                 timestamp=user_input_time,
                                                                 agent_emoticons=self.agent_emoticons,
                                                                 chat_analysis_resp=chat_analysis_resp,
                                                                 question_suitability_resp=question_suitability_resp))

        for i in new_text:
            self.general_chat_history[self.curr_tick].append(ChatLog(person_type='agent',
                                                                     guid=i['agent_guid'],
                                                                     text=i['text'],
                                                                     tick=self.curr_tick,
                                                                     timestamp=process_agents_end))
        """ --------------------------- Append to General Chat Histories --------------------------- """

        """ --------- Add memories of responses to each student which isn't distracted. --------- """
        for agent in self.agents.values():
            if agent.curr_action != agent.distracted:
                for i in new_text:
                    if i['agent_guid'] != agent.guid:
                        agent.memories.append(i['text'])
        """ --------- Add memories of responses to each student which isn't distracted. --------- """

        tick_finish_time = round(time.time(), 3)

        self.general_agent_data[self.curr_tick] = {}

        for i in self.agents.values():
            i.curr_tick_data.tick = self.curr_tick

            i.curr_tick_data.tick_finish_timestamp = tick_finish_time

            self.general_agent_data[self.curr_tick][i.guid] = i.curr_tick_data.to_obj()

        self.curr_tick += 1

        return {'valid': True, 'response': new_text}

    async def process_agents(self, user_input, chat_analysis_resp, question_suitability_resp):
        tasks = []
        for agent in self.agents.values():
            task = asyncio.create_task(self.process_agent(agent, user_input, chat_analysis_resp, question_suitability_resp))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        print(results)

        fin_results = []

        for result in results:
            if result != None:
                if not result['valid']:
                    return result
                else:
                    fin_results.append(result['response'])

        return {'valid': True, 'response': fin_results}

    async def process_agent(self, agent, user_input, chat_analysis_resp, question_suitability_resp):
        returned_data = await agent.choose_action(user_input, self.teacher_gender, chat_analysis_resp, question_suitability_resp)

        if not returned_data['valid']:
            return returned_data

        print(agent.curr_action)

        agent_resp = await agent.curr_action

        if not agent_resp['valid']:
            return agent_resp

        agent_text = agent_resp['response']

        if agent_text is not None:
            return agent_resp

    async def save_data(self, folder_name):
        folder_path = f'./logger/{folder_name}'

        print(folder_path)

        check_path_or_create(folder_path)

        """ ------------------------- Save ChromaDB Data ------------------------- """
        collection_data = self.collection.get()


        dump_to_pickle(f'{folder_path}/chromadb_data.pickle', collection_data)
        """ ------------------------- Save ChromaDB Data ------------------------- """

        """ ------------------------- Save Agent Data ------------------------- """
        print('AGENT FINAL DATA VARIABLES:')

        student_final_data = {}

        for key, value in self.agents.items():

            student_final_data[key] = value.to_obj_for_saving()

            student_final_data[key]['persona'] = student_final_data[key]['persona'].to_obj()

        dump_to_pickle(f'{folder_path}/student_final_data.pickle', student_final_data)

        dump_to_pickle(f'{folder_path}/student_past_data.pickle', self.general_agent_data)
        """ ------------------------- Save Agent Data ------------------------- """

        """ ------------------------- Save Chat History Data ------------------------- """
        converted_chat_history = {}

        for key, chat_log_list in self.general_chat_history.items():
            # Convert each ChatLog object in the list using its to_obj() method
            converted_chat_history[key] = [chat_log_obj.to_obj() for chat_log_obj in chat_log_list]

        dump_to_pickle(f'{folder_path}/general_chat_history.pickle', converted_chat_history)
        """ ------------------------- Save Chat History Data ------------------------- """

    def primary_year_check(self, primary_year):
        if primary_year == "Year 5":
            return 10
        elif primary_year == "Year 6":
            return 11