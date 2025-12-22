import zarr
import numpy as np

# Open the ZipStore in read-only mode
store = zarr.storage.TarStore("exampleArray.tar", read_only=True)
print(store)

z = zarr.open_array(store, mode='r')

# read the data as a NumPy Array
print(z[:])
print(z.info)