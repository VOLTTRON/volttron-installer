"""Driver library data models and catalog."""

from pydantic import BaseModel


class DriverLibrary(BaseModel):
    """Represents an installable driver library for the platform driver."""
    name: str  # Display name
    pip_package: str  # pip package name
    driver_type: str  # driver_type value used in device configs
    description: str
    default_registry_csv: str = ""  # Template registry CSV content
    default_device_config: str = "{}"  # Template driver_config JSON
    required_agents: list[str] = []  # Supporting agents required by this driver
    driver_config_fields: list[dict[str, str | bool]] = []  # UI field metadata


_FAKE_REGISTRY_CSV = """Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes
EKG,EKG,waveform,,TRUE,sin,float,Sine wave
Heartbeat,Heartbeat,On/Off,On/Off,TRUE,0,boolean,Point for heartbeat toggle
OutsideAirTemperature1,OutsideAirTemperature1,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.00
SampleWritableFloat1,SampleWritableFloat1,PPM,1000.00 (default),TRUE,10,float,Setpoint
SampleLong1,SampleLong1,Enumeration,1 through 13,FALSE,50,int,Status indicator
SampleWritableShort1,SampleWritableShort1,%,0.00 to 100.00 (75 default),TRUE,20,int,Command
SampleBool1,SampleBool1,On / Off,on/off,FALSE,TRUE,boolean,Status
SampleWritableBool1,SampleWritableBool1,On / Off,on/off,TRUE,TRUE,boolean,Command"""

_BACNET_REGISTRY_CSV = """Point Name,Volttron Point Name,Units,Unit Details,BACnet Object Type,Property,Writable,Index,Notes
SupplyFanStatus,SupplyFanStatus,On/Off,on/off,binaryValue,presentValue,FALSE,,Status
ReturnFanStatus,ReturnFanStatus,On/Off,on/off,binaryValue,presentValue,FALSE,,Status
OutsideAirTemperature,OutsideAirTemperature,degreesFahrenheit,-100 to 300,analogInput,presentValue,FALSE,,Reading"""

_MODBUS_REGISTRY_CSV = """Point Name,Volttron Point Name,Units,Writable,Default Value,Transform,Table,Register Address,Type
SampleAnalog,SampleAnalog,units,TRUE,0,,HoldingRegister,0,float
SampleBool,SampleBool,bool,TRUE,FALSE,,CoilRegister,0,bool"""

_DNP3_REGISTRY_CSV = """Point Name,Volttron Point Name,Units,Writable,Group,Variation,Index,Type,Notes
BinaryInputStatus,BinaryInputStatus,,FALSE,1,2,0,bool,
AnalogInputValue,AnalogInputValue,,FALSE,30,1,0,float,
AnalogOutputSetpoint,AnalogOutputSetpoint,,TRUE,40,4,0,float,"""

_HOMEASSISTANT_REGISTRY_CSV = """Point Name,Volttron Point Name,Entity ID,Attribute,Writable,Type,Notes
LivingRoomTemperature,LivingRoomTemperature,sensor.living_room_temperature,state,FALSE,float,
LivingRoomHumidity,LivingRoomHumidity,sensor.living_room_humidity,state,FALSE,float,
MainThermostatSetpoint,MainThermostatSetpoint,climate.main_thermostat,temperature,TRUE,float,"""


class DriverLibraryCatalog(BaseModel):
    """Hardcoded catalog of available driver libraries."""
    drivers: list[DriverLibrary] = [
        DriverLibrary(
            name="Fake Driver",
            pip_package="volttron-lib-fake-driver",
            driver_type="fake",
            description="Simulated driver for testing — generates sample data points",
            default_registry_csv=_FAKE_REGISTRY_CSV,
            default_device_config='{}',
            driver_config_fields=[],
        ),
        DriverLibrary(
            name="BACnet Driver",
            pip_package="volttron-lib-bacnet-driver",
            driver_type="bacnet",
            description="BACnet protocol driver for building automation devices",
            default_registry_csv="""Point Name,Volttron Point Name,Units,Unit Details,BACnet Object Type,Property,Writable,Index,Write Priority,Array Index,COV Flag,Notes
OutsideAirTemperature,OutsideAirTemperature,degreesFahrenheit,-50 to 250,analogInput,presentValue,FALSE,3000741,,,Primary CHW Return Temp
ReturnWaterTemperature,ReturnWaterTemperature,degreesFahrenheit,-50 to 250,analogInput,presentValue,FALSE,3000744,,,CHW Flow
SupplyFanEnable,SupplyFanEnable,On/Off,on/off,binaryOutput,presentValue,TRUE,10010,8,,TRUE,Writable fan enable""",
            default_device_config='{"device_address": "10.0.0.1", "device_id": 1000, "proxy_address": "platform.bacnet_proxy", "max_per_request": 24, "min_priority": 8, "use_read_multiple": true, "timeout": 30.0, "cov_lifetime": 180, "ping_retry_interval": 5.0}',
            required_agents=["platform.bacnet_proxy"],
            driver_config_fields=[
                {"key": "device_address", "label": "Device Address", "type": "text", "required": True, "placeholder": "10.0.0.1", "description": "Network address used by the BACnet driver."},
                {"key": "device_id", "label": "Device ID", "type": "number", "required": True, "placeholder": "1000", "description": "BACnet device instance number."},
                {"key": "proxy_address", "label": "BACnet Proxy Identity", "type": "text", "required": False, "placeholder": "platform.bacnet_proxy", "description": "VIP identity of the BACnet proxy agent."},
                {"key": "max_per_request", "label": "Max Points Per Request", "type": "number", "required": False, "placeholder": "24", "description": "Maximum points read in each request."},
                {"key": "min_priority", "label": "Minimum Write Priority", "type": "number", "required": False, "placeholder": "8", "description": "Lowest allowed write priority."},
                {"key": "use_read_multiple", "label": "Use Read Multiple", "type": "checkbox", "required": False, "description": "Enable BACnet ReadPropertyMultiple optimization."},
                {"key": "timeout", "label": "Timeout (seconds)", "type": "float", "required": False, "placeholder": "30", "description": "RPC timeout for BACnet operations."},
                {"key": "cov_lifetime", "label": "COV Lifetime (seconds)", "type": "number", "required": False, "placeholder": "180", "description": "Lifetime for COV subscriptions."},
                {"key": "ping_retry_interval", "label": "Ping Retry Interval (seconds)", "type": "float", "required": False, "placeholder": "5", "description": "Interval before retrying an unreachable device."},
            ],
        ),
        DriverLibrary(
            name="Modbus TK Driver",
            pip_package="volttron-lib-modbustk-driver",
            driver_type="modbus",
            description="Modbus driver using the MinimalModbus/ModbusTK library",
            default_registry_csv=_MODBUS_REGISTRY_CSV,
            default_device_config='{"device_address": "10.0.0.1", "port": 502, "slave_id": 1}',
            driver_config_fields=[
                {"key": "device_address", "label": "Device Address", "type": "text", "required": True, "placeholder": "10.0.0.1", "description": "IP address or hostname for the Modbus device."},
                {"key": "port", "label": "Port", "type": "number", "required": False, "placeholder": "502", "description": "TCP port for Modbus communications."},
                {"key": "slave_id", "label": "Slave ID", "type": "number", "required": True, "placeholder": "1", "description": "Modbus slave/unit identifier."},
            ],
        ),
        DriverLibrary(
            name="Modbus Driver",
            pip_package="volttron-lib-modbus-driver",
            driver_type="modbus",
            description="Modbus driver using pymodbus",
            default_registry_csv=_MODBUS_REGISTRY_CSV,
            default_device_config='{"device_address": "10.0.0.1", "port": 502, "slave_id": 1}',
            driver_config_fields=[
                {"key": "device_address", "label": "Device Address", "type": "text", "required": True, "placeholder": "10.0.0.1", "description": "IP address or hostname for the Modbus device."},
                {"key": "port", "label": "Port", "type": "number", "required": False, "placeholder": "502", "description": "TCP port for Modbus communications."},
                {"key": "slave_id", "label": "Slave ID", "type": "number", "required": True, "placeholder": "1", "description": "Modbus slave/unit identifier."},
            ],
        ),
        DriverLibrary(
            name="DNP3 Driver",
            pip_package="volttron-lib-dnp3-driver",
            driver_type="dnp3",
            description="DNP3 protocol driver for SCADA and utility devices",
            default_registry_csv=_DNP3_REGISTRY_CSV,
            default_device_config='{"device_address": "127.0.0.1", "port": 20000, "outstation_id": 1, "master_id": 2}',
            driver_config_fields=[
                {"key": "device_address", "label": "Outstation Address", "type": "text", "required": True, "placeholder": "127.0.0.1", "description": "IP address or hostname of the DNP3 outstation."},
                {"key": "port", "label": "Port", "type": "number", "required": False, "placeholder": "20000", "description": "TCP port for DNP3 communications."},
                {"key": "outstation_id", "label": "Outstation ID", "type": "number", "required": True, "placeholder": "1", "description": "Remote DNP3 outstation ID."},
                {"key": "master_id", "label": "Master ID", "type": "number", "required": True, "placeholder": "2", "description": "Local DNP3 master ID."},
            ],
        ),
        DriverLibrary(
            name="Home Assistant Driver",
            pip_package="volttron-lib-homeassistant-driver",
            driver_type="homeassistant",
            description="Driver for Home Assistant smart home devices (installed from GitHub source)",
            default_registry_csv=_HOMEASSISTANT_REGISTRY_CSV,
            default_device_config='{"url": "http://localhost:8123", "access_token": "YOUR_LONG_LIVED_TOKEN", "verify_ssl": true, "request_timeout": 15}',
            driver_config_fields=[
                {"key": "url", "label": "Home Assistant URL", "type": "text", "required": True, "placeholder": "http://localhost:8123", "description": "Base URL for your Home Assistant instance."},
                {"key": "access_token", "label": "Access Token", "type": "password", "required": True, "placeholder": "YOUR_LONG_LIVED_TOKEN", "description": "Home Assistant long-lived access token."},
                {"key": "verify_ssl", "label": "Verify SSL", "type": "checkbox", "required": False, "description": "Verify TLS certificates when connecting to Home Assistant."},
                {"key": "request_timeout", "label": "Request Timeout (seconds)", "type": "number", "required": False, "placeholder": "15", "description": "Timeout for Home Assistant API requests."},
            ],
        ),
    ]