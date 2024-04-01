import random
from typing import List, Optional

from agent_tick_data import TickData
from emotion import EmotionData
from persona import Persona
from common import *


class SimAgent:

    def __init__(self, guid: str, collection, langchain_chroma, class_year):
        self.collection = collection
        self.langchain_chroma = langchain_chroma
        self.guid = guid
        self.persona: Optional[Persona] = None
        self.curr_action = None
        self.emotion_active: str = ''
        self.memories: List[str] = []
        self.action_history: List[str] = []
        self.num_of_definitions = 0
        self.num_of_examples = 0
        self.num_of_correct_maths_responses = 0
        self.teacher_math_statement = 0
        self.curr_emoticon = None
        self.class_year = class_year

        self.curr_tick_data = TickData(guid)

    """ Convert Student Agent to Dictionary """
    def to_obj(self):
        return {
            'guid': self.guid,
            'persona': self.persona,
            'num_of_definitions': self.num_of_definitions,
            'num_of_examples': self.num_of_examples,
            'num_of_correct_maths_responses': self.num_of_correct_maths_responses,
            'teacher_math_statement': self.teacher_math_statement,
            'memories': self.memories,
            'action_history': self.action_history
        }

    """ Convert Student Agent to Dictionary for Saving, saves only necessary variables """
    def to_obj_for_saving(self):
        return {
            'guid': self.guid,
            'persona': self.persona,
            'num_of_definitions': self.num_of_definitions,
            'num_of_examples': self.num_of_examples,
            'num_of_correct_maths_responses': self.num_of_correct_maths_responses,
            'teacher_math_statement': self.teacher_math_statement
        }

    """ Goes through process of Adjusting Emotions, Building Prompt for Action Taker and Choosing Action """
    async def choose_action(self, user_input, teacher_gender, chat_analysis_resp, question_suitability_resp):

        self.curr_emoticon = None

        # Save Original Emotions in Current Tick Data
        self.curr_tick_data.emotions_original = EmotionData(self.persona.enjoyment,
                                                            self.persona.boredom,
                                                            self.persona.anger,
                                                            self.persona.anxiety)

        """ ---------------------------------------- Emotion Adjustment ---------------------------------------- """
        if (chat_analysis_resp['talking_to'] == 'Whole Class' and self.emotion_active != 'bored') or \
                chat_analysis_resp['talking_to'] == self.persona.name:

            # Check Interaction Style
            interaction_style_resp = self.interaction_style_check(chat_analysis_resp['interaction_style'])

            # Adjust Emotions based on the below Variables
            adjusted_emotions = await self.adjust_emotions(teacher_talking_to_current_student=True,
                                                           user_input=user_input,
                                                           speech_action=chat_analysis_resp['speech_action'],
                                                           tone=chat_analysis_resp['tone'],
                                                           talking_to_name=chat_analysis_resp['talking_to'],
                                                           teacher_interaction_style=interaction_style_resp,
                                                           student_characteristics=self.characteristics_resp)
        else:
            # Adjust Emotions based on Action History and Characteristics
            adjusted_emotions = await self.adjust_emotions(teacher_talking_to_current_student=False,
                                                           student_characteristics=self.characteristics_resp,
                                                           action_history=self.memories[-5:])

        # If non-valid response generated, show to User
        if not adjusted_emotions['valid']:
            return adjusted_emotions

        # Set the newly active emotion
        self.set_active_agent_emotion()
        """ ---------------------------------------- Emotion Adjustment ---------------------------------------- """

        """ ---------------------------------------- Prompt Builder ---------------------------------------- """
        action_taker_user_input = f'Teacher: {user_input}'

        # Initialise Default Text for Prompts
        relevant_information = ''
        direct_address_text = f"If the teacher is asking a question to {self.persona.name}, respond with {{\"action\": \"respond to teacher\"}}.\n"
        general_instruction_text = f"For general statements not specific to {self.persona.name}, use {{\"action\": \"listen to teacher\"}}.\n"
        maths_concepts_or_examples_text = f"Select {{\"action\": \"take notes\"}} only if the teacher presents a full-sentence mathematical concept or explanation that is directly relevant to the lesson's content."

        compare_vector_documents_resp = {'able_to_respond': False}

        # IF Student is Bored and teacher is not talking to Student, make Model choose "Distracted"
        if self.emotion_active == 'bored' and chat_analysis_resp['talking_to'] != self.persona.name:
            response_format = 'Respond with {"action": "distracted"}"'
        else:
            # If teacher is talking to another student then don't respond
            if (chat_analysis_resp['talking_to'] != self.persona.name and
                    chat_analysis_resp['talking_to'] != 'Whole Class'):
                direct_address_text = ''
            elif chat_analysis_resp['talking_to'] == 'Whole Class':
                # If teacher is talking to whole class, then respond if asking question to whole class
                direct_address_text = f"If the teacher is asking a question to the whole class, respond with {{\"action\": \"respond to teacher\"}}.\n"

            # If not a question, then don't respond
            if not question_suitability_resp['is_question'] and chat_analysis_resp['talking_to'] == self.persona.name:
                direct_address_text = 'If the teacher is talking to you directly and there is a need to respond, respond with {{\"action\": \"respond to teacher\"}}.\n'

            # If can answer, then respond correctly
            if question_suitability_resp['can_answer']:
                # If about Maths, then get compare vector documents result
                if question_suitability_resp['is_about_maths']:
                    # Get Documents of Student Agent most similar to User Input
                    documents = (self.langchain_chroma.similarity_search_with_score(user_input,
                                                                                    filter={"student": {
                                                                                            '$eq': self.persona.guid}},
                                                                                    k=10))

                    # Filter out Documents which hava similarity score of less than 0.3
                    curr_relevant_documents = [document for document in documents if document[1] < 0.3]

                    # If relevant documents exist, then add them to relevant_information variable
                    if len(curr_relevant_documents) > 0:
                        for document in curr_relevant_documents:
                            relevant_information = f'\n{document[0].page_content}'
                    # Else, place Empty in relevant_information
                    else:
                        relevant_information = 'Empty'

                    # If Relevant Information not Empty, then prompt model to see whether it can be used to solve the User Input
                    if relevant_information != 'Empty':
                        time_start_model = round(time.time(), 3)

                        compare_vector_documents_resp = await run_prompt_and_convert_to_obj(
                                'compare_vector_documents.yaml',
                                print_prompt=True,
                                max_tokens_limit=20,
                                user_input=user_input,
                                relevant_information=relevant_information)

                        # If non-valid response generated, show to User
                        if not compare_vector_documents_resp['valid']:
                            return compare_vector_documents_resp

                        compare_vector_documents_resp = compare_vector_documents_resp['response']

                        print("Compare Vector Documents Model: ", round(float(time.time()) - time_start_model, 3))
                    else:
                        compare_vector_documents_resp = {'able_to_respond': False}
                elif not question_suitability_resp['is_about_maths']:
                    maths_concepts_or_examples_text = ''

            # Allow Actions to be taken by Model based on the Student Agent's Currently Active Emotion
            if self.emotion_active == 'enjoyable':
                print('Enjoyment Prompt Used')
                response_format = f'{direct_address_text}{general_instruction_text}{maths_concepts_or_examples_text}'
            elif self.emotion_active == 'angry':
                print('Angry Prompt Used')
                response_format = f'{general_instruction_text}\n{direct_address_text}'
            elif self.emotion_active == 'anxious':
                print('Anxious Prompt Used')
                response_format = f'{general_instruction_text}'
            else:
                print('Neutral Prompt Used')
                response_format = f'{direct_address_text}{general_instruction_text}{maths_concepts_or_examples_text}'

        chosen_memories = self.memories

        # Get 10 most recent memories
        if len(self.memories) > 10:
            chosen_memories = self.memories[-10]

        people_identified = chat_analysis_resp['talking_to']

        time_start_model = round(time.time(), 3)
        """ ---------------------------------------- Prompt Builder ---------------------------------------- """

        """ ---------------------------------------- Action Chooser ---------------------------------------- """
        # Prompt model to choose action from available set of actions for the Student Agent
        action_taker_resp = await run_prompt_and_convert_to_obj('action_taker_prompt.yaml',
                                                                print_prompt=False,
                                                                name=self.persona.name,
                                                                academic_emotion=self.emotion_active,
                                                                tone=chat_analysis_resp['tone'],
                                                                teacher_talking_to=people_identified,
                                                                speech_action=chat_analysis_resp['speech_action'],
                                                                chat_memory=chosen_memories,
                                                                user_input=action_taker_user_input,
                                                                response_format=response_format)

        print("Action Taker Model: ", round(float(time.time()) - time_start_model, 3))

        # If non-valid response generated, show to User
        if not action_taker_resp['valid']:
            return action_taker_resp

        action_taker_resp = action_taker_resp['response']

        # Append Action to Action History
        self.action_history.append(action_taker_resp["action"])

        # Remove Oldest Action if Greater than 10
        if len(self.action_history) > 10:
            self.action_history.pop(0)  # Remove the first element

        """ ---------------------------------------- Action Chooser ---------------------------------------- """

        print(self.persona.name)

        print(f'ACTION TAKER RESP: {action_taker_resp["action"]}')

        # Check Action Chosen by Model and set to Student's Current Action
        self.action_chosen_check(user_input, teacher_gender, action_taker_resp["action"], question_suitability_resp,
                                 compare_vector_documents_resp)

        return {"valid": True, "response": None}

    """ Listen to Teacher Action, Input is saved to memory but no response is generated"""
    async def listen_to_teacher(self, user_input, question_suitability_resp, compare_vector_documents_resp):
        # Append User Input to Memory
        self.memories.append(f'Teacher: {user_input}')

        self.curr_tick_data.student_response = None
        self.curr_tick_data.action_specific_data = None

        # If Input was about Maths and Student is probably able to answer, then add this input into the Vector Store
        if question_suitability_resp['is_about_maths'] and question_suitability_resp['can_answer']:
            self.teacher_math_statement += 1

            # Create vector id
            vector_id = f'{self.persona.guid}_teacher_math_statement_{self.num_of_examples}'

            # Add Input to Collection
            self.collection.add(ids=[vector_id],
                                documents=[f'Teacher: {user_input}'],
                                metadatas=[{'note_type': 'teacher_math_statement', 'student': self.persona.guid}])

        return {'valid': True, 'response': None}

    """ Respond to Teacher Action, Input is saved to memory and a response is generated"""
    async def respond_to_teacher(self, user_input, teacher_gender, question_suitability_resp,
                                 compare_vector_documents_resp):

        # Append User Input to Memory
        self.memories.append(f'Teacher: {user_input}')

        new_details = ''

        # This Fine-tuning takes a look at the analysis made in the initial models before processing each agent,
        # and adds new information in the prompt to get a better response
        """ --------------- Fine-tuning of Student Prompt --------------- """
        if question_suitability_resp['is_question']:
            if question_suitability_resp['is_about_maths']:
                if question_suitability_resp['can_answer']:
                    if not compare_vector_documents_resp['able_to_respond']:
                        new_details = 'You are being asked a question by the teacher. You do not know the response to the question, respond incorrectly.'
                    else:
                        new_details = 'You are being asked a question by the teacher. You know the response to the question, respond correctly.'
                else:
                     new_details = 'You are being asked a question by the teacher. You do not know the response to the question, respond incorrectly.'
            else:
                if question_suitability_resp['can_answer']:
                    new_details = 'You are being asked a question by the teacher. You know the response to the question.'
                else:
                    new_details = 'You are being asked a question by the teacher. You do not know the response to the question.'
        elif not question_suitability_resp['is_question']:
            if question_suitability_resp['can_answer']:
                new_details = 'The Teacher is Talking to you. Respond Normally.'

                if question_suitability_resp['is_about_maths']:
                    if not compare_vector_documents_resp['able_to_respond']:
                        new_details = "The Teacher is Talking to you about something which you don't know."

            else:
                new_details = "The Teacher is Talking to you about something which you don't know."
        """ --------------- Fine-tuning of Student Prompt --------------- """

        time_start_model = round(time.time(), 3)

        # Get 10 most recent memories
        if len(self.memories) > 10:
            chat_history = self.memories[-10:]
        else:
            chat_history = self.memories

        # Generate a Response from the Student
        student_resp = await load_and_run_prompt('student_prompt.yaml',
                                                 print_prompt=True,
                                                 name=self.persona.name,
                                                 age=self.persona.age,
                                                 gender=self.persona.gender,
                                                 active_emotion=self.emotion_active,
                                                 teacher_gender=teacher_gender,
                                                 user_input=user_input,
                                                 chat_history=chat_history,
                                                 new_details=new_details,
                                                 class_year=self.class_year)

        # If non-valid response generated, show to User
        if not student_resp['valid']:
            return student_resp

        student_resp = student_resp['response']

        print("Student Resp Model: ", round(float(time.time()) - time_start_model, 3))

        # If User Input is about maths and the Student Agent has the knowledge to respond, save it to Vector Store
        if question_suitability_resp['is_about_maths'] and compare_vector_documents_resp['able_to_respond']:
            self.num_of_correct_maths_responses += 1

            vector_id = f'{self.persona.guid}_correct_math_response_{self.num_of_examples}'

            # Save Generated Response to Vector Store
            self.collection.add(ids=[vector_id],
                                documents=[student_resp],
                                metadatas=[{'note_type': 'correct_math_response', 'student': self.persona.guid}])

        # Append Generated Response to Memories
        self.memories.append(student_resp)

        self.curr_tick_data.student_response = student_resp
        self.curr_tick_data.action_specific_data = {
            "question_suitability_resp": question_suitability_resp,
            "compare_vector_documents_resp": (
                compare_vector_documents_resp if compare_vector_documents_resp != '' else None)
        }

        # Return Generated Response to be shown to User
        return {'valid': True, 'response': {'text': student_resp, 'agent_guid': self.guid}}

    """ Take Notes Action, Student Saves the Teacher's Input to the Vector Database and doesn't generate a Response """
    async def take_notes(self, user_input):
        # Append User input to Memory
        self.memories.append(f'Teacher: {user_input}')

        time_start_model = round(time.time(), 3)

        # Prompt Model to "Summarize the User's Input into an Example or Definition
        learning_resp = await run_prompt_and_convert_to_obj('learning_prompt.yaml',
                                                            print_prompt=True,
                                                            user_input=user_input)

        print("Learning Model: ", round(float(time.time()) - time_start_model, 3))

        # If not valid response generated, show to User
        if not learning_resp['valid']:
            return learning_resp

        learning_resp = learning_resp['response']

        # If an example, then increment num_of_examples, else increment num_of_definitions
        if learning_resp["explanation"] == 'example':
            self.num_of_examples += 1
            vector_id = f'{self.persona.guid}_example_{self.num_of_examples}'
        else:
            self.num_of_definitions += 1
            vector_id = f'{self.persona.guid}_definition_{self.num_of_definitions}'

        # Save explanation to Vector Store
        self.collection.add(ids=[vector_id],
                            documents=[learning_resp["explanation"]],
                            metadatas=[{'note_type': learning_resp["explanation_type"], 'student': self.persona.guid}])

        self.curr_tick_data.student_response = None
        self.curr_tick_data.action_specific_data = {
            "learning_resp": learning_resp,
        }

        return {'valid': True, 'response': None}

    """ Distracted Action, Nothing happens due to Student being Distracted """
    async def distracted(self):

        self.curr_tick_data.student_response = None
        self.curr_tick_data.action_specific_data = None

        return {'valid': True, 'response': None}

    """ Sets Current Active Emotion for Student Agent """
    def set_active_agent_emotion(self):
        emotions = {
            'angry': self.persona.anger,
            'anxious': self.persona.anxiety,
            'bored': self.persona.boredom,
            'enjoyable': self.persona.enjoyment
        }

        # Filter emotions that are greater than 4
        active_emotions = {emotion: level for emotion, level in emotions.items() if level > 4}

        if not active_emotions:
            # If no emotions are above 5, set to neutral
            self.emotion_active = 'neutral'
        else:
            # Find the highest emotion level
            max_level = max(active_emotions.values())

            # Get all emotions with the highest level
            max_emotions = [emotion for emotion, level in active_emotions.items() if level == max_level]

            # Randomly select one emotion if there are multiple with the same max level
            self.emotion_active = random.choice(max_emotions)

    """ Adjust Student Emotions based on a number of variables"""
    async def adjust_emotions(self, teacher_talking_to_current_student, **kwargs):

        if teacher_talking_to_current_student:

            time_start_model = round(time.time(), 3)

            # Prompt Model given Emotions and above variables
            academic_emotion_changer = await run_prompt_and_convert_to_obj(
                'academic_emotion_changer_before_action.yaml',
                print_prompt=False,
                boredom=self.persona.boredom,
                enjoyment=self.persona.enjoyment,
                anger=self.persona.anger,
                anxiety=self.persona.anxiety,
                **kwargs)

            print("Academic Emotion Before Action Model: ", round(float(time.time()) - time_start_model, 3))
        else:

            time_start_model = round(time.time(), 3)

            # Prompt Model given Emotions and above variables
            academic_emotion_changer = await run_prompt_and_convert_to_obj('academic_emotion_changer_after_action.yaml',
                                                                           print_prompt=False,
                                                                           boredom=self.persona.boredom,
                                                                           enjoyment=self.persona.enjoyment,
                                                                           anger=self.persona.anger,
                                                                           anxiety=self.persona.anxiety,
                                                                           **kwargs)

            print("Academic Emotion Before Action Model: ", round(float(time.time()) - time_start_model, 3))

        # If non-valid response generated, show to User
        if not academic_emotion_changer['valid']:
            return academic_emotion_changer

        academic_emotion_changer = academic_emotion_changer['response']

        # Set Updated Emotions in Current Tick Data
        self.curr_tick_data.emotions_updated = EmotionData(academic_emotion_changer['enjoyment'],
                                                           academic_emotion_changer['boredom'],
                                                           academic_emotion_changer['anger'],
                                                           academic_emotion_changer['anxiety'])

        # Set Updated Emotions in Student agent Persona
        self.persona.boredom = academic_emotion_changer['boredom']
        self.persona.enjoyment = academic_emotion_changer['enjoyment']
        self.persona.anger = academic_emotion_changer['anger']
        self.persona.anxiety = academic_emotion_changer['anxiety']

        return {'valid': True, 'response': None}

    """ Actives Action Chosen and assigned Emoticon based on Action Chosen"""
    def action_chosen_check(self, user_input, teacher_gender, action_taken, question_suitability_resp,
                            compare_vector_documents_resp):
        if action_taken == 'listen to teacher':
            self.curr_action = self.listen_to_teacher(user_input, question_suitability_resp, compare_vector_documents_resp)
            self.curr_emoticon = None
        elif action_taken == 'respond to teacher':
            self.curr_action = self.respond_to_teacher(user_input, teacher_gender, question_suitability_resp,
                                                       compare_vector_documents_resp)
            self.curr_emoticon = 'respond_to_teacher'
        elif action_taken == 'take notes':
            self.curr_action = self.take_notes(user_input)
            self.curr_emoticon = 'taking_notes'
        elif action_taken == 'distracted':
            self.curr_action = self.distracted()
            self.curr_emoticon = 'distracted'

        self.curr_tick_data.action_chosen = action_taken

    """ Checks Interaction Style for Prompting """
    def interaction_style_check(self, interaction_text):
        if interaction_text == 'encouraging_and_supportive':
            return 'Teacher is being encouraging and supportive, increase enjoyment and decrease anxiety'
        elif interaction_text == 'engaging_and_interactive':
            return 'Teacher is being engaging and interactive, increase enjoyment and decrease boredom'
        elif interaction_text == 'empathetic_and_understanding':
            return 'Teacher is being empathetic and understanding, decrease anxiety and decrease anger'
        elif interaction_text == 'critical_or_negative':
            return 'Teacher is being critical or negative, increase anxiety and anger'
        elif interaction_text == 'monotonous_or_irrelevant':
            return 'Teacher is being monotonous or irrelevant, increase boredom'
        elif interaction_text == 'lack_of_support_or_acknowledgment':
            return 'Teacher is lacking support or acknowledgment, increase boredom and decrease in enjoyment'
        else:
            return 'Empty'

    """ Checks Characteristics of Student Agent for Prompting """
    def characteristics_check(self):
        if self.persona.creative > 4:
            fin_creative_prompt = "Very Creative: Greatly Increase Enjoyment and Boredom based on teaching Novelty and Creativity\n"
        elif self.persona.creative > 2:
            fin_creative_prompt = 'Creative: Increase in Enjoyment and Boredom based on teaching Novelty and Creativity\n'
        else:
            fin_creative_prompt = ''

        if self.persona.curious > 4:
            fin_curios_prompt = 'Very Curios: Great Rapid Increase or Decrease in Enjoyment based on Content Engagement and Challenge\n'
        elif self.persona.curious > 2:
            fin_curios_prompt = 'Curios: Rapid Increase or Decrease in Enjoyment based on Content Engagement and Challenge\n'
        else:
            fin_curios_prompt = ''

        if self.persona.tolerant > 4:
            fin_tolerance_prompt = 'Very Tolerant: Rarely Prone to Anger, Need for Strong Stimuli for Emotional Change\n'
        elif self.persona.tolerant > 2:
            fin_tolerance_prompt = 'Tolerant: Less Prone to Anger, Need for Stimuli for Emotional Change\n'
        else:
            fin_tolerance_prompt = ''

        if self.persona.persistent > 4:
            fin_persistence_prompt = 'Very Persistence: Very slow, Steady Emotion Changes, very resilient to short-term setbacks\n'
        elif self.persona.persistent > 2:
            fin_persistence_prompt = 'Persistence: Steady Emotion Changes, Resilience to Short-term Setbacks\n'
        else:
            fin_persistence_prompt = ''

        if self.persona.responsible > 4:
            fin_responsible_prompt = 'Very Responsible: Very slow, Steady Emotion Changes, very resilient to short-term setbacks\n'
        elif self.persona.responsible > 2:
            fin_responsible_prompt = 'Responsibility: Stability in Emotional State, Buffer Against Negative Emotions\n'
        else:
            fin_responsible_prompt = ''

        if self.persona.self_control > 4:
            fin_self_control_prompt = 'Very Self-Controlled: Very Stable in Emotional State, Great Buffer Against Negative Emotions\n'
        elif self.persona.self_control > 2:
            fin_self_control_prompt = 'Self-Control: Stability in Emotional State, Buffer Against Negative Emotions\n'
        else:
            fin_self_control_prompt = ''

        self.characteristics_resp = f'{fin_creative_prompt}{fin_curios_prompt}{fin_tolerance_prompt}{fin_persistence_prompt}{fin_responsible_prompt}{fin_self_control_prompt}'
