import zarr
import numpy as np

tarStore = zarr.storage.TarStore("exampleEmptyGroup.tar", mode="w")

root = zarr.create_group(store=tarStore)
#root
print(root.tree())

tarStore.close()