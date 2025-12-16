import zarr
import numpy as np

tarStore = zarr.storage.TarStore("exampleGroup.tar", mode="w")

root = zarr.create_group(store=tarStore)
#root
print(root.tree())

# Create nested groups and add arrays
foo = root.create_group("foo")
bar = root.create_array(
    name="bar", shape=(100, 10), chunks=(10, 10), dtype="f4"
)
spam = foo.create_array(name="spam", shape=(10,), dtype="i4")

# Assign values
bar[:, :] = np.random.random((100, 10))
spam[:] = np.arange(10)

# print the hierarchy
print(root.tree())

tarStore.close()

