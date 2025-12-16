import zarr
import numpy as np

# Open the TarStore in read-only mode
tarStore = zarr.storage.TarStore("exampleEmptyGroup.tar", read_only=True)
print(tarStore)

root = zarr.open_group(store=tarStore, mode='r')

print(root.tree())

print(root.info)

tarStore.close()