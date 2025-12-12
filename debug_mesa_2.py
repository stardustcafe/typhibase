import mesa.model
import mesa.agent
import inspect

print("Inspecting mesa.model...")
print([m[0] for m in inspect.getmembers(mesa.model)])

print("\nInspecting mesa.agent...")
print([m[0] for m in inspect.getmembers(mesa.agent)])
