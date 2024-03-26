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

    def to_array(self):
        return [
            f"GUID: {self.guid}",
            f"Name: {self.name}",
            f"Age: {self.age}",
            f"Gender: {self.gender}",
            f"Enjoyment: {self.enjoyment}",
            f"Anger: {self.anger}",
            f"Anxiety: {self.anxiety}",
            f"Boredom: {self.boredom}",
            f"Creative: {self.creative}",
            f"Curious: {self.curious}",
            f"Tolerant: {self.tolerant}",
            f"Persistent: {self.persistent}",
            f"Responsible: {self.responsible}",
            f"Self-Control: {self.self_control}"
        ]

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


    def id(self) -> str:
        return self.guid
