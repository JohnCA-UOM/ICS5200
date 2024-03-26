class EmotionData:
    enjoyment: float
    boredom: float
    anger: float
    anxiety: float

    def __init__(self, enjoyment, boredom, anger, anxiety):
        self.enjoyment = enjoyment
        self.boredom = boredom
        self.anger = anger
        self.anxiety = anxiety

    def print_emotions(self):
        print(
            f'Emotions: Enjoyment: {self.enjoyment}, Boredom: {self.boredom}, Anger: {self.anger}, Anxiety: {self.anxiety}')

    def to_obj(self):
        return {
            'enjoyment': self.enjoyment,
            'boredom': self.boredom,
            'anger': self.anger,
            'anxiety': self.anxiety
        }