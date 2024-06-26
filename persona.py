from attr import define


@define(slots=True)
class Persona():
    guid: str
    name: str
    age: str
    gender: str
    enjoyment: float
    anger: float
    anxiety: float
    boredom: float
    creative: int
    curious: int
    tolerant: int
    persistent: int
    responsible: int
    self_control: int

    """ Converts Persona Object to Dictionary"""
    def to_obj(self):
        return {
            'guid': self.guid,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'enjoyment': self.enjoyment,
            'anger': self.anger,
            'anxiety': self.anxiety,
            'boredom': self.boredom,
            'creative': self.creative,
            'curious': self.curious,
            'tolerant': self.tolerant,
            'persistent': self.persistent,
            'responsible': self.responsible,
            'self_control': self.self_control
        }
