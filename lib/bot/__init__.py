from discord.ext.commands import Bot as BotBase
from glob import glob
from channels import OWNER_IDS

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..db import db 

PREFIX = "+"
COGS = [path.split("\\")[-1][:-3] for path in glob("./lib/cogs/*.py")]

class Bot(BotBase):
    def __init__(self):
        self.PREFIX = PREFIX
        self.ready = False
        self.guild = None
        self.scheduler = AsyncIOScheduler()

        db.autosave(self.scheduler)

        super().__init__(command_prefix=PREFIX, owner_ids=OWNER_IDS)
    
    def setup(self):
        for cog in COGS:
            self.load_extension(f"lib.cogs.{cog}")
            print(f"{cog} cog loaded")
        
        print ("setup complete")
    
    def run(self, version):
        self.VERSION = version

        print("running setup")
        self.setup()

        with open("./lib/bot/token.0", "r", encoding="utf-8") as tf:
            self.TOKEN = tf.read()
        
        print("running bot")
        super().run(self.TOKEN, reconnect=True)

    async def on_connect(self):
        print("Connected")
    
    async def on_disconnect(self):
        print("Disconnected")

    async def on_ready(self):
        if not self.ready:
            self.ready = True

            self.scheduler.start()

            print("bot ready")
        else:
            print("bot reconnected")

    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)

bot = Bot()
