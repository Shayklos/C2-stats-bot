import discord
from discord import app_commands
from discord.ext import commands
import sys
import os
import subprocess
sys.path.append(f'..{os.sep}c2-stats-bot')
import database, methods

class Botzilla(commands.Cog):
    run_message = r"""Botzilla is being summoned!

**Bot command list** (You use these *ingame*)
/bot help | displays this message
/bot follow me | join the room of the person who wrote this
/bot follow <player> | join the room <player> is in
/bot join <room> | join the room with name <room>
/bot status | display current bpm/combo targets (only works in a room chat)
/bot leave | leave a room (can be called by all registered users)"""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    def run():
        if os.name == 'nt': # Windows
            os.chdir('.\c2-patch_ai')
            subprocess.call('.\Windows-64-Start-cultris2.bat')
            os.chdir('..\\')
        else: #os.name == 'posix' (Linux)
            os.chdir('.' + os.sep + 'c2-patch_ai')
            # subprocess.call('.' + os.sep + 'Linux-32-Start-cultris2.sh')
            subprocess.call(['sh', '.' + os.sep + 'Linux-32-Start-cultris2.sh'])
            os.chdir('..' + os.sep)

    def is_process_running(process_name):
        def _is_process_running_windows(process_name):
            try:
                # Run tasklist command to get all running processes
                output = subprocess.check_output('tasklist', shell=True).decode()
                # Check if process name appears in the output
                return process_name in output
            except subprocess.CalledProcessError:
                return False
            
        def _is_process_running_linux(process_name):
            try:
                # Use pgrep to check if process is running
                subprocess.check_output(['pgrep', '-f', process_name])
                return True
            except subprocess.CalledProcessError:
                return False

        return _is_process_running_windows(process_name) if os.name == 'nt' else _is_process_running_linux(process_name)

    @app_commands.command(description="Summons a bot to Cultris II you can play with.")
    async def botzilla(self, interaction: discord.Interaction):
        correct = await methods.checks(interaction)
        if not correct:
            return
        
        # There are potentially three ways of checking botzilla is already on. 
        #
        # 1) You could check if an account named 'botzilla' is on. This is a great approach, however it depends on
        #    the good faith of the community. If someone logs in as 'botzilla', or creates an account named like 
        #    this, this approach will stop working.
        # 2) You could check if there's a java process running. Of course, this assumes that the environment doesn't
        #    have any other java processes. Relatively safe if the environment is well isolated. 
        # 3) Finally, you could check for a window titled 'Cultris II'. This is arguably the best way to check whether
        #    or not botzilla is already on. However, it requires dependencies to non-builtin libraries.  

        # Check if botzilla is online
        liveinfo: dict = await database.getLiveinfoData()
        for player in liveinfo.get('players'):
            if player.get('name') == 'botzilla':
                await interaction.response.send_message("Botzilla is already running.", ephemeral=True)
                return 
            
        # Check if there exists a java process (Cultris II).
        if Botzilla.is_process_running('java'):
            await interaction.response.send_message("Botzilla is already running.", ephemeral=True)
            return 

        Botzilla.run()
        await interaction.response.send_message(Botzilla.run_message, ephemeral=True)


        
            

                

async def setup(bot: commands.Bot):
    await bot.add_cog(Botzilla(bot))
    print("Loaded /botzilla command.")