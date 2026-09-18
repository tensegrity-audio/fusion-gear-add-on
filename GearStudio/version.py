"""Release metadata importable under both Fusion and standard Python loaders.

Fusion loads GearStudio.py as a generated package without executing __init__.py.
Runtime modules must import this module explicitly, not attributes on the root.
"""

__version__ = "0.3.2"
