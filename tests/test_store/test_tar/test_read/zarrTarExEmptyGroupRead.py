import zarr
import numpy as np

# Open the ZipStore in read-only mode
tarStore = zarr.storage.TarStore("exampleEmptyGroup.tar", read_only=True)
print(tarStore)

root = zarr.open_group(store=tarStore, mode='r')
#root
print(root.tree())

print(root.info)

tarStore.close()

#z = zarr.open_array(store, mode='r')

# read the data as a NumPy Array
#print(z[:])
#print(z.info)