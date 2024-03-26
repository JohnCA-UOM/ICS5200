from typing import Optional, Dict, List


class ChatLog():
    person_type: str
    guid: str
    text: str
    tick: int
    agent_emoticons: Optional[List]
    chat_analysis_resp: Optional[Dict]
    question_suitability_resp: Optional[Dict]
    timestamp: float

    def __init__(self, person_type, guid, text, tick, timestamp, agent_emoticons=None, chat_analysis_resp=None, question_suitability_resp=None):
        self.person_type = person_type
        self.guid = guid
        self.text = text
        self.tick = tick
        self.agent_emoticons = agent_emoticons
        self.chat_analysis_resp = chat_analysis_resp
        self.question_suitability_resp = question_suitability_resp
        self.timestamp = timestamp


    def print_log(self):
        if self.chat_analysis_resp is None:
            print(f'Chat Log Data: Person Type: "{self.person_type}", '
                  f'guid: "{self.guid}" '
                  f'Text: "{self.text}", '
                  f'Tick: {self.tick}, '
                  f'Timestamp: {self.timestamp}')
        else:
            print(f'Chat Log Data: Person Type: "{self.person_type}", '
                  f'guid: "{self.guid}" '
                  f'Text: "{self.text}", '
                  f'Tick: {self.tick}, '
                  f'Emoticons: {self.agent_emoticons}, '
                  f'Timestamp: {self.timestamp}'
                  f'Chat Analysis Resp: {self.chat_analysis_resp}, '
                  f'Question Suitability Resp: {self.question_suitability_resp}, ')

    def to_obj(self):
        if self.chat_analysis_resp is None:
            return {
                'person_type': self.person_type,
                'guid': self.guid,
                'text': self.text,
                'tick': self.tick,
                'timestamp': self.timestamp
            }
        else:
            return {
                'person_type': self.person_type,
                'guid': self.guid,
                'text': self.text,
                'tick': self.tick,
                'agent_emoticons': self.agent_emoticons,
                'timestamp': self.timestamp,
                'chat_analysis_resp': self.chat_analysis_resp,
                'question_suitability_resp': self.question_suitability_resp
            }