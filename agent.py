class Agent:
    def __init__(self, agent_id, age_days=0):
        self.agent_id = agent_id
        self.age_days = age_days
        self.survived = True

    @property
    def age_years(self):
        return self.age_days // 365