from class_simulation import Simulation
from common import init_chromadb_connections, check_path_or_create, dump_to_pickle
import random


class SessionData:
    teacher_id: str
    teacher_gender: str
    ip_address: str
    difficulty: str
    login_time: float
    logout_time: float
    in_menu: bool
    in_lesson: bool
    finished_lesson: bool
    finished_review: bool
    current_student_value: int
    current_student_talking_to: str
    current_action_chosen: str
    collection: object
    langchain_chroma: object
    chromadb_client: object
    simulation: Simulation

    def __init__(self, teacher_id, gender, student_year, ip_address, login_time):
        self.teacher_id = teacher_id
        self.teacher_gender = gender
        self.student_year = student_year
        self.ip_address = ip_address
        self.difficulty = ''
        self.login_time = login_time
        self.logout_time = -1.0
        self.collection_name = f'{teacher_id}'
        self.in_menu = True
        self.in_lesson = False
        self.finished_lesson = False
        self.currently_being_reviewed = False
        self.finished_review = False
        self.current_student_value = -1
        self.current_student_talking_to = ''
        self.current_action_chosen = ''

        self.init_chromadb_collection()

        self.init_simulation()

    """ Initialise ChromaDB Collection using init_chromadb_connections in common.py """
    def init_chromadb_collection(self):
        # Go through process of initialising ChromaDB Connection
        collection, langchain_chroma, chromadb_client = init_chromadb_connections(path="chromadb/",
                                                                                  collection_name=self.collection_name,
                                                                                  model_name="text-embedding-ada-002")

        # Save Session Data
        self.collection = collection
        self.langchain_chroma = langchain_chroma
        self.chromadb_client = chromadb_client

    """ Initialise Simulation Object """
    def init_simulation(self):
        # Select Difficulty of Simulation
        self.difficulty = random.choice(['easy', 'medium', 'hard'])

        # Initialise Simulation
        self.simulation = Simulation(self.collection, self.langchain_chroma, self.teacher_gender, self.student_year)

        # Load Simulation Data given Difficulty
        self.simulation.load(self.difficulty)

    """ Delete ChromaDB Collection of Collection Name found in Session """
    def delete_collection(self):
        self.chromadb_client.delete_collection(name=self.collection_name)

    """ Save Session Data to File """
    def save_session_to_file(self, folder_name):
        # Define Path to save Session in
        folder_path = f'./logger/{folder_name}'

        # Convert to Object and save it to file
        dump_to_pickle(f'{folder_path}/session_details.pickle', self.to_obj_for_saving())

    """ Print Session Data in Format for Debugging """
    def print_data(self):
        print(f'Session Data:\n'
              f'Teacher ID: "{self.teacher_id}"\n'
              f'Teacher Gender: "{self.teacher_gender}"\n'
              f'Student Year: "{self.student_year}"\n'
              f'IP Address: "{self.ip_address}"\n'
              f'Difficulty: "{self.difficulty}"\n'
              f'Login Time: "{self.login_time}"\n'
              f'Collection Name: "{self.collection_name}"\n'
              f'In Menu: "{self.in_menu}"\n'
              f'In Lesson: "{self.in_lesson}"\n'
              f'Finished Lesson: "{self.finished_lesson}"\n'
              f'Finished Review: "{self.finished_review}"\n'
              f'Currently Being Reviewed: "{self.currently_being_reviewed}"\n'
              f'Current Student Value: "{self.current_student_value}"\n'
              f'Current Student Talking To: "{self.current_student_talking_to}"\n'
              f'Current Action Chosen: "{self.current_action_chosen}"\n'
              f'Simulation: "{self.simulation}"\n')

    """ Convert Session Data Object to Dictionary for Saving (only converts and returns data which needs to be saved)"""
    def to_obj_for_saving(self):
        return {
            'teacher_id': self.teacher_id,
            'teacher_gender': self.teacher_gender,
            'student_year': self.student_year,
            'difficulty': self.difficulty,
            'login_time': self.login_time,
            'logout_time': self.logout_time,
            'in_menu': self.in_menu,
            'in_lesson': self.in_lesson,
            'finished_lesson': self.finished_lesson,
            'finished_review': self.finished_review,
            'currently_being_reviewed': self.currently_being_reviewed,
            'current_student_value': self.current_student_value,
            'current_student_talking_to': self.current_student_talking_to,
            'current_action_chosen': self.current_action_chosen
        }
