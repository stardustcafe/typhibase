import mesa
import inspect

print("Searching for RandomActivation in mesa...")
for name, obj in inspect.getmembers(mesa):
    if "RandomActivation" in name:
        print(f"Found {name} in mesa")

# Check submodules
try:
    import mesa.time
    print("mesa.time exists")
except ImportError:
    print("mesa.time does not exist")

# Try to find where it is
# Maybe it's not imported by default
import pkgutil
print("Submodules:")
for importer, modname, ispkg in pkgutil.iter_modules(mesa.__path__):
    print(modname)
