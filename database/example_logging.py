"""
Example of using the new log_event method with Concept constants.

This demonstrates how to log events using predefined Concept constants
without manually writing templates or function names.
"""

import asyncio
from database.database import Database
from database.log_models import Concept, CategoryEnum


async def example_function():
    """Example function that demonstrates the new logging approach."""
    
    # Connect to the database
    db = await Database.connect('files/cultris2.db', 'files/log.db')
    
    try:
        # Using predefined Concept constants with logging
        await db.log_event(
            'example_function',  # Function name
            Concept.UpdateUser,  # Use Concept constant (includes template and category)
            text_params=['John'],
            num_params=[123]
        )
        
        # Override category if needed (otherwise uses concept's default)
        await db.log_event(
            'another_function',
            Concept.AddRound,
            category=CategoryEnum.DISCORD,  # Override default category
            num_params=[456, 789]
        )
        
        # Still supports old string-based templates for backward compatibility
        await db.log_event(
            'legacy_function',
            'Custom template with ~& and number ~¡',  # Old way still works
            text_params=['parameter'],
            num_params=[999]
        )
        
        # Query the log_view to see the results
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        async_session = async_sessionmaker(db.log_engine, expire_on_commit=False)
        async with async_session() as sess:
            rows = await sess.execute(
                text('SELECT function_name, category, message FROM log_view ORDER BY id DESC LIMIT 3')
            )
            for row in rows.fetchall():
                print(f"Function: {row[0]}, Category: {row[1]}")
                print(f"Message: {row[2]}\n")
        
        # Available Concept constants:
        # - Concept.UpdateUser           (category: GENERAL)
        # - Concept.CreateUser           (category: GENERAL)
        # - Concept.AddRound             (category: GENERAL)
        # - Concept.ProcessRounds        (category: GENERAL)
        # - Concept.ProcessAllRounds     (category: GENERAL)
        
        # To create new concept constants, add them to ConceptDef class
        
    finally:
        await db.engine.dispose()
        await db.log_engine.dispose()


if __name__ == '__main__':
    asyncio.run(example_function())
