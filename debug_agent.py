import mesa
import inspect

print("Inspecting mesa.Agent.__init__...")
try:
    print(inspect.signature(mesa.Agent.__init__))
except Exception as e:
    print(e)

print("\nTrying to instantiate Agent...")
class MyAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

class MockModel:
    pass

try:
    model = MockModel()
    a = MyAgent(1, model)
    print("Success!")
except Exception as e:
    print("Failed:", e)
