"""BACnet data models."""

from typing import Any, Optional
from pydantic import BaseModel


class BACnetDevice(BaseModel):
    pduSource: str
    deviceIdentifier: str
    maxAPDULengthAccepted: int
    segmentationSupported: str
    vendorID: int
    object_name: str
    scanned_ip_target: str
    device_instance: int


class BACnetScanResults(BaseModel):
    status: str
    devices: list[BACnetDevice]


class BACnetReadPropertyRequest(BaseModel):
    device_address: str
    object_identifier: str
    property_identifier: str
    property_array_index: int | None = None


class BACnetWritePropertyRequest(BaseModel):
    device_address: str
    object_identifier: str
    property_identifier: str
    value: Any
    priority: int
    property_array_index: int | None = None


class BACnetReadDeviceAllRequest(BaseModel):
    device_address: str
    device_object_identifier: str


class BACnetReadObjectListRequest(BaseModel):
    device_address: str
    device_object_identifier: str
    page: int | None = None
    page_size: int | None = None
    force_fresh_read: bool = True