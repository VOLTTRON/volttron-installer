"""BacnetScanState - BACnet device scanning and management state."""

import reflex as rx
import json
import csv
import io
import math
import asyncio
from typing import Dict, Any, Optional, Literal
from loguru import logger

from ..model_views import ConfigStoreEntryModelView, BACnetDeviceModelView, BACnetDevicePointModelView
from ..utils.create_component_uid import generate_unique_uid
from ..utils.conversion_methods import csv_string_to_usable_dict
from ..utils.validate_content import check_json
from ..backend.models import ToolRequest, BACnetDevice, BACnetWritePropertyRequest, BACnetReadPropertyRequest, BACnetReadDeviceAllRequest, BACnetReadObjectListRequest
from ..thin_endpoint_wrappers import start_tool, discover_networks, ApiError
from ..models import (
    BACnetObjectType, BACnetPointTableFilter, BACnetPointColumnFilters,
    BACnetDevicePointScanStatus, Instance, InstanceStatus,
    RequestWhoIsModel, ReadDeviceAllModel, ScanIPRangeModel, PingIPModel,
    ReadPropertyModel, WritePropertyModel,
    LocalIPModel, WindowsHostIPModel, NetworkDiscoveryModel,
)

from bacnet_scan_api.models import ObjectListNamesResponse

# Import BACnet thin endpoint wrappers - use wildcard import matching original state.py
from ..thin_endpoint_wrappers import *
from ..thin_endpoint_wrappers import discover_networks, ApiError

class BacnetScanState(rx.State):
    selected_property_tab: Literal["read", "write"] = "read"  # Default to "read" tab
    discovered_devices: list[BACnetDeviceModelView] = []  # Store discovered devices
    selected_device: BACnetDeviceModelView | None = None  # Store the currently selected device
    ip_detection_mode: Literal["", "local_ip", "windows_host_ip", "network_discovery"] = ""  # "local_ip", "windows_host_ip", "network_discovery" or ""
    expanded_device_index: int = -1

    scanning_bacnet_range: bool = False
    is_starting_proxy: bool = False
    proxy_up: bool = False
    pinging_ip: bool = False
    _is_write_property_valid: bool = False
    _is_read_property_valid: bool = False
    _warn_ping_range: bool = False

    # Device Points page filters
    point_table_filter: BACnetPointTableFilter = BACnetPointTableFilter()
    point_column_filter: BACnetPointColumnFilters = BACnetPointColumnFilters()

    # For all points pagination
    _point_per_page_limit: int = 20
    _points_table_page_number: int = 1
    
    # For selected points pagination
    _selected_points_per_page_limit: int = 15
    _selected_points_page_number: int = 1

    # Dialog States
    dialog_registry_open: bool = False
    dialog_select_platform_open: bool = False
    dialog_confirm_add_platform_agent: bool = False
    selected_platform_uid: str = ""

    # Fields
    proxy_field_value: str = ""

    # Models
    request_who_is: RequestWhoIsModel = RequestWhoIsModel()
    read_device_all: ReadDeviceAllModel = ReadDeviceAllModel()
    scan_ip_range: ScanIPRangeModel = ScanIPRangeModel()
    ping_ip: PingIPModel = PingIPModel()
    read_property: ReadPropertyModel = ReadPropertyModel()
    write_property: WritePropertyModel = WritePropertyModel()

    # UI driven models
    local_ip_info: LocalIPModel = LocalIPModel()
    windows_host_ip_info: WindowsHostIPModel = WindowsHostIPModel()
    network_discovery_info: NetworkDiscoveryModel = NetworkDiscoveryModel()
    discovered_networks: list[str] = []  # Store the list of discovered networks
    selected_network: str = ""  # Currently selected network for scanning
    is_discovering_networks: bool = False  # Loading state for network discovery
    
    # Info dialog states
    show_proxy_info_dialog: bool = False
    show_network_info_dialog: bool = False
    show_scan_info_dialog: bool = False
    
    all_device_scan_point_status: list[BACnetDevicePointScanStatus] = []


    _platform_has_platform_driver: bool = True


    # For bacnet point stuff
    NEVER_WRITABLE: list[int] = [
        0,
        3,
        8,
        13,
        37
    ]
    writable_map: Dict[int, BACnetObjectType] = {
        # INPUTS NEVER, some maybe
        0: BACnetObjectType(value=0, type_name="analog-input", writable=False), # NEVER
        1: BACnetObjectType(value=1, type_name="analog-output", writable=True),
        2: BACnetObjectType(value=2, type_name="analog-value", writable=True),
        3: BACnetObjectType(value=3, type_name="binary-input", writable=False), # NEVER
        4: BACnetObjectType(value=4, type_name="binary-output", writable=True),
        5: BACnetObjectType(value=5, type_name="binary-value", writable=True),
        6: BACnetObjectType(value=6, type_name="calendar", writable=True),
        7: BACnetObjectType(value=7, type_name="command", writable=False),
        8: BACnetObjectType(value=8, type_name="device", writable=False), # NEVER
        9: BACnetObjectType(value=9, type_name="event-enrollment", writable=False),
        10: BACnetObjectType(value=10, type_name="file", writable=False),
        11: BACnetObjectType(value=11, type_name="group", writable=False),
        12: BACnetObjectType(value=12, type_name="loop", writable=False),
        13: BACnetObjectType(value=13, type_name="multi-state-input", writable=False), # NEVER
        14: BACnetObjectType(value=14, type_name="multi-state-output", writable=True),
        15: BACnetObjectType(value=15, type_name="notification-class", writable=True),
        16: BACnetObjectType(value=16, type_name="program", writable=True),
        17: BACnetObjectType(value=17, type_name="schedule", writable=True),
        18: BACnetObjectType(value=18, type_name="averaging", writable=False),
        19: BACnetObjectType(value=19, type_name="multi-state-value", writable=True),
        20: BACnetObjectType(value=20, type_name="trend-log", writable=False),
        21: BACnetObjectType(value=21, type_name="life-safety-point", writable=False),
        22: BACnetObjectType(value=22, type_name="life-safety-zone", writable=False),
        23: BACnetObjectType(value=23, type_name="accumulator", writable=False),
        24: BACnetObjectType(value=24, type_name="pulse-converter", writable=False),
        25: BACnetObjectType(value=25, type_name="event-log", writable=False),
        26: BACnetObjectType(value=26, type_name="global-group", writable=False),
        27: BACnetObjectType(value=27, type_name="trend-log-multiple", writable=False),
        28: BACnetObjectType(value=28, type_name="load-control", writable=False),
        29: BACnetObjectType(value=29, type_name="structured-view", writable=False),
        30: BACnetObjectType(value=30, type_name="access-door", writable=False),
        31: BACnetObjectType(value=31, type_name="unassigned", writable=False),
        32: BACnetObjectType(value=32, type_name="access-credential", writable=False),
        33: BACnetObjectType(value=33, type_name="access-point", writable=False),
        34: BACnetObjectType(value=34, type_name="access-rights", writable=False),
        35: BACnetObjectType(value=35, type_name="access-user", writable=False),
        36: BACnetObjectType(value=36, type_name="access-zone", writable=False),
        37: BACnetObjectType(value=37, type_name="credentional-data-input", writable=False), # NEVER
        38: BACnetObjectType(value=38, type_name="network-security", writable=False),
        39: BACnetObjectType(value=39, type_name="bitstring-value", writable=False),
        40: BACnetObjectType(value=40, type_name="characterstring-value", writable=False),
        41: BACnetObjectType(value=41, type_name="date-pattern-value", writable=False),
        42: BACnetObjectType(value=42, type_name="date-value", writable=False),
        43: BACnetObjectType(value=43, type_name="datetime-pattern-value", writable=False),
        44: BACnetObjectType(value=44, type_name="datetime-value", writable=False),
        45: BACnetObjectType(value=45, type_name="integer-value", writable=False),
        46: BACnetObjectType(value=46, type_name="large-analog-value", writable=False),
        47: BACnetObjectType(value=47, type_name="octetstring-value", writable=False),
        48: BACnetObjectType(value=48, type_name="positive-integer-value", writable=False),
        49: BACnetObjectType(value=49, type_name="time-pattern-value", writable=False),
        50: BACnetObjectType(value=50, type_name="time-value", writable=False),
        51: BACnetObjectType(value=51, type_name="notification-forwarder", writable=False),
        52: BACnetObjectType(value=52, type_name="alert-enrollment", writable=False),
        53: BACnetObjectType(value=53, type_name="channel", writable=False),
        54: BACnetObjectType(value=54, type_name="lighting-output", writable=False),
    }

    # important event, actually spins up the tool when the page loads.
    @rx.event
    async def start_tool(self, value):
        await start_tool(
            ToolRequest(
                tool_name=value,
                module_path="bacnet_scan_api.main:app",
                use_poetry=False
            )
        )


    # Computed Vars
    @rx.var
    def platform_has_platform_driver(self) -> bool:
        if self.selected_platform_uid == "":
            return True
        return self._platform_has_platform_driver
        

    # For point pagination
    @rx.var
    def total_pages(self) -> int:
        """Calculate the total number of pages based on filtered points count."""
        if self.selected_device is None or not self.filtered_points_with_indices:
            return 1
        
        # Use the length of filtered points
        total_filtered_points = len(self.filtered_points_with_indices)
        return max(1, math.ceil(total_filtered_points / self._point_per_page_limit))

    @rx.var
    def points_table_page_number(self) -> int:
        """Current page number, clamped to valid range."""
        # Ensure page number is within bounds
        if self._points_table_page_number < 1:
            return 1
        elif self._points_table_page_number > self.total_pages:
            return self.total_pages
        return self._points_table_page_number

    @rx.var
    def next_page_allowed(self) -> bool:
        """Whether there's a next page available."""
        return self.points_table_page_number < self.total_pages

    @rx.var
    def prev_page_allowed(self) -> bool:
        """Whether there's a previous page available."""
        return self.points_table_page_number > 1

    @rx.var
    def points_to_load(self) -> list[tuple[int, BACnetDevicePointModelView]]:
        """Get the points for the current page with their original indices."""
        filtered_points = self.filtered_points_with_indices
        
        if not filtered_points:
            return []
        
        page_view_low = (self.points_table_page_number - 1) * self._point_per_page_limit
        page_view_high = min(page_view_low + self._point_per_page_limit, len(filtered_points))
        
        # Safety check to prevent out-of-bounds errors
        if page_view_low >= len(filtered_points):
            page_view_low = 0
            page_view_high = min(self._point_per_page_limit, len(filtered_points))
        
        return filtered_points[page_view_low:page_view_high]

    @rx.event
    def save_point_table_filters(self, form_data: dict):
        # Update filters based on form data
        filters = {
            "volttron_point_name": form_data.get("volttron_point_name") == "on",
            "units": form_data.get("units") == "on",
            "object_type": form_data.get("object_type") == "on",
            "present_value": form_data.get("present_value") == "on",
            "writable": form_data.get("writable") == "on",
            "index": form_data.get("index") == "on",
            "notes": form_data.get("notes") == "on",
        }
        self.point_column_filter=BACnetPointColumnFilters(**filters)
        self._points_table_page_number = 1  # Reset to first page when filters change

    @rx.var
    def warn_ping_range(self) -> bool: 
        self._warn_ping_range = "/" in self.scan_ip_range.network_string
        return self._warn_ping_range

    @rx.var
    def has_devices(self) -> bool:
        """Check if any devices have been discovered."""
        return len(self.discovered_devices) > 0
    
    @rx.var
    def is_read_property_valid(self) -> bool:
        for field, value in self.read_property.model_dump().items():
            if field == "property_array_index":
                break
            if value == "":
                self._is_read_property_valid = False
                return self._is_read_property_valid
        self._is_read_property_valid = True
        return self._is_read_property_valid

    @rx.var
    def is_write_property_valid(self) -> bool:
        for field, value in self.write_property.model_dump().items():
            if field == "property_array_index":
                break
            if value == "":
                self._is_write_property_valid = False
                return self._is_write_property_valid
        self._is_write_property_valid = True
        return self._is_write_property_valid

    # For selected points pagination
    @rx.var
    def selected_points(self) -> list[BACnetDevicePointModelView]:
        if self.selected_device is not None:
            return [point for point in self.selected_device.points if point.selected]
        return []
    
    @rx.var
    def selected_points_total(self) -> int:
        """Get the total count of selected points."""
        return len(self.selected_points)

    @rx.var
    def selected_points_total_pages(self) -> int:
        """Calculate the total number of pages for selected points."""
        if not self.selected_points:
            return 1
        return max(1, math.ceil(self.selected_points_total / self._selected_points_per_page_limit))

    @rx.var
    def selected_points_page_number(self) -> int:
        """Get the current page number for selected points, with bounds checking."""
        # Ensure page number is within bounds
        if self._selected_points_page_number < 1:
            return 1
        elif self._selected_points_page_number > self.selected_points_total_pages:
            return self.selected_points_total_pages
        return self._selected_points_page_number

    @rx.var
    def paginated_selected_points(self) -> list[BACnetDevicePointModelView]:
        """Get the selected points for the current page only."""
        all_selected = self.selected_points
        
        if not all_selected:
            return []
        
        start_idx = (self.selected_points_page_number - 1) * self._selected_points_per_page_limit
        end_idx = min(start_idx + self._selected_points_per_page_limit, len(all_selected))
        
        # Safety check
        if start_idx >= len(all_selected):
            start_idx = 0
            end_idx = min(self._selected_points_per_page_limit, len(all_selected))
        
        return all_selected[start_idx:end_idx]

    @rx.var
    def selected_points_has_next_page(self) -> bool:
        """Whether there's a next page available for selected points."""
        return self.selected_points_page_number < self.selected_points_total_pages

    @rx.var
    def selected_points_has_prev_page(self) -> bool:
        """Whether there's a previous page available for selected points."""
        return self.selected_points_page_number > 1

    @rx.var
    def filtered_points_with_indices(self) -> list[tuple[int, BACnetDevicePointModelView]]:
        """Get all points that match the current filter, with their original indices."""
        if self.selected_device is None or not self.selected_device.points:
            return []
        
        # Apply filters to the points
        filtered_points = []
        for i, point in enumerate(self.selected_device.points):
            # Check each filter field independently
            # Skip if any filter doesn't match its corresponding field
            # Only apply filters for columns that are visible (not toggled off)
            
            # Check volttron_point_name filter - only if column is visible
            if (self.point_column_filter.volttron_point_name and 
                self.point_table_filter.volttron_point_name and 
                self.point_table_filter.volttron_point_name.lower() not in str(point.volttron_point_name or "").lower()):
                continue
            
            # Check units filter - only if column is visible
            if (self.point_column_filter.units and 
                self.point_table_filter.units and 
                self.point_table_filter.units.lower() not in str(point.units or "").lower()):
                continue
            
            # Check object_type filter - only if column is visible
            if (self.point_column_filter.object_type and 
                self.point_table_filter.object_type and 
                self.point_table_filter.object_type.lower() not in str(point.object_type or "").lower()):
                continue
            
            # Check writable filter - only if column is visible
            if self.point_column_filter.writable and self.point_table_filter.writable:
                writable_filter = self.point_table_filter.writable.lower()
                point_writable_str = str(point.writable).lower()
                
                # Filter for "true"/"false" or partial matches like "t" for true
                if writable_filter not in point_writable_str and (
                    (writable_filter.startswith("t") and not point.writable) or
                    (writable_filter.startswith("f") and point.writable)
                ):
                    continue
            
            # Check present_value filter - only if column is visible
            if (self.point_column_filter.present_value and 
                self.point_table_filter.present_value and 
                self.point_table_filter.present_value.lower() not in str(point.present_value or "").lower()):
                continue
            
            # Check index filter - only if column is visible
            if (self.point_column_filter.index and 
                self.point_table_filter.index and 
                self.point_table_filter.index.lower() not in str(point.index or "").lower()):
                continue
            
            # Check notes filter - only if column is visible
            if (self.point_column_filter.notes and 
                self.point_table_filter.notes and 
                self.point_table_filter.notes.lower() not in str(point.notes or "").lower()):
                continue
            
            # If we get here, the point passed all filters
            filtered_points.append((i, point))
        
        return filtered_points

    @rx.var
    def filtered_points(self) -> list[BACnetDevicePointModelView]:
        """Return just the filtered points."""
        return [point for _, point in self.filtered_points_with_indices]

    # Events
    async def _process_single_point(self, object_identifier: str, properties: Any, device_identifier: str, device_identifier_str: str, device_ip: str) -> Optional[BACnetDevicePointModelView]:
        try:
            # Parse the object identifier to get type and instance
            obj_parts = object_identifier.split(",")
            if len(obj_parts) != 2:
                logger.warning(f"Invalid object identifier format: {object_identifier}")
                return None
                
            object_type = obj_parts[0]
            index_value = obj_parts[1]
            
            # Make sure we are skipping the the "host" device within the points
            if f"{index_value}" == f"{device_identifier_str}":
                return None

            # Extract properties - handle both dict and object formats
            if isinstance(properties, dict):
                # Dictionary format from API response
                point_name = properties.get("object_name") or f"Unknown-{object_identifier}"
                units = properties.get("units")
                present_value = properties.get("present_value")
            else:
                # Object format (fallback for other response types)
                point_name = getattr(properties, 'object_name', None) or f"Unknown-{object_identifier}"
                units = getattr(properties, 'units', None)
                present_value = getattr(properties, 'present_value', None)
            
            # Determine if point is writable and never writable
            writable: bool = False
            never_writable: bool = False
            type_int = None
            
            for k, v in self.writable_map.items():
                if v.type_name == object_type:
                    writable=v.writable
                    type_int = v.type_name
                    if k in self.NEVER_WRITABLE:
                        never_writable = True
                    break
            
            # Try to read the description property
            notes_value = ""
            try:
                # Only try to read notes if we have a valid object type 
                # and it's not one of the problem types
                if type_int and type_int not in ["unknown", "device", "network-port"]:
                    # Note: read_bacnet_property returns a dict
                    data = await read_bacnet_property(
                        BACnetReadPropertyRequest(
                            device_address=device_ip,
                            object_identifier=f"{type_int},{index_value}",
                            property_identifier="description"
                        ),
                        TIMEOUT=0.05
                    )
                    
                    # Extract notes value from response if available
                    if isinstance(data, dict) and "result" in data and "_value" in data["result"]:
                        notes_value = data["result"]["_value"]
            except Exception:
                # If description property read fails, use default value of ""
                pass
                
            # Create point model
            point = BACnetDevicePointModelView(
                device_name=point_name,
                volttron_point_name=point_name,
                writable=writable,
                present_value=present_value if present_value is not None else "",
                units=units if units is not None else "",
                notes=notes_value,
                index=index_value,
                object_type=object_type,
                never_writable=never_writable
            )
            point.safe_point = point.to_dict()
            point.set_write_request_target(device_ip, object_identifier)
            return point
            
        except Exception as e:
            logger.error(f"Error processing point {object_identifier}: {e}")
            return None

    # Background tasks
    @rx.event(background=True)
    async def scan_for_points(self, device: BACnetDeviceModelView, device_index: int, total_points_amount: int):
        """Background task to scan for points from an object list."""
        logger.debug(f"Starting background point scan for device {device.scanned_ip_target}")
        
        # Create status object and add it to the list
        status_id = len(self.all_device_scan_point_status)
        device_name = device.object_name
        
        # Get device index
        device_object_index: list[str] = device.deviceIdentifier.split(",")
        device_identifier: str = device_object_index[1]

        status = BACnetDevicePointScanStatus(
            message=f"Scanning {total_points_amount} points on device: {device_name}...",
            device_name=device_name,
            percent_finished=0,
            object_name=device.object_name  # Using the device's object_name
        )
        
        async with self:
            self.all_device_scan_point_status.append(status)
        yield BacnetScanState.update_ui()
        
        try:
            # Calculate total pages needed
            total_pages = (total_points_amount + self._point_per_page_limit - 1) // self._point_per_page_limit
            logger.debug(f"Scanning {total_points_amount} points across {total_pages} pages")
            
            # Clear existing points if needed
            device.points = []
            
            # Update status
            async with self:
                self.all_device_scan_point_status[status_id].message = f"Preparing to scan {total_points_amount} points..."
            yield BacnetScanState.update_ui()
            
            # Iterate through all pages
            points_processed = 0
            for current_page in range(1, total_pages + 1):
                logger.debug(f"Requesting page {current_page} of {total_pages}")
                
                # Update status - indicate how many points we've processed and how many more to go
                points_so_far = min(points_processed, total_points_amount)
                
                async with self:
                    self.all_device_scan_point_status[status_id].message = f"Reading points {points_so_far+1}-{min(points_so_far+self._point_per_page_limit, total_points_amount)} of {total_points_amount}..."
                    self.all_device_scan_point_status[status_id].percent_finished = int(points_so_far / total_points_amount * 100)
                yield BacnetScanState.update_ui()
                
                res: ObjectListNamesResponse = await read_bacnet_object_list_names(
                    BACnetReadObjectListRequest(
                        device_address=device.scanned_ip_target,
                        device_object_identifier=device.deviceIdentifier,
                        page_size=self._point_per_page_limit,
                        page=current_page,
                        force_fresh_read=True
                    )
                )
                
                if res.status != "done":
                    logger.error(f"Error getting points {points_so_far+1}-{min(points_so_far+self._point_per_page_limit, total_points_amount)}: {res.error}")
                    async with self:
                        self.all_device_scan_point_status[status_id].message = f"Error retrieving points {points_so_far+1}-{min(points_so_far+self._point_per_page_limit, total_points_amount)}: {res.error}"
                    yield BacnetScanState.update_ui()
                    points_processed += self._point_per_page_limit  # Move to next page even if there was an error
                    continue
                    
                # Update status - processing points
                points_in_page = len(res.results)
                async with self:
                    self.all_device_scan_point_status[status_id].message = f"Processing {points_in_page} points ({points_so_far+1}-{points_so_far+points_in_page} of {total_points_amount})..."
                yield BacnetScanState.update_ui()
                    
                # Process the results for this page in parallel
                tasks = []
                for object_identifier, properties in res.results.items():
                    tasks.append(
                        self._process_single_point(
                            object_identifier, 
                            properties, 
                            device_identifier, 
                            device_identifier,
                            device.scanned_ip_target
                        )
                    )
                
                # Execute all tasks concurrently to speed up property reading
                processed_points = await asyncio.gather(*tasks)
                
                # Add valid points to device
                valid_points_count = 0
                for point in processed_points:
                    if point is not None:
                        device.points.append(point)
                        valid_points_count += 1
                        logger.debug(f"Added point: {point.volttron_point_name} ({point.index})")
                
                # Update UI after each page to show progress
                points_processed += points_in_page
                points_processed_so_far = min(points_processed, total_points_amount)
                
                async with self:
                    self.discovered_devices[device_index] = device
                    self.all_device_scan_point_status[status_id].message = f"Scanned {points_processed_so_far} of {total_points_amount} points"
                    self.all_device_scan_point_status[status_id].percent_finished = int(points_processed_so_far / total_points_amount * 100)
                yield BacnetScanState.update_ui()
                
                # Optional: Add a small delay to avoid overwhelming the device
                await asyncio.sleep(0.5)
                
            # Update status to show completion
            async with self:
                self.all_device_scan_point_status[status_id].message = f"Completed scan of {len(device.points)} points for {device_name}"
                self.all_device_scan_point_status[status_id].percent_finished = 100
            yield BacnetScanState.update_ui()
            
        except Exception as e:
            logger.error(f"Failed during point scan: {e}")
            async with self:
                self.all_device_scan_point_status[status_id].message = f"Error during scan: {str(e)}"
                self.all_device_scan_point_status[status_id].percent_finished = 100
            yield BacnetScanState.update_ui()
        
        logger.debug(f"Completed background point scan for device {device.scanned_ip_target}")
        
        # Final UI update
        yield BacnetScanState.update_ui()
        
        # Remove status after 5 seconds
        await asyncio.sleep(5)
        async with self:
            if status_id < len(self.all_device_scan_point_status):
                self.all_device_scan_point_status.pop(status_id)
        yield BacnetScanState.update_ui()

    @rx.event
    def update_ui(self): yield
        
    # For points pagination
    @rx.event
    def next_point_page(self):
        """Go to the next page if available."""
        if self.next_page_allowed:
            self._points_table_page_number += 1

    @rx.event
    def prev_point_page(self):
        """Go to the previous page if available."""
        if self.prev_page_allowed:
            self._points_table_page_number -= 1
    
    # May use one day
    @rx.event
    def go_to_point_page(self, page_number: int):
        """Go to a specific page."""
        if 1 <= page_number <= self.total_pages:
            self._points_table_page_number = page_number

    # For selected points pagination
    @rx.event
    def selected_points_next_page(self):
        """Go to the next page of selected points if available."""
        if self.selected_points_has_next_page:
            self._selected_points_page_number += 1

    @rx.event
    def selected_points_prev_page(self):
        """Go to the previous page of selected points if available."""
        if self.selected_points_has_prev_page:
            self._selected_points_page_number -= 1
            
    @rx.event
    def selected_points_go_to_page(self, page: int):
        """Go to a specific page of selected points."""
        if 1 <= page <= self.selected_points_total_pages:
            self._selected_points_page_number = page
    
    # Dialog events
    @rx.event
    def open_registry_dialog(self):
        self.dialog_registry_open = True
        self.dialog_select_platform_open = False

    @rx.event
    def open_select_platform_dialog(self):
        self.dialog_registry_open = False
        self.dialog_select_platform_open = True

    @rx.event
    def close_dialogs(self):
        self.selected_platform_uid = ""
        self.dialog_registry_open = False
        self.dialog_select_platform_open = False

    @rx.event
    def on_selected_points_dialog_close(self):
        self._selected_points_page_number = 1

    @rx.event
    def filter_form_submit(self, form_data: dict):
        # Start with the current filter values
        current_filter = self.point_table_filter
        
        # Create a new filter object preserving all existing values
        self.point_table_filter = BACnetPointTableFilter(
            # For each field, use the form data if provided, otherwise keep existing value
            volttron_point_name=form_data.get("volttron_point_name", current_filter.volttron_point_name),
            units=form_data.get("units", current_filter.units),
            object_type=form_data.get("object_type", current_filter.object_type),
            writable=form_data.get("writable", current_filter.writable).strip() if form_data.get("writable") is not None else current_filter.writable,
            present_value=form_data.get("present_value", current_filter.present_value),
            index=form_data.get("index", current_filter.index),
            notes=form_data.get("notes", current_filter.notes)
        )

    @rx.event
    def clear_point_filter(self, field: str):
        change: dict[str, str] = self.point_table_filter.dict()
        change[field] = ""  # Clear the specified field
        self.point_table_filter = BACnetPointTableFilter(
            **change
        )
        self._selected_points_page_number = 1

    @rx.event
    def toggle_select_all_points(self, checked: bool):
        self.selected_device.select_all_points = checked
        for point in self.selected_device.points:
            point.selected=checked

        # Reset to first page when selections change
        self._selected_points_page_number = 1

    @rx.event
    def handle_device_check(self, device_index: int, checked: bool):
        device_index = self.get_absolute_index(device_index)
        self.selected_device.select_all_points = False
        self.selected_device.points[device_index].selected = checked
        
        # Reset to first page when selections change
        self._selected_points_page_number = 1

    @rx.event
    def handle_proxy_field_edit(self, value: str):
        self.proxy_field_value = value 

    @rx.event
    def set_selected_property_tab(self, tab: str):
        """Update the selected property tab."""
        self.selected_property_tab = tab
    
    @rx.event
    def handle_device_row_click(self, device_index: int):
        """Handle when a device row is clicked."""
        if 0 <= device_index < len(self.discovered_devices):
            selected_device = self.discovered_devices[device_index]
            if selected_device == self.selected_device:
                self.selected_device = None
                return
            self.selected_device = selected_device
            
            # Auto-fill the property operation fields with selected device info
            device_address = selected_device.scanned_ip_target
            device_id = selected_device.deviceIdentifier
            
            # Update read property form
            self.read_property.device_address = device_address
            self.read_property.object_identifier = f"{device_id}"
            
            # Update write property form
            self.write_property.device_address = device_address
            self.write_property.object_identifier = f"{device_id}"
            
            yield rx.toast.info(f"Selected device: {selected_device.object_name}")
    
    @rx.event
    def set_ip_detection_mode(self, mode: Literal["windows_host_ip", "local_ip", "network_discovery"]):
        """Switch between local IP, Windows host IP, and network discovery mode."""
        self.ip_detection_mode = mode
        yield BacnetScanState.get_network_info()

    @rx.event
    async def get_network_info(self):
        """Get network information based on current detection mode."""
        self.pinging_ip = True
        yield rx.toast.info(f"Retrieving network information...")        
        if self.ip_detection_mode == "local_ip":
            yield BacnetScanState.handle_get_local_ip()
        elif self.ip_detection_mode == "windows_host_ip":
            yield BacnetScanState.handle_get_windows_host_ip()
        elif self.ip_detection_mode == "network_discovery":
            yield BacnetScanState.handle_discover_networks()

        self.pinging_ip = False
        yield

    @rx.event
    def set_open_items(self, value):
        self._open_accordion_items = value

    @rx.event
    def toggle_proxy(self):
        """Toggle the proxy state"""
        if self.proxy_up:
            yield BacnetScanState.stop_proxy()
        else:
            yield rx.toast.info("Starting proxy...")
            yield BacnetScanState.start_proxy()

    @rx.event
    async def start_proxy(self):
        """Handle the start proxy button click"""
        if self.is_starting_proxy:
            yield rx.toast.info("Proxy is already starting.")
            return
        self.is_starting_proxy = True
        yield
        try:
            ip_address = self.proxy_field_value if self.proxy_field_value != "" else None
            logger.debug(f"this is the ip address we will start a proxy with: {ip_address}")
            data = await start_bacnet_proxy(ip_address)
            if data.get("status") == "error":
                raise Exception(data)
            self.proxy_field_value = data["address"]
            self.proxy_up = True
            self.is_starting_proxy = False
            yield rx.toast.success("Proxy started successfully.")
        except Exception as e:
            logger.debug(e)
            self.is_starting_proxy = False
            yield rx.toast.error("There was an error starting up a BACnet proxy")

    @rx.event
    async def stop_proxy(self):
        try:
            await stop_bacnet_proxy()
            self.proxy_up = False
            yield rx.toast.success("Proxy stopped successfully")
        except Exception as e:
            logger.debug(f"Error starting proxy: {e}")
            yield rx.toast.error("There was an error stopping the BACnet proxy")
    
    @rx.event
    async def handle_bacnet_scan(self):
        """Handle the BACnet scan button click"""
        if self.scanning_bacnet_range:
            yield rx.toast.info("BACnet scan is already in progress.")
            return
        self.scanning_bacnet_range = True
        yield
        # TODO implement scan logic
        import asyncio
        await asyncio.sleep(2)
        self.scanning_bacnet_range = False
        self.discovered_devices=[
            {"name": "Device Alpha", "id": "1234", "address": "192.168.1.10"},
            {"name": "Device Beta", "id": "5678", "address": "192.168.1.12"},
            {"name": "Device Gamma", "id": "9012", "address": "192.168.1.14"},
        ]
        yield

    # Handle inputs into model
    @rx.event
    def request_who_is_input(self, field: str, value: str):
        """Handle input changes for the Request Who Is form."""
        if field == "device_instance_low":
            self.request_who_is.device_instance_low = value
        elif field == "device_instance_high":
            self.request_who_is.device_instance_high = value
        elif field == "dest":
            self.request_who_is.dest = value

    @rx.event
    def read_device_all_input(self, field: str, value: str):
        """Handle input changes for the Read Device All form."""
        if field == "device_address":
            self.read_device_all.device_address = value
        elif field == "device_object_identifier":
            self.read_device_all.device_object_identifier = value

    @rx.event
    def scan_ip_range_input(self, value: str):
        """Handle input changes for the Scan IP Range form."""
        self.scan_ip_range.network_string = value

    @rx.event
    def ping_ip_input(self, value: str):
        """Handle input changes for the Ping IP form."""
        self.ping_ip.ip_address = value

    @rx.event
    def read_property_input(self, field: str, value: str):
        """Handle input changes for the Read Property form."""
        if field == "device_address":
            self.read_property.device_address = value
        elif field == "object_identifier":
            self.read_property.object_identifier = value
        elif field == "property_identifier":
            self.read_property.property_identifier = value
        elif field == "property_array_index":
            # Handle empty string as None for optional field
            self.read_property.property_array_index = value if value.strip() else None

    @rx.event
    def write_property_input(self, field: str, value: str):
        """Handle input changes for the Write Property form."""
        if field == "device_address":
            self.write_property.device_address = value
        elif field == "object_identifier":
            self.write_property.object_identifier = value
        elif field == "property_identifier":
            self.write_property.property_identifier = value
        elif field == "value":
            self.write_property.value = value
        elif field == "priority":
            self.write_property.priority = value
        elif field == "property_array_index":
            # Handle empty string as None for optional field
            self.write_property.property_array_index = value if value.strip() else None

    @rx.event
    def ip_address_input(self, value: str):
        """Handle input change for the main IP address field."""
        self.ip_address = value

    # Handle Device Point editing
    @rx.event
    def handle_present_value_edit(self, index: int, value: str):
        index = self.get_absolute_index(index)
        self.selected_device.points[index].present_value = value

    @rx.event
    def enable_device_point_present_value_edit(self, index: int):
        index = self.get_absolute_index(index)
        self.selected_device.points[index].present_value_editing = True
    
    @rx.event
    def disable_device_point_present_value_edit(self, index: int):
        index = self.get_absolute_index(index)
        self.selected_device.points[index].present_value_editing = False

    @rx.event
    def cancel_device_point_present_value_edit(self, index: int):
        absolute_index = self.get_absolute_index(index)
        yield BacnetScanState.disable_device_point_present_value_edit(index)
        yield
        self.selected_device.points[absolute_index].present_value = self.selected_device.points[absolute_index].safe_point['present_value']
        yield

    @rx.event
    def save_device_point_present_value_edit(self, index: int):
        absolute_index = self.get_absolute_index(index)
        yield BacnetScanState.disable_device_point_present_value_edit(index)
        yield
        self.selected_device.points[absolute_index].safe_point = self.selected_device.points[absolute_index].to_dict()
        yield
        yield BacnetScanState.handle_write_property(
            self.selected_device.points[absolute_index],
            "present-value",
            self.selected_device.points[absolute_index].safe_point["present_value"],
            8
        )

    @rx.event
    def flip_device_point_writable(self, index: int):
        """Toggle the writable state of a device point."""
        index = self.get_absolute_index(index)
        point = self.selected_device.points[index]
        point.writable = not point.writable
        # Update the writable map for this object type
        if point.object_type in self.writable_map:
            self.writable_map[point.object_type].writable = point.writable


    @rx.event
    def handle_volttron_point_name_value_edit(self, index: int, value: str):
        index = self.get_absolute_index(index)
        self.selected_device.points[index].volttron_point_name = value

    @rx.event
    def enable_device_point_volttron_point_name_value_edit(self, index: int):
        index = self.get_absolute_index(index)
        self.selected_device.points[index].volttron_point_name_editing = True
    
    @rx.event
    def disable_device_point_volttron_point_name_value_edit(self, index: int):
        index = self.get_absolute_index(index)
        self.selected_device.points[index].volttron_point_name_editing = False

    @rx.event
    def cancel_device_point_volttron_point_name_value_edit(self, index: int):
        absolute_index = self.get_absolute_index(index)
        yield BacnetScanState.disable_device_point_volttron_point_name_value_edit(index)
        yield
        self.selected_device.points[absolute_index].volttron_point_name = self.selected_device.points[absolute_index].safe_point['volttron_point_name']
        yield

    @rx.event
    def save_device_point_volttron_point_name_value_edit(self, index: int):
        absolute_index = self.get_absolute_index(index)
        yield BacnetScanState.disable_device_point_volttron_point_name_value_edit(index)
        yield
        self.selected_device.points[absolute_index].safe_point = self.selected_device.points[absolute_index].to_dict()
        yield


    # Handle the actual endpoint actions/functionality
    @rx.event
    async def handle_request_who_is(self):
        """Handle the Request Who Is form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
            
        # Access form data using self.request_who_is.device_instance_low, etc.
        yield rx.toast.info(f"Sending Who-Is request from {self.request_who_is.device_instance_low} to {self.request_who_is.device_instance_high}")
        
        # TODO: Implement actual BACnet logic here
        import asyncio
        await asyncio.sleep(1)
        
        # Example response handling
        yield rx.toast.success("Who-Is request completed.")
    
    @rx.event
    async def handle_read_device_all(self):
        """Handle the Read Device All form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
            
        yield rx.toast.info(f"Reading all properties from device {self.read_device_all.device_address}")
        
        # TODO: Implement actual BACnet logic here
        import asyncio
        await asyncio.sleep(1)
        
        yield rx.toast.success("Read Device All completed.")
    
    @rx.event
    async def handle_scan_ip_range(self):
        """Handle the Scan IP Range form submission."""
        from bacnet_scan_api.models import ScanResponse
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
        yield
        self.scanning_bacnet_range = True
        yield
        
        try:
            scan_results: ScanResponse = await scan_bacnet_subnet(self.scan_ip_range.network_string)
            logger.debug(f"Raw scan_results: {scan_results}")
            logger.debug(f"scan_results.devices: {scan_results.devices}")
            
            # Get devices 
            devices = [
                BACnetDeviceModelView(
                    deviceIdentifier = device.deviceIdentifier,
                    device_instance=device.device_instance,
                    scanned_ip_target = device.address,
                    vendorId = device.vendorID,
                )
                for device in scan_results.devices
            ]
            logger.debug(f"devices we found: {devices}")

            # Read device all on each of our devices[]
            for device_index, device in enumerate(devices):
                logger.debug(f"this is our device we are operating on: {device}")
                try:            
                    res = await read_bacnet_device_all(
                            BACnetReadDeviceAllRequest(
                                device_address=device.scanned_ip_target,
                                device_object_identifier=device.deviceIdentifier
                            ),
                            timeout=30.0
                        )
                    if res.get("status") == "error":
                        logger.debug(f"this is our res: {res}")
                        raise Exception(f"Error occurred calling api though thin endpoint wrapper")
                except Exception as e:
                    import traceback
                    logger.debug(f"An error occurred reading device {device.scanned_ip_target}: {traceback.format_exc()}")
                    device.object_name="UNKNOWN"
                    device.read_device_all_failed = True
                    continue  # Skip this device and move to the next one instead of breaking
                
                # Only execute these lines if the device was successfully read
                logger.debug(f"Device {device.scanned_ip_target} response structure: {list(res.keys())}")
                
                # Check the response structure - it could be either format
                if "result" in res:
                    # Successful response format: {"result": {...}, "error": {...}}
                    device.object_name = res["result"].get("object-name", "UNKNOWN")
                    
                    # Check if object-list exists in the result
                    if "object-list" not in res["result"]:
                        logger.debug(f"Device {device.scanned_ip_target} does not have 'object-list' property. Available properties: {list(res['result'].keys())}")
                        device.read_device_all_failed = True
                        continue  # Skip this device and move to the next one
                    
                    points: list = res["result"]["object-list"]
                elif "properties" in res and "result" in res["properties"]:
                    # New response format: {"status": "done", "properties": {"result": {...}}, "error": ...}
                    logger.debug(f"Device {device.scanned_ip_target} using properties.result format")
                    device.object_name = res["properties"]["result"].get("object-name", "UNKNOWN")
                    
                    # Check if object-list exists in the result
                    if "object-list" not in res["properties"]["result"]:
                        logger.debug(f"Device {device.scanned_ip_target} does not have 'object-list' property. Available properties: {list(res['properties']['result'].keys())}")
                        device.read_device_all_failed = True
                        continue  # Skip this device and move to the next one
                    
                    points: list = res["properties"]["result"]["object-list"]
                elif "properties" in res:
                    # Error response format: {"status": "error", "properties": "", "error": ...}
                    logger.debug(f"Device {device.scanned_ip_target} returned error response format: {res}")
                    device.object_name = "UNKNOWN"
                    device.read_device_all_failed = True
                    continue  # Skip this device and move to the next one
                else:
                    # Unknown response format
                    logger.debug(f"Device {device.scanned_ip_target} returned unknown response format. Response keys: {list(res.keys())}")
                    device.object_name = "UNKNOWN"
                    device.read_device_all_failed = True
                    continue  # Skip this device and move to the next one
                
                if not points or len(points) <= 1:
                    logger.debug(f"Device {device.scanned_ip_target} has no scannable points (object-list length: {len(points) if points else 0})")
                    continue  # Skip devices with no points to scan
                
                points_amount: int = len(points) - 1
                logger.debug(f"we have {points_amount} points to scan for on device {device.scanned_ip_target}")
                # logger.debug(f"we are going to go through {len(points) - 1}")
                # logger.debug(f"sike we only getting 50")
                
                # Launch background task to scan for points
                yield BacnetScanState.scan_for_points(device, device_index, points_amount) 

            logger.debug(f"this is our scan results: {scan_results}")
            self.discovered_devices = devices
            yield rx.toast.success("IP Range scan completed.")
        except:
            import traceback
            logger.debug(f"An error occurred running scan: {traceback.format_exc()}")
        
        self.scanning_bacnet_range = False
    
    @rx.event
    async def handle_ping_ip(self):
        """Handle the Ping IP form submission."""
        yield rx.toast.info(f"Pinging IP: {self.ping_ip.ip_address}")
        
        # TODO: Implement actual ping logic here
        import asyncio
        await asyncio.sleep(0.5)
        
        yield rx.toast.success("Ping completed.")
    
    @rx.event
    async def handle_read_property(self):
        """Handle the Read Property form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return
            
        yield rx.toast.info(f"Reading property from {self.read_property.device_address}")
        
        # TODO: Implement actual BACnet logic here
        import asyncio
        await asyncio.sleep(1)
        
        yield rx.toast.success("Read Property completed.")
    
    @rx.event
    async def handle_write_property(
        self, 
        point: BACnetDevicePointModelView, 
        property_identifier: str, 
        value: Any,
        priority: int, 
        property_array_index: int | None = None
    ):
        """Handle the Write Property form submission."""
        if not self.proxy_up:
            yield rx.toast.error("Proxy must be started first.")
            return

        yield rx.toast.info(f"Writing to property on {self.write_property.device_address}")
        logger.debug(f"Writing `{property_identifier}` with value: `{value}` on address: `{self.write_property.device_address}`")

        try:
            logger.debug(f"Writing bacnet property: {property_identifier}, to target: {point.write_request_target}, value: {value}")
            response = await write_bacnet_property(
                BACnetWritePropertyRequest(
                    **point.write_request_target,
                    # device_address="130.20.24.157",
                    # object_identifier="2,3000112",
                    # ==============================
                    property_identifier=property_identifier,
                    value=value,
                    priority=priority
                    # Omit property_array_index for now 
                )
            )
            logger.debug(f"we have written and this is our response: {response}")
        except:
            import traceback
            logger.debug(f"An error occurred writing property {traceback.format_exc()}")
        
        yield rx.toast.success("Write Property completed.")

    @rx.event
    async def handle_get_local_ip(self):
        try:
            self.local_ip_info = await get_bacnet_local_ip(self.local_ip_info)
            self.scan_ip_range.network_string = self.local_ip_info.cidr
            yield rx.toast.success("Retrieved Local Host IP")
        except Exception as e:
            logger.debug(f"There was an error getting local ip info {e}")

    @rx.event
    async def handle_get_windows_host_ip(self):
        try:
            self.windows_host_ip_info = await get_bacnet_host_ip()
            self.scan_ip_range.network_string = self.windows_host_ip_info.address.rsplit('.', 1)[0] + ".0/24" # Split at the last period, max 1 split. tack it off with cidr range
            yield rx.toast.success("Retrieved Host IP")
        except Exception as e:
            logger.debug(f"There was an error getting local ip info {e}")

    @rx.event
    async def handle_discover_networks(self):
        """Handle comprehensive network discovery."""
        try:
            # Set loading state
            self.is_discovering_networks = True
            self.discovered_networks = []  # Clear previous results
            yield  # Yield to update UI immediately
            
            # Perform the discovery
            self.network_discovery_info = await discover_networks(verbose=False)
            
            # Process results
            if self.network_discovery_info.status == "done":
                self.discovered_networks = self.network_discovery_info.networks
                # Auto-select the first network if available
                if self.discovered_networks:
                    self.selected_network = self.discovered_networks[0]
                    self.scan_ip_range.network_string = self.selected_network
                yield rx.toast.success(f"Discovered {len(self.discovered_networks)} networks using comprehensive analysis")
            else:
                yield rx.toast.error(f"Network discovery failed: {self.network_discovery_info.error}")
        except Exception as e:
            logger.debug(f"There was an error during network discovery: {e}")
            yield rx.toast.error("Network discovery failed")
        finally:
            # Always clear loading state
            self.is_discovering_networks = False

    @rx.event
    def select_discovered_network(self, network: str):
        """Select a discovered network for scanning."""
        self.selected_network = network
        self.scan_ip_range.network_string = network
        yield rx.toast.info(f"Selected network: {network}")

    # Info dialog handlers
    @rx.event
    def show_proxy_info(self):
        """Show BACnet proxy information dialog."""
        self.show_proxy_info_dialog = True
    
    @rx.event
    def hide_proxy_info(self):
        """Hide BACnet proxy information dialog."""
        self.show_proxy_info_dialog = False
    
    @rx.event
    def show_network_info(self):
        """Show network information dialog."""
        self.show_network_info_dialog = True
    
    @rx.event
    def hide_network_info(self):
        """Hide network information dialog."""
        self.show_network_info_dialog = False
    
    @rx.event
    def show_scan_info(self):
        """Show scan for devices information dialog."""
        self.show_scan_info_dialog = True
    
    @rx.event
    def hide_scan_info(self):
        """Hide scan for devices information dialog."""
        self.show_scan_info_dialog = False

    # Other
    @rx.event
    async def select_platform_for_registry_config(self, uid: str):
        from ..state import PlatformPageState
        self.selected_platform_uid = uid if self.selected_platform_uid != uid else ""

        platform_state = await self.get_state(PlatformPageState)
        platform = platform_state.platforms.get(uid)
        if not platform:
            self._platform_has_platform_driver = True
            return
        
        self._platform_has_platform_driver = "platform.driver" in platform.platform.agents
        return

    @rx.event
    def on_add_to_registry_config_confirm(self, form_data):
        """Handle the confirmation to add selected points to registry config."""
        if self.selected_platform_uid == "":
            # yield rx.toast.error("No platform selected for registry config.")
            return
        
        logger.debug(f"selected platform UID: {self.selected_platform_uid}")
        platform_uid = self.selected_platform_uid

        path = form_data.get("path", "")
        if path == "":
            yield rx.toast.error("Path cannot be empty.")
            return

        # Close any open dialogs
        yield BacnetScanState.close_dialogs()
        
        # Convert selected points to CSV format
        csv_data = self._convert_selected_points_to_csv()
        escaped_csv_data = csv_data.replace("'", "\\'")
        
        # Add the registry config to the platform
        yield BacnetScanState.on_add_to_registry_config(platform_uid, path, escaped_csv_data)

    # TODO move all the stuff handiling adding the actual config store entry to its designated state and method
    @rx.event
    async def on_add_to_registry_config(self, platform_uid: str, path: str, escaped_csv_data: str):
        """Add selected BACnet points to a platform.driver registry configuration."""
        from ..state import PlatformPageState
        # Close any open dialogs
        yield BacnetScanState.close_dialogs()


        # Step 1: Ensure platform.driver agent exists
        # yield BacnetScanState.ensure_platform_driver_exists(platform_uid)
        # we need tto shove the method in here to ensure that it runs one at a time...
        platform_page_state: PlatformPageState = await self.get_state(PlatformPageState)
        platform = platform_page_state.platforms.get(platform_uid)
        if not platform:
            logger.debug(f"Platform with UID {platform_uid} not found.")
            logger.debug(f"Available platforms: {list(platform_page_state.platforms.keys())}")
            yield rx.toast.error("Platform not found")
            return
        
        # Find and add platform.driver agent
        if "platform.driver" not in platform.platform.agents:
            for agent in platform_page_state.list_of_agents:
                if agent.identity == "platform.driver":
                    yield PlatformPageState.handle_adding_agent(agent, platform_uid)
        # ===============================================================

        # Step 2: Add the registry config to the platform.driver agent
        yield BacnetScanState.add_config_to_platform_driver(
            platform_uid, 
            escaped_csv_data,
            path
        )
        
        # Step 3: Create corresponding device config JSON
        # Extract location info from the current scan if available
        registry_name = path if path else "bacnet_registry.csv"
        if not registry_name.endswith(".csv"):
            registry_name += ".csv"
        
        # Parse device info from selected device
        campus = "campus"
        building = "building"
        unit = "bacnet_device"
        
        # Try to get device info from selected device
        if self.selected_device:
            device = self.selected_device
            # Use device instance or ID as unit name
            unit = f"bacnet_{device.device_id}" if device.device_id else "bacnet_device"
            # If device has a name, use it
            if device.name:
                unit = device.name.lower().replace(" ", "_")
        
        # Create device config JSON
        device_config = {
            "driver_config": {
                "device_address": getattr(self.selected_device, "address", ""),
                "device_id": getattr(self.selected_device, "device_id", 0)
            },
            "driver_type": "bacnet",
            "registry_config": f"config://{registry_name}",
            "interval": 5,
            "timezone": "US/Pacific",
            "campus": campus,
            "building": building,
            "unit": unit,
        }
        
        device_path = f"devices/{campus}/{building}/{unit}"
        
        # Add device config to platform.driver
        driver_agent = platform.platform.agents.get("platform.driver")
        if driver_agent:
            device_component_id = generate_unique_uid()
            device_entry = ConfigStoreEntryModelView(
                path=device_path,
                data_type="JSON",
                value=json.dumps(device_config, indent=2),
                component_id=device_component_id,
                uncommitted=False,
                valid=True,
            )
            device_entry.safe_entry = {
                "path": device_path,
                "data_type": "JSON",
                "value": json.dumps(device_config, indent=2),
                "component_id": device_component_id,
                "csv_variants": ""
            }
            driver_agent.config_store.append(device_entry)
            driver_agent.safe_agent = driver_agent.to_dict()
            
            yield rx.toast.success(f"BACnet driver added: {device_path}")

    @rx.event
    async def ensure_platform_driver_exists(self, platform_uid: str):
        """Make sure the platform has a platform.driver agent.

        Returns:
            bool: True if platform.driver exists or was successfully added, False otherwise.
        """
        from ..state import PlatformPageState
        platform_page_state: PlatformPageState = await self.get_state(PlatformPageState)
        platform = platform_page_state.platforms.get(platform_uid)
        if not platform:
            return
        
        # Check if platform.driver already exists
        if "platform.driver" in platform.platform.agents:
            return 
        
        # Find and add platform.driver agent
        for agent in platform_page_state.list_of_agents:
            if agent.identity == "platform.driver":
                yield PlatformPageState.handle_adding_agent(agent, platform_uid)
                # We need to check if the agent was actually added
                return 
        
        # Couldn't find platform.driver in available agents
        yield rx.toast.error("Could not add platform.driver agent")
    
    @rx.event
    async def add_config_to_platform_driver(
        self, 
        platform_uid: str, 
        csv_value: str,
        path: str
    ):
        """Add a config store entry with the CSV value to the platform.driver agent."""
        platform_page_state: PlatformPageState = await self.get_state(PlatformPageState)
        platform = platform_page_state.platforms.get(platform_uid)
        if "platform.driver" not in platform.platform.agents:
            yield rx.toast.error("Platform or platform.driver agent not found")
        
        # Get the platform.driver agent
        driver_agent = platform.platform.agents.get("platform.driver", None)
        if driver_agent is None:
            logger.debug(f"an error occurred, here are the list of agents on the platform: {platform.platform.agents.keys()}")
            yield rx.toast.error("Platform.driver agent not found on platform")
            return

        # Create and add the config store entry
        component_id = generate_unique_uid()
        config_entry = self._create_config_store_entry(path, csv_value, component_id)
        driver_agent.config_store.append(config_entry)
        
        # Save the config store entry

        # NOTE: This is largely a copy and paste job from AgentConfigState.save_config_store_entry
        # TODO: make the function referenced above more modular and not tied to AgentConfigState variables
        list_of_config_paths: list[tuple[str, str]] = [
            (entry_.safe_entry["path"], entry_.component_id) for entry_ in driver_agent.config_store
        ]
        # Check if the path exists and belongs to a different component
        for path, component_id in list_of_config_paths:
            if config_entry.path == "" or (config_entry.path == path and config_entry.component_id != component_id):
                # This check catches all empty paths or duplicate paths
                yield rx.toast.error(f"Config path is already in use.")
                return
        config_entry.safe_entry = config_entry.dict()
        logger.debug(f"this is the config_entry's safe dict: {config_entry.safe_entry}")
        config_entry.uncommitted=False
        logger.debug(f"going through the agent's config store, here they are:")
        for driver_agent_config in driver_agent.config_store:
            logger.debug(f"safe dict: {driver_agent_config.safe_entry}")

        # Finalize and save the agent
        driver_agent.is_new = False
        driver_agent.safe_agent = driver_agent.to_dict()
        
        # Update the platform state
        # yield PlatformPageState.cement_registry_config(platform)
        yield rx.toast.success("BACnet points added to registry")

    # Exporting
    @rx.event
    def export_to_csv(self):
        csv_data = self._convert_selected_points_to_csv()

        escaped_csv_data = csv_data.replace("'", "\\'")  # Escape single quotes in CSV content
        
        # JavaScript code for invoking the "Save As" dialog
        js_code = f"""
            if (window.showSaveFilePicker) {{
                // Use File System Access API for explicit Save As dialog
                async function saveFile() {{
                    try {{
                        const options = {{
                            suggestedName: 'points',
                            types: [{{
                                description: 'CSV file',
                                accept: {{
                                    'text/csv': ['.csv']
                                }}
                            }}]
                        }};
                        const fileHandle = await window.showSaveFilePicker(options);
                        const writable = await fileHandle.createWritable();
                        await writable.write(`{escaped_csv_data}`);
                        await writable.close();
                        return true;  // Indicate success
                    }} catch (err) {{
                        // Check if this is an abort error (user canceled)
                        if (err.name === 'AbortError') {{
                            // console.log('User canceled the save dialog');
                            return false;  // User canceled
                        }} else {{
                            // console.error('Save As failed:', err);
                            return false;  // Other error
                        }}
                    }}
                }}
                
                saveFile();  // We don't need to catch here as we already handle errors inside
            }} else {{
                // Fallback to Blob saving
                try {{
                    const blob = new Blob([`{escaped_csv_data}`], {{ type: 'text/csv;charset=utf-8' }});
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = 'bacnet_points.csv';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(link.href);
                }} catch (err) {{
                   // console.error('Fallback save method failed:', err);
                }}
            }}
        """
        return rx.call_script(js_code)

    # Resetting methods
    @rx.event
    def reset_point_table_filters(self):
        self.point_column_filter = BACnetPointColumnFilters()

    def get_absolute_index(self, relative_index: int) -> int:
        """
        Convert a relative index (page position) to an absolute index in the original points list.
        
        Args:
            relative_index: The index within the current page view
            
        Returns:
            The absolute index in the original points list
        """
        points_to_load = self.points_to_load
        
        if not points_to_load or relative_index >= len(points_to_load):
            return -1  # Invalid index
        
        # Get the original index stored in the tuple
        original_index, _ = points_to_load[relative_index]
        return original_index
    
    def apply_point_table_filters(self, filters: BACnetPointTableFilter) -> list[tuple[int, BACnetDevicePointModelView]]:
        """
        Apply filters to the data points and return filtered results with their original indices.
        
        Args:
            filters: BACnetPointTableFilter instance containing filter criteria
            
        Returns:
            List of tuples (original_index, point)
        """
        if self.selected_device is None:
            return []
        
        # Start with all points and their original indices
        points_with_indices = list(enumerate(self.selected_device.points))
        
        # Define a helper function to apply a single filter
        def apply_filter(points_with_indices, filter_value, column_enabled, attr_name):
            if filter_value == "" or not column_enabled:
                return points_with_indices
            
            return [
                (idx, point) for idx, point in points_with_indices 
                if filter_value.lower() in str(getattr(point, attr_name, "")).lower()
            ]
        
        # Apply each filter sequentially
        filter_specs = [
            (filters.volttron_point_name, self.point_column_filter.volttron_point_name, "volttron_point_name"),
            (filters.units, self.point_column_filter.units, "units"),
            (filters.object_type, self.point_column_filter.object_type, "object_type"),
            (filters.writable, self.point_column_filter.writable, "writable"),
            (filters.present_value, self.point_column_filter.present_value, "present_value"),
            (filters.index, self.point_column_filter.index, "index"),
            (filters.notes, self.point_column_filter.notes, "notes")
        ]
        
        # Apply each filter in sequence
        for filter_value, column_enabled, attr_name in filter_specs:
            points_with_indices = apply_filter(points_with_indices, filter_value, column_enabled, attr_name)
        
        return points_with_indices

    def _convert_selected_points_to_csv(self) -> str:
        """Convert selected_points to CSV string with mapped column names."""
        # Define the CSV columns and their mapping to model fields
        columns = [
            ("Point Name", "device_name"),
            ("VOLTTRON Point Name", "volttron_point_name"),
            ("Units", "units"),
            ("BACnet Object Type", "object_type"),
            ("Property", "present_value"),
            ("Writable", "writable"),
            ("Index", "index"),
            ("Notes", "notes"),
        ]
        fieldnames = [field for _, field in columns]
        header = [col for col, _ in columns]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)

        for point in self.selected_points:
            point_dict = point.dict() if hasattr(point, "dict") else point.__dict__
            row = []
            for header_cell, field in columns:
                if header_cell == "Property":
                    value = "presentValue"
                    row.append(value)
                    continue

                value = point_dict.get(field, "")
                if isinstance(value, bool):
                    value = "TRUE" if value else "FALSE"
                row.append(value)
            writer.writerow(row)

        csv_data = output.getvalue()
        output.close()
        return csv_data

    def _create_config_store_entry(self, path: str, csv_value: str, component_id: str) -> ConfigStoreEntryModelView:
        """Create a new ConfigStoreEntryModelView with the provided values."""
        new_entry = ConfigStoreEntryModelView(
            path=path,
            data_type="CSV",
            value=csv_value,
            component_id=component_id,
            safe_entry={
                "path": path,
                "data_type": "CSV",
                "value": csv_value,
            }
        )
        
        # Process CSV data
        usable_csv = csv_string_to_usable_dict(csv_value)
        new_entry.csv_variants["Custom"] = usable_csv
        new_entry.safe_entry = new_entry.dict()
        
        return new_entry
