import zarr
import numpy as np

tarStore = zarr.storage.TarStore("exampleArray.tar", mode="w")

tarArray = zarr.create_array(
    store=tarStore,
    shape=(100, 100),
    chunks=(10, 10),
    dtype="f4",
    compressors=None
)

tarArray[:, :] = np.random.random((100, 100))

tarStore.close()