import os
import zarr
import json
import pprint
import asyncio
import numpy as np
from io import BytesIO
import zarr.core.buffer.cpu as buffer

# Set PYTHONTRACEMALLOC to help debug memory issues if needed
import tracemalloc

#os.environ["PYTHONTRACEMALLOC"] = "1"
#tracemalloc.start()


# Open the ZipStore in read-only mode
store = zarr.storage.TarStore( "exampleEmpty.tar", read_only=True )

z = zarr.open(store, mode='r')


# Open the ZipStore in read-only mode
store = zarr.storage.TarStore("exampleEmpty.tar", read_only=True)
print(f"Store type: {type(store)}")   
print(f"Path:{store.path}")
print(f"Read only: {store.read_only}")
print(f"Supports consolidated metadata: {store.supports_consolidated_metadata}")
print(f"Supports writes: {store.supports_writes}")
print(f"Supports deletes: {store.supports_deletes}")
print(f"Supports listing: {store.supports_listing}")
print(store.__repr__())
print(f"Listing: {store.list()} ")

async def listMembers(store):
    itemList = store.list()
    async for item in itemList:
        print(f"Item: {item} ")
asyncio.run( listMembers(store) )

async def checkExists(store, key):
    exists = await store.exists(key)
    return exists

print(f"Exists: { asyncio.run( checkExists(store, 'zarr.json') ) }" )



async def listMembersWithPrefix( store, prefix ):
    itemList = store.list_prefix( prefix )
    async for item in itemList:
        print(f"Prefix Item: {item} ")

asyncio.run( listMembersWithPrefix(store, 'zarr') )




async def listMembersWithDirectoryPrefix( store, prefix ):
    itemList = store.list_dir( prefix )
    async for item in itemList:
        print(f"Directory Item: {item} ")

asyncio.run( listMembersWithDirectoryPrefix(store, '/') )

print( f"Get Store contents: {z[:]}" )


rawBytes = asyncio.run( store.get('zarr.json', prototype=buffer.buffer_prototype) )
print( f"{ rawBytes }" ) 

meta = json.loads(rawBytes.to_bytes().decode('utf-8'))
pprint.pprint(meta)

# memory debug

#snapshot = tracemalloc.take_snapshot()
#top_stats = snapshot.statistics('lineno')

#print("[ Top 10 ]")
#for stat in top_stats[:10]:
#    print(stat)
