import asyncio
# we cannot rely on normal imports when the script is executed directly
# (`python database/setup_logging_db.py`), because the `database` package may
# not be initialized.  Use importlib to load the module by path instead.
import importlib.util, os, sys

def _load_database_class():
    here = os.path.dirname(__file__)
    path = os.path.join(here, 'database.py')
    spec = importlib.util.spec_from_file_location('database.database', path)
    module = importlib.util.module_from_spec(spec)
    # create a package object so that relative imports see a parent package
    if 'database' not in sys.modules:
        pkg = importlib.util.module_from_spec(importlib.util.spec_from_loader('database', loader=None))
        pkg.__path__ = [os.path.dirname(path)]
        sys.modules['database'] = pkg
    module.__package__ = 'database'
    spec.loader.exec_module(module)
    return module.Database

Database = _load_database_class()


async def main():
    # we don't care about the stats database here, it can be in-memory.
    stats_path = ':memory:'
    log_path = 'files/log.db'
    db = await Database.connect(stats_path, log_path)
    print("Logging database initialized (" + log_path + ")")

    # optional: add a few sample functions/concepts so that the view can be
    # exercised immediately.
    await db.ensure_functions(["logInteraction"])
    await db.ensure_concepts(["User ~& used /~&"])
    print("Seeded example function and concept.")


if __name__ == '__main__':
    asyncio.run(main())
