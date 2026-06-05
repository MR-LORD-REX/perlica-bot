# from cryptography.fernet import Fernet

# print(Fernet.generate_key().decode())

from endfield import Endfield
import asyncio

async def main():
    async with Endfield() as ef:
        data=await ef.get_factory_blueprints(
            region='Asia',
            item='ferrium-component',
            start=0,
            end=1
        )
        print(data.model_dump_json(indent=2))
asyncio.run(main())