from typing import Optional

from emotion import EmotionData


class TickData:
    emotions_original: Optional[EmotionData]
    emotions_updated: Optional[EmotionData]
    action_chosen: str
    student_response: Optional[str]
    action_specific_data: Optional[dict]
    tick: int
    tick_finish_timestamp: float

    def __init__(self, guid):
        self.agent_guid = guid
        self.emotions_original = None
        self.emotions_updated = None
        self.action_chosen = ''
        self.student_response = None
        self.action_specific_data = {}
        self.tick = -1
        self.tick_finish_timestamp = 0.0

    """ Print Tick Data in Format for Debugging """
    def print_log(self):
        print(f'Tick Data:\n'
              f'Student GUID: {self.agent_guid}\n'
              f'Emotions Original: {self.emotions_original.to_obj()}\n'
              f'Emotions Updated: {self.emotions_updated.to_obj()}\n'
              f'Action Chosen: "{self.action_chosen}"\n'
              f'Student Response: "{self.student_response}"\n'
              f'Action Specific Data: {self.action_specific_data}\n'
              f'Tick: {self.tick}\n'
              f'Tick Finish Timestamp: {self.tick_finish_timestamp}')

    """ Convert Tick Data Object to Dictionary for Saving """
    def to_obj(self):
        return {'agent_guid': self.agent_guid,
                'emotions_original': self.emotions_original.to_obj(),
                'emotions_updated': self.emotions_updated.to_obj(),
                'action_chosen': self.action_chosen,
                'student_response': self.student_response,
                'action_specific_data': self.action_specific_data,
                'tick': self.tick,
                'tick_finish_timestamp': self.tick_finish_timestamp}