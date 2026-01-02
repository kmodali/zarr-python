from __future__ import annotations

import os
import shutil
import threading
import time
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from google_crc32c import value

from zarr.abc.store import (
    ByteRequest,
    OffsetByteRequest,
    RangeByteRequest,
    Store,
    SuffixByteRequest,
)
from zarr.core.buffer import Buffer, BufferPrototype

from zarr.core.common import (
    ZARR_JSON,
    ZARRAY_JSON,
    ZGROUP_JSON,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable

TarStoreAccessModeLiteral = Literal["r", "w", "a"]


class TarStore(Store):
    """
    Store using a TAR file.

    Parameters
    ----------
    path : str
        Location of file.
    mode : str, optional
        One of 'r' to read an existing file, 'w' to truncate and write a new
        file, 'a' to append to an existing file, or 'x' to exclusively create
        and write a new file.
    #compression : int, optional
    #    Compression method to use when writing to the archive.
    #allowZip64 : bool, optional
    #    If True (the default) will create ZIP files that use the ZIP64
    #    extensions when the tarfile is larger than 2 GiB. If False
    #    will raise an exception when the ZIP file would require ZIP64
    #    extensions.

    Attributes
    ----------
    allowed_exceptions
    supports_writes
    supports_deletes
    supports_listing
    path
    #compression
    #allowZip64
    """

    supports_writes: bool = True
    supports_deletes: bool = False
    supports_listing: bool = True

    path: Path
    #compression: int
    #allowZip64: bool

    _tf: tarfile.TarFile
    _lock: threading.RLock

    def __init__(
        self,
        path: Path | str,
        *,
        mode: TarStoreAccessModeLiteral = "r",
        read_only: bool | None = None,
        #compression: int = tarfile.ZIP_STORED,
        #allowZip64: bool = True,
    ) -> None:
        if read_only is None:
            read_only = mode == "r"

        super().__init__(read_only=read_only)

        if isinstance(path, str):
            path = Path(path)
        assert isinstance(path, Path)
        self.path = path  # root?

        self._zmode = mode
        #self.compression = compression
        #self.allowZip64 = allowZip64
        self.metadataDict = {}        

    def _sync_open(self) -> None:
        if self._is_open:
            raise ValueError("store is already open")

        self._lock = threading.RLock()

        self._tf = tarfile.TarFile(
            self.path,
            mode=self._zmode,
            #compression=self.compression,
            #allowZip64=self.allowZip64,
        )

        self._is_open = True
    
    def _sync_open_readonly(self) -> None:
        if self._is_open:
            raise ValueError("store is already open")

        self._lock = threading.RLock()

        self._tf = tarfile.TarFile(
            self.path,
            mode = "r",
            #compression=self.compression,
            #allowZip64=self.allowZip64,
        )

        self._is_open = True






    async def _open(self) -> None:
        self._sync_open()

    def __getstate__(self) -> dict[str, Any]:
        # We need a copy to not modify the state of the original store
        state = self.__dict__.copy()
        for attr in ["_tf", "_lock"]:
            state.pop(attr, None)
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__ = state
        self._is_open = False
        self._sync_open()

    def close(self) -> None:
        # docstring inherited
        if self._is_open:
            super().close()
            with self._lock:
                self._tf.close()
        else:
            print("TarStore.close(): store is already closed")
            pass

    async def clear(self) -> None:
        # docstring inherited
        with self._lock:
            self._check_writable()
            self._tf.close()
            os.remove(self.path)
            self._tf = tarfile.TarFile(
                self.path, mode="w" #, compression=self.compression, allowZip64=self.allowZip64
            )

    def __str__(self) -> str:
        #return f"zip://{self.path}"
        return f"file://{self.path}"

    def __repr__(self) -> str:
        return f"TarStore('{self}')"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.path == other.path

    def _getNew(
        self,
        key: str,
        prototype: BufferPrototype,
        byte_range: ByteRequest | None = None,
    ) -> Buffer | None:
        
         # MKM added -- to avoid crash, when creating new group under 
         #              tarfile ( which is opened in 'w' mode)
        if not self._is_open:
            self._sync_open()
        # docstring inherited
        try: # MKM added 'mode' based on 'tafile' docs 
            f = None
            orignalMode = None
            f = self._tf.getmember(key) # MKM for first time creation needed this, works with 'w' mode
            #if self._zmode == 'w': # MKM for adding a Group to an existing Store / Group
            if f is None:
                return None
            else: # Reading from an existing Store / Group
                if self._zmode == 'w':
                    orignalMode = self._zmode
                    self.close()
                    self._sync_open_readonly()

                with self._tf.extractfile(key) as fObj:  # MKM changed based on tarfile docs
                    if byte_range is None:
                        value = prototype.buffer.from_bytes(fObj.read())
                        #return prototype.buffer.from_bytes(fObj.read())
                        if self._zmode == 'w':
                            self.close()
                            self._sync_open()
                            self._zmode = orignalMode
                        return value
                    elif isinstance(byte_range, RangeByteRequest):
                        fObj.seek(byte_range.start)
                        #return prototype.buffer.from_bytes(fObj.read(byte_range.end - fObj.tell()))
                        value = prototype.buffer.from_bytes(fObj.read(byte_range.end - fObj.tell()))
                        if self._zmode == 'w':
                            self.close()
                            self._sync_open()
                            self._zmode = orignalMode
                        return value
                        
                    
                    size = f.seek(0, os.SEEK_END)
                    if isinstance(byte_range, OffsetByteRequest):
                        fObj.seek(byte_range.offset)
                    elif isinstance(byte_range, SuffixByteRequest):
                        fObj.seek(max(0, size - byte_range.suffix))
                    else:
                        raise TypeError(f"Unexpected byte_range, got {byte_range}.")
                                            #return prototype.buffer.from_bytes(fObj.read(byte_range.end - fObj.tell()))
                    value = prototype.buffer.from_bytes(fObj.read())
                    if self._zmode == 'w':
                        self.close()
                        self._sync_open()
                        self._zmode = orignalMode
                    return value
                    #return prototype.buffer.from_bytes(fObj.read())                
        except KeyError:
            return None

    def _get(
        self,
        key: str,
        prototype: BufferPrototype,
        byte_range: ByteRequest | None = None,
    ) -> Buffer | None:
        
        # MKM added -- to avoid crash, when creating new group under 
        #              tarfile ( which is opened in 'w' mode)
        if not self._is_open:
            self._sync_open()
        # docstring inherited
        try: # MKM added 'mode' based on 'tafile' docs 
            f = self._tf.getmember(key) # MKM for first time creation needed this, works with 'w' mode
            if self._zmode == 'w': # MKM for adding a Group to an existing Store / Group
                #print(f"TarStore._get() 'w' mode  Key: {key}", flush=True)                
                if any( k in key for k in [ ZARR_JSON, ZGROUP_JSON, ZARRAY_JSON ] ):
                    #print(f"Key :{key} substringList {[ ZARR_JSON, ZGROUP_JSON, ZARRAY_JSON ]} found in key.", flush=True)
                    # Fetch the metadata from the dictionary
                    #print(f"TarStore._get() returning metadata: {self.metadataDict[key]} from dictionary for key: {key}", flush=True)
                    return prototype.buffer.from_bytes( self.metadataDict[key].encode('utf-8') )
            else: # Reading from an existing Store / Group
                with self._tf.extractfile(key) as fObj:  # MKM changed based on tarfile docs
                    if byte_range is None:
                        return prototype.buffer.from_bytes(fObj.read())
                    elif isinstance(byte_range, RangeByteRequest):
                        fObj.seek(byte_range.start)
                        return prototype.buffer.from_bytes(fObj.read(byte_range.end - fObj.tell()))
                    
                    size = f.seek(0, os.SEEK_END)
                    if isinstance(byte_range, OffsetByteRequest):
                        fObj.seek(byte_range.offset)
                    elif isinstance(byte_range, SuffixByteRequest):
                        fObj.seek(max(0, size - byte_range.suffix))
                    else:
                        raise TypeError(f"Unexpected byte_range, got {byte_range}.")
                    return prototype.buffer.from_bytes(fObj.read())                
        except KeyError:
            return None

    async def get(
        self,
        key: str,
        prototype: BufferPrototype,
        byte_range: ByteRequest | None = None,
    ) -> Buffer | None:
        # docstring inherited
        assert isinstance(key, str)

        with self._lock:
            return self._get(key, prototype=prototype, byte_range=byte_range)

    async def get_partial_values(
        self,
        prototype: BufferPrototype,
        key_ranges: Iterable[tuple[str, ByteRequest | None]],
    ) -> list[Buffer | None]:
        # docstring inherited
        out = []
        with self._lock:
            for key, byte_range in key_ranges:
                out.append(self._get(key, prototype=prototype, byte_range=byte_range))
        return out

    def _set(self, key: str, value: Buffer) -> None:
        # MKM added for converting value to bytes
        from io import BytesIO 
        
        if not self._is_open:
            self._sync_open()
        # generally, this should be called inside a lock
        keyinfo = tarfile.TarInfo(name=key)
        keyinfo.size = len(value.to_bytes())       
        #keyinfo.compress_type = self.compression

        # MKM Check if the key is a metadata file
        if any( k in key for k in [ ZARR_JSON, ZGROUP_JSON, ZARRAY_JSON ] ): 
            #print(f"Key :{key} substringList {[ ZARR_JSON, ZGROUP_JSON, ZARRAY_JSON ]} found in key.", flush=True)
            # Store the metadata in the dictionary
            self.metadataDict[key] = value.to_bytes().decode('utf-8')
            #print(f"TarStore._set() returning metadata: {self.metadataDict[key]} from dictionary for key: {key}", flush=True)
        self._tf.addfile( tarinfo = keyinfo, fileobj = BytesIO( value.to_bytes() ) )        

    async def set(self, key: str, value: Buffer) -> None:
        # docstring inherited
        self._check_writable()
        if not self._is_open:
            self._sync_open()
        assert isinstance(key, str)
        if not isinstance(value, Buffer):
            raise TypeError(
                f"TarStore.set(): `value` must be a Buffer instance. Got an instance of {type(value)} instead."
            )
        with self._lock:
            self._set(key, value)

    async def set_if_not_exists(self, key: str, value: Buffer) -> None:
        self._check_writable()
        with self._lock:
            members = self._tf.getnames()
            if key not in members:
                self._set(key, value)

    async def delete_dir(self, prefix: str) -> None:
        # only raise NotImplementedError if any keys are found
        self._check_writable()
        if prefix != "" and not prefix.endswith("/"):
            prefix += "/"
        async for _ in self.list_prefix(prefix):
            raise NotImplementedError

    async def delete(self, key: str) -> None:
        # docstring inherited
        # we choose to only raise NotImplementedError here if the key exists
        # this allows the array/group APIs to avoid the overhead of existence checks
        self._check_writable()
        if await self.exists(key):
            raise NotImplementedError

    async def exists(self, key: str) -> bool:
        # MKM added
        if not self._is_open:
            self._sync_open()

        # docstring inherited
        with self._lock:
            try:
                self._tf.getmember(key) # MKM changed based on tarfile docs
            except KeyError:
                return False
            else:
                return True

    async def list(self) -> AsyncIterator[str]:
        # docstring inherited
        # MKM added
        if not self._is_open:
            self._sync_open()
        
        with self._lock:
            for key in self._tf.getnames():
                yield key
        

    async def list_prefix(self, prefix: str) -> AsyncIterator[str]:
        # docstring inherited
        async for key in self.list():
            if key.startswith(prefix):
                yield key

    async def list_dir(self, prefix: str) -> AsyncIterator[str]:
        # docstring inherited
        prefix = prefix.rstrip("/")

        keys = self._tf.getnames()
        seen = set()
        if prefix == "":
            keys_unique = {k.split("/")[0] for k in keys}
            for key in keys_unique:
                if key not in seen:
                    seen.add(key)
                    yield key
        else:
            for key in keys:
                if key.startswith(prefix + "/") and key.strip("/") != prefix:
                    k = key.removeprefix(prefix + "/").split("/")[0]
                    if k not in seen:
                        seen.add(k)
                        yield k

    async def move(self, path: Path | str) -> None:
        """
        Move the store to another path.
        """
        if isinstance(path, str):
            path = Path(path)
        self.close()
        os.makedirs(path.parent, exist_ok=True)
        shutil.move(self.path, path)
        self.path = path
        await self._open()
