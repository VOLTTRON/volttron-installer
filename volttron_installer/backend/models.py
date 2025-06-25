from typing import Any, Literal, List, Optional
from typing_extensions import Annotated
import logging

from pydantic import BaseModel, AfterValidator, ValidationError, Field, field_validator

from .validators import is_valid_field_name_for_config
import re

logger = logging.getLogger(__name__)

class HostEntry(BaseModel):
    """
    A `HostEntry` represents a single entry in the inventory.  It is a single
    VOLTTRON instance connection point.
    """
    id: str
    ansible_user: str
    ansible_host: str
    ansible_port: int = Field(default=22)
    ansible_connection: Literal["ssh", "local"] = "ssh"
    http_proxy: str | None = None
    https_proxy: str | None = None
    volttron_venv: str | None = None
    volttron_home: str = "~/.volttron"
    host_configs_dir: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "ansible_user": self.ansible_user,
            "ansible_host": self.ansible_host,
            "ansible_port": int(self.ansible_port),
            "ansible_connection": self.ansible_connection,
            "http_proxy": "" if self.http_proxy is None else self.http_proxy,
            "https_proxy": "" if self.https_proxy is None else self.https_proxy,
            "volttron_venv": "" if self.volttron_venv is None else self.volttron_venv,
            "volttron_home": self.volttron_home,
            "host_configs_dir": "" if self.host_configs_dir is None else self.host_configs_dir
        }

class ToolRequest(BaseModel):
    tool_name: str
    module_path: str
    use_poetry: bool = False

class ToolStatusResponse(BaseModel):
    tool_name: str
    tool_running: bool
    port: int

class ReachableResponse(BaseModel):
    reachable: bool = True

class CreateOrUpdateHostEntryRequest(HostEntry):
    """Request model for creating or updating a host entry"""
    pass

class RemoveHostEntryRequest(BaseModel):
    """Request model for removing a host entry"""
    id: str
    
class ConfigStoreEntry(BaseModel):
    """Represents an entry in the configuration store"""
    # path: Annotated[str, AfterValidator(is_valid_field_name_for_config)]
    path: str
    data_type: Literal["CSV", "JSON"] = "JSON"
    value: str = ""

    def to_dict(self)-> dict[str, str]:
        return {
            "path" : self.path,
            "data_type": self.data_type,
            "value": self.value
        }

class SuccessResponse(BaseModel):
    """Simple success response model"""
    success: bool = True
    object: BaseModel = None

class AgentDefinition(BaseModel):
    """Represents an agent definition with validation in model_post_init"""
    identity: str
    state: str = "present"
    running: bool = True
    enabled: bool = False
    tag: str | None = None
    pypi_package: str | None = None
    source: str | None = None
    config: str | None = None
    config_store: dict[str, ConfigStoreEntry] = {}
    config_store_allowed: bool = True

    def to_dict(self) -> dict[str, str]:
        return {
            "identity": self.identity,
            "config_store" : self.config_store
        }

    def model_post_init(self, __context):
        if self.pypi_package is None and self.source is None:
            logger.error(f"Agent {self.identity}: Neither pypi_package nor source is set")
            raise ValidationError("Either pypi_package or source must be set.")
        elif self.pypi_package is not None and self.source is not None:
            logger.error(f"Agent {self.identity}: Both pypi_package and source are set")
            raise ValidationError("Only one of pypi_package or source can be set.")
        logger.debug(f"Initialized agent definition for {self.identity}")

class CreateAgentRequest(BaseModel):
    """Request model for creating an agent"""
    identity: str
    source: str | None = None
    pypi_package: str | None = None
    config_store: dict[str, ConfigStoreEntry] = {}

    def model_post_init(self, __context):
        if self.pypi_package is None and self.source is None:
            logger.error(f"Agent {self.identity}: Neither pypi_package nor source is set")
            raise ValidationError("Either pypi_package or source must be set.")
        elif self.pypi_package is not None and self.source is not None:
            logger.error(f"Agent {self.identity}: Both pypi_package and source are set")
            raise ValidationError("Only one of pypi_package or source can be set.")
        logger.debug(f"Initialized agent creation request for {self.identity}")

class AgentType(BaseModel):
    """Represents a type of agent with default configurations"""
    identity: str
    default_config: dict | str
    default_config_store: dict[str, ConfigStoreEntry]
    source: str | None = None
    pypi_package: str | None = None
    config_store_allowed: bool = True

class AgentCatalog(BaseModel):
    """Catalog of default agents available with default configurations"""
    agents: dict[str, AgentType] = {
        "listener": AgentType(
            identity="listener",
            default_config={
                "agentid": "listener",
                "message": "Hello, World!",
                "log-level": "INFO"
            },
            default_config_store={},
            config_store_allowed=False,
            source="examples/ListenerAgent"
        ),
        "platform.driver": AgentType(
            identity="platform.driver",
            default_config={
                "driver_scrape_interval": 0.05,
                "publish_breadth_first_all": False,
                "publish_depth_first": False,
                "publish_breadth_first": False
            },
            default_config_store={
                "fake.csv": ConfigStoreEntry(
                    path="fake.csv",
                    data_type="CSV",
                    value="""Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes
Heartbeat,Heartbeat,On/Off,On/Off,TRUE,0,boolean,Point for heartbeat toggle
EKG,EKG,waveform,waveform,TRUE,1,float,Sine wave for baseline output
OutsideAirTemperature1,OutsideAirTemperature1,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm
SampleWritableFloat1,SampleWritableFloat1,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation
SampleLong1,SampleLong1,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
SampleWritableShort1,SampleWritableShort1,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
SampleBool1,SampleBool1,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1
SampleWritableBool1,SampleWritableBool1,On / Off,on/off,TRUE,TRUE,boolean,Status indicator
OutsideAirTemperature2,OutsideAirTemperature2,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm
SampleWritableFloat2,SampleWritableFloat2,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation
SampleLong2,SampleLong2,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
SampleWritableShort2,SampleWritableShort2,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
SampleBool2,SampleBool2,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1
SampleWritableBool2,SampleWritableBool2,On / Off,on/off,TRUE,TRUE,boolean,Status indicator
OutsideAirTemperature3,OutsideAirTemperature3,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm
SampleWritableFloat3,SampleWritableFloat3,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation
SampleLong3,SampleLong3,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
SampleWritableShort3,SampleWritableShort3,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
SampleBool3,SampleBool3,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1
SampleWritableBool3,SampleWritableBool3,On / Off,on/off,TRUE,TRUE,boolean,Status indicator
HPWH_Phy0_PowerState,PowerState,1/0,1/0,TRUE,0,int,Power on off status
ERWH_Phy0_ValveState,ValveState,1/0,1/0,TRUE,0,int,power on off status
EKG_Sin,EKG_Sin,1-0,SIN Wave,TRUE,0,float,SIN wave
EKG_Cos,EKG_Cos,1-0,COS Wave,TRUE,0,float,COS wave"""),
                "devices/fake/driver": ConfigStoreEntry(
                    path="fake.json",
                    data_type="JSON",
                    value="""{
                        "driver_config": {},
                        "registry_config":"config://fake.csv",
                        "interval": 5,
                        "timezone": "US/Pacific",
                        "heart_beat_point": "Heartbeat",
                        "driver_type": "fakedriver",
                        "publish_breadth_first_all": false,
                        "publish_depth_first": false,
                        "publish_breadth_first": false,
                        "campus": "campus",
                        "building": "building",
                        "unit": "fake_device"
                    }""")
            },
            source="services/core/PlatformDriverAgent"
        ),
        # Services/core agents
        # From this agent onward, im not entirely sure that any of these agents have 
        # a config store/default config store agent
        "platform.actuator": AgentType(
            identity="platform.actuator",
            default_config={
                "schedule_publish_interval": 30,
                "heartbeat_interval": 20,
                "preempt_grace_time": 30
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/PlatformActuator"
        ),
        "platform.bacnet_proxy": AgentType(
            identity="platform.bacnet_proxy",
            default_config={
                "device_address": "10.0.2.15",
                "max_apdu_length": 1024,
                "object_id": 599,
                "object_name": "Volttron BACnet driver",
                "vendor_id": 5,
                "segmentation_supported": "segmentedBoth"
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/BACnetProxyAgent"
        ),
        "data.mover": AgentType(
            identity="data.mover",
            default_config={
                "destination-vip": "tcp://127.0.0.1:22916",
                "destination-serverkey": "<valid server key>",
                "destination-historian-identity": "platform.historian"
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/DataMover"
        ),
        "dnp3-outstation-agent": AgentType(
            identity="dnp3_outstation_agent",
            default_config={
                "outstation_ip": "0.0.0.0",
                "port": 20000,
                "master_id": 2,
                "outstation_id": 1
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/DNP3OutstationAgent"
        ),
        "forward.historian": AgentType(
            identity="forward.historian",
            default_config={
                "destination-vip": "tcp://127.0.0.1:22916",
                "destination-serverkey": None
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/ForwardHistorian"
        ),
        # TODO: Agent type doesn't yet have the functionality to accept yaml configs as default configs. CSV Data table cant quite yet parse
        # these big csv fields; we need to create a "special field" within config store entry so we can check if we need every single field filled out. 
        # "2030_5.agent": AgentType(
        #     identity="2030_5.agent",
        #     default_config={
        #         "destination-vip": "tcp://127.0.0.1:22916",
        #         "destination-serverkey": "<valid server key>",
        #         "destination-historian-identity": "platform.historian"
        #     },
        #     default_config_store={
        #         "inverter1" : ConfigStoreEntry(
        #             path="inverter1",
        #             data_type="JSON",
        #             value=""""
        #             {
        #                 "driver_config": {},
        #                 "registry_config":"config://inverter1.points.csv",
        #                 "interval": 5,
        #                 "timezone": "US/Pacific",
        #                 "heart_beat_point": "Heartbeat",
        #                 "driver_type": "fakedriver",
        #                 "publish_breadth_first_all": false,
        #                 "publish_depth_first": false,
        #                 "publish_breadth_first": false,
        #                 "campus": "devices",
        #                 "building": "inverter1"
        #             }
        #             """
        #         ),
        #         "invert1.points.csv" : ConfigStoreEntry(
        #             path="inverter1.points.csv",
        #             data_type="CSV",
        #             value="""
        #                 Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes
        #                 Heartbeat,Heartbeat,On/Off,On/Off,TRUE,0,boolean,Point for heartbeat toggle
        #                 EKG1,BAT_SOC,waveform,waveform,TRUE,sin,float,Sine wave for baseline output
        #                 EKG2,INV_REAL_PWR,waveform,waveform,TRUE,cos,float,Sine wave
        #                 EKG3,INV_REACT_PWR,waveform,waveform,TRUE,tan,float,Cosine wave
        #                 SampleBool3,energized,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1
        #                 SampleWritableBool3,connected,On / Off,on/off,TRUE,TRUE,boolean,Status indicator
        #                 SampleLong3,INV_OP_STATUS_MODE,Enumeration,1-4,FALSE,3,int,Mode of Inverter
        #                 ctrl_freq_max,ctrl_freq_max,,,TRUE,,int,
        #                 ctrl_volt_max,ctrl_volt_max,,,TRUE,,int,
        #                 ctrl_freq_min,ctrl_freq_min,,,TRUE,,int,
        #                 ctrl_volt_min,ctrl_volt_min,,,TRUE,,int,
        #                 ctrl_ramp_tms,ctrl_ramp_tms,,,TRUE,,int,
        #                 ctrl_rand_delay,ctrl_rand_delay,,,TRUE,,int,
        #                 ctrl_grad_w,ctrl_grad_w,,,TRUE,,int,
        #                 ctrl_soft_grad_w,ctrl_soft_grad_w,,,TRUE,,int,
        #                 ctrl_connected,ctrl_connected,,,TRUE,,boolean,
        #                 ctrl_energized,ctrl_energized,,,TRUE,,boolean,
        #                 ctrl_fixed_pf_absorb_w,ctrl_fixed_pf_absorb_w,,,TRUE,,int,
        #                 ctrl_fixed_pf_ingect_w,ctrl_fixed_pf_ingect_w,,,TRUE,,int,
        #                 ctrl_fixed_var,ctrl_fixed_var,,,TRUE,,int,
        #                 ctrl_fixed_w,ctrl_fixed_w,,,TRUE,,int,
        #                 ctrl_es_delay,ctrl_es_delay,,,TRUE,,int,
        #             """
        #         ),
        #         "inverter_sample.csv" : ConfigStoreEntry(
        #             path="inverter_sample.csv",
        #             data_type="CSV",
        #             value="""
        #                 Point Name,Description,Multiplier,MRID,Offset,Parameter Type,Notes
        #                 ,,,,,DERCapability::rtgMaxW,DERCapabilities are not generally writable but the corresponding setting is.
        #                 ,,,,,DERCapability::rtgOverExcitedW,
        #                 ,,,,,DERCapability::rtgOverExcitedPF,
        #                 ,,,,,DERCapability::rtgUnderExcitedW,
        #                 ,,,,,DERCapability::rtgUnderExcitedPF,
        #                 ,,,,,DERCapability::rtgMaxVA,
        #                 ,,,,,DERCapability::rtgNormalCategory,
        #                 ,,,,,DERCapability::rtgAbnormalCategory,
        #                 ,,,,,DERCapability::rtgMaxVar,
        #                 ,,,,,DERCapability::rtgMaxVarNeg,
        #                 ,,,,,DERCapability::rtgMaxChargeRateW,
        #                 ,,,,,DERCapability::rtgMaxChargeRateVA,
        #                 ,,,,,DERCapability::rtgVNom,
        #                 ,,,,,DERCapability::rtgMaxV,
        #                 ,,,,,DERCapability::rtgMinV,
        #                 ,,,,,DERCapability::modesSupported,
        #                 ,,,,,DERCapability::rtgReactiveSusceptance,
        #                 ,,,,,DERStatus::alarmStatus,"Bitmap Position (0 = over current, 1 over voltage, 2 under voltage, 3 over frequency, 4 under frequency, 5 voltage imbalance, 6 current imbalance, 7 emergency local, 8 emergency remote, 9 low power input, 10 phase rotation)"
        #                 ,,,,,DERStatus::genConnectStatus,"DER Generator Status (0 = Connected, 1 = Available, 2 = Operating, 3 = Test, 4 = Fault/Error)"
        #                 ,,,,,DERStatus::inverterStatus,"DER Inverter Status (0 = Connected, 1 = Available, 2 = Operating, 3 = Test, 4 = Fault/Error)"
        #                 ,,,,,DERStatus::localControlModeStatus,0 = local control 1 = remote control
        #                 ,,,,,DERStatus::manufacturerStatus,A manufacturer status code string
        #                 ,,,,,DERStatus::operationalModeStatus,"DER OperationalModeStatus (0 = Not applicable, 1 = Off, 2 = Operational, 3 = Test)"
        #                 BAT_SOC,,,,,DERStatus::stateOfChargeStatus,DER StateOfChargeStatus % of charge
        #                 ,,,,,DERStatus::storageModeStatus,"DER StorageModeStatus (0 = Charging, 1 = Discharging, 2 = Holding)"
        #                 ,,,,,DERStatus::storConnectStatus,"DER Storage Status (0 = Connected, 1 = Available, 2 = Operating, 3 = Test, 4 = Fault/Error)"
        #                 ,,,,,DERSettings::setESHighVolt,
        #                 ,,,,,DERSettings::setESLowVolt,
        #                 ,,,,,DERSettings::setESHighFreq,
        #                 ,,,,,DERSettings::setESLowFreq,
        #                 ,,,,,DERSettings::setESDelay,
        #                 ,,,,,DERSettings::setESRandomDelay,
        #                 ,,,,,DERSettings::setESRampTms,
        #                 ctrl_es_delay,,,,,DefaultDERControl::setESDelay,
        #                 ctrl_freq_max,,,,,DefaultDERControl::setESHighFreq,
        #                 ctrl_volt_max,,,,,DefaultDERControl::setESHighVolt,
        #                 ctrl_freq_min,,,,,DefaultDERControl::setESLowFreq,
        #                 ctrl_volt_min,,,,,DefaultDERControl::setESLowVolt,
        #                 ctrl_ramp_tms,,,,,DefaultDERControl::setESRampTms,
        #                 ctrl_rand_delay,,,,,DefaultDERControl::setESRandomDelay,
        #                 ctrl_grad_w,,,,,DefaultDERControl::setGradW,
        #                 ctrl_soft_grad_w,,,,,DefaultDERControl::setSoftGradW,
        #                 ctrl_connected,,,,,DERControlBase::opModConnect,"True/False Connected = True, Disconnected = False"
        #                 ctrl_energized,,,,,DERControlBase::opModEnergize,"True/False Energized = True, De-Energized = False"
        #                 ctrl_fixed_pf_absorb_w,,,,,DERControlBase::opModFixedPFAbsorbW,
        #                 ctrl_fixed_pf_ingect_w,,,,,DERControlBase::opModFixedPFInjectW,
        #                 ctrl_fixed_var,,,,,DERControlBase::opModFixedVar,
        #                 ctrl_fixed_w,,,,,DERControlBase::opModFixedW,
        #                 ctrl_freq_droop,,,,,DERControlBase::opModFreqDroop,
        #                 ctrl_freq_w,,,,,DERControlBase::opModFreqWatt,
        #                 ,,,,,DERControlBase::opModHFRTMayTrip,
        #                 ,,,,,DERControlBase::opModHFRTMustTrip,
        #                 ,,,,,DERControlBase::opModHVRTMomentaryCessation,
        #                 ,,,,,DERControlBase::opModHVRTMustTrip,
        #                 ,,,,,DERControlBase::opModLFRTMayTrip,
        #                 ,,,,,DERControlBase::opModLVRTMomentaryCessation,
        #                 ,,,,,DERControlBase::opModLVRTMustTrip,
        #                 ctrl_max_w,,,,,DERControlBase::opModMaxLimW,
        #                 ctrl_target_var,,,,,DERControlBase::opModTargetVar,
        #                 ctrl_target_w,Target Real Power,,,,DERControlBase::opModTargetW,
        #                 ,,,,,DERControlBase::opModVoltVar,
        #                 ,,,,,DERControlBase:opModVoltWatt,
        #                 ,,,,,DERControlBase::opModWattPF,
        #                 ,,,,,DERControlBase::opModWattVar,
        #                 ,,,,,DERControlBase::rampTms,
        #             """
        #         )
        #     },
        #     config_store_allowed=True,
        #     source="services/core/IEEE_2030_5"
        # ),
        "mqtt.historian": AgentType(
            identity="mqtt.historian",
            default_config={
                "connection": {
                    "mqtt_hostname": "localhost",
                    "mqtt_port": 1883
                }
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/MQTTHistorian"
        ),
        "platform.tagging_service": AgentType(
            identity="platform.tagging_service",
            default_config={
                "connection": {
                    "type": "mongodb",
                    "params": {
                        "host": "localhost",
                        "port": 27017,
                        "database": "mongo_test",
                        "user": "test",
                        "passwd": "test"
                    }
                },
                "table_prefix":"volttron",
                "historian_vip_identity":"platform.historian"
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/MongodbTaggingService"
        ),
        "platform.openadr.ven": AgentType(
            identity="platform.openadr.ven",
            default_config={
                "ven_name": "PNNLVEN",
                "vtn_url": "https://eiss2demo.ipkeys.com/oadr2/OpenADR2/Simple/2.0b",
                "debug": True,
                "disable_signature": True,
                "cert_path": "~/.ssh/secret/TEST_RSA_VEN_221206215541_cert.pem",
                "key_path": "~/.ssh/secret/TEST_RSA_VEN_221206215541_privkey.pem"
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/OpenADRVenAgent"
        ),
        "platform.aggregate_historian": AgentType(
            identity="platform.aggregate_historian",
            default_config={
                "connection": {
                    "type": "sqlite",
                    "params": {
                        "database": "test.sqlite",
                        "timeout": 15
                    }
                },
                "aggregations":[
                    {
                    "aggregation_period": "1m",
                    "use_calendar_time_periods": True,
                    "points": [
                            {
                            "topic_names": ["device1/out_temp"],
                            "aggregation_type": "sum",
                            "min_count": 2
                            },
                            {
                            "topic_names": ["device1/in_temp"],
                            "aggregation_type": "sum",
                            "min_count": 2
                            }
                        ]
                    },
                    {
                        "aggregation_period": "2m",
                        "use_calendar_time_periods": False,
                        "points": [
                            {"topic_names": ["device1/out_temp"],
                            "aggregation_type": "sum", "min_count": 2},
                            {"topic_names": ["device1/in_temp"],
                            "aggregation_type": "sum", "min_count": 2}
                        ]
                    }
                ]
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/SQLAggregateHistorian"
        ),
        "platform.historian": AgentType(
            identity="platform.historian",
            default_config={
                "connection": {
                    "type": "mysql",
                    "params": {
                        "host": "localhost",
                        "port": 3306,
                        "database": "test_historian",
                        "user": "historian",
                        "passwd": "historian"
                    }
                }
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/SQLHistorian"
        ),
        "sqlite.tagging_service": AgentType(
            identity="sqlite.tagging_service",
            default_config={
                # sqlite connection parameters
                "connection": {
                    "type": "sqlite",
                    "params": {
                        "database": "~/.volttron/data/volttron.tags.sqlite"
                    }
                },
                # optional. Specify if collections created for tagging should have names
                # starting with a specific prefix <given prefix>_<collection_name>
                "table_prefix":"volttron",

                # optional. Specify if you want tagging service to query the historian
                # with this vip identity. defaults to platform.historian
                "historian_vip_identity": "crate.historian"
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/SQLiteTaggingService"
        ),
        "volttron.central": AgentType(
            identity="volttron.central",
            default_config={},
            default_config_store={},
            config_store_allowed=True,
            source="services/core/VolttronCentral"
        ),
        "platform.agent": AgentType(
            identity="platform.agent",
            default_config={
                "volttron-central-address": "http://ip<host>:port `or` tcp://ip:port",
                "volttron-central-serverkey": "VC agent's instance serverkey",
                "volttron-central-reconnect-interval": 5,
                "instance-name": "name of instances (VC agent's instance ip address as default)",
                "stats-publish-interval": 30,
                "topic-replace-map": {
                    "from": "to",
                    "from1": "to1"
                }
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/VolttronCentralPlatform"
        ),
        "weatheragent": AgentType(
            identity="weatheragent",
            default_config={
                "database_file": "weather.sqlite",
                "max_size_gb": 1,
                "poll_locations": [{"station": "KLAX"}, {"station": "KPHX"}],
                "poll_interval": 60
            },
            default_config_store={},
            config_store_allowed=True,
            source="services/core/WeatherDotGov"
        ),
        # services/ops agents
        "watcheragent": AgentType(
            identity="watcheragent",
            default_config={
                "watchlist": [
                    "platform.driver",
                    "platform.actuator"
                ],
                "check-period": 10
            },
            default_config_store={},
            config_store_allowed=False,
            source="services/ops/AgentWatcher"
        ),
        "emaileragent": AgentType(
            identity="emaileragent",
            default_config={
                "smtp-address": "<smtp-address>",
                "smtp-username":"<smtp-username>",
                "smtp-password":"<smtp-password>",
                "smtp-port":"<smtp-port>",
                "smtp-tls":"<true/false>",
                "from-address": "foo@foo.com",
                "to-addresses": [
                    "foo1@foo.com",
                    "foo2@foo.com"
                ],

                # Only send a certain alert-key message every 120 minutes.
                "allow-frequency-minutes": 120
            },
            default_config_store={},
            config_store_allowed=False,
            source="services/ops/EmailerAgent"
        ),
        "platform.filewatchpublisher": AgentType(
            identity="platform.filewatchpublisher",
            default_config={
                "files": [
                    {
                        "file": "/opt/myservice/logs/myservice.log",
                        "topic": "record/myservice/logs"
                    },
                    {
                        "file": "/home/volttron/tempfile.txt",
                        "topic": "temp/filepublisher"
                    }
                ]
            },
            default_config_store={},
            config_store_allowed=False,
            source="services/ops/FileWatchPublisher"
        ),
        "platform.logstatisticsagent": AgentType(
            identity="platform.logstatisticsagent",
            default_config={
                "file_path" : "~/volttron/volttron.log",
                "analysis_interval_sec" : 60,
                "publish_topic" : "platform/log_statistics",
                "historian_topic" : "analysis/log_statistics"
            },
            default_config_store={},
            config_store_allowed=False,
            source="services/ops/LogStatisticsAgent"
        ),
        "platform.sysmon": AgentType(
            identity="platform.sysmon",
            default_config={
                "base_topic": "datalogger/log/platform",
                "cpu_check_interval": 5,
                "memory_check_interval": 5,
                "disk_check_interval": 5,
                "disk_path": "/"
            },
            default_config_store={},
            config_store_allowed=False,
            source="services/ops/SysMonAgent"
        ),
        "platform.thresholddetection": AgentType(
            identity="platform.thresholddetection",
            default_config={
                "datalogger/log/platform/cpu_percent": {
                "threshold_max": 99
                },

                "datalogger/log/platform/memory_percent": {
                "threshold_max": 99
                },

                "datalogger/log/platform/disk_percent": {
                "threshold_max": 97
                },

                "devices/some/device/all": {
                    "point0": {
                        "threshold_max": 10,
                        "threshold_min": 0
                    },
                    "point1": {
                        "threshold_max": 42
                    }
                }
            },
            default_config_store={},
            config_store_allowed=False,
            source="services/ops/ThresholdDetectionAgent"
        ),
        "platform.thresholddetection": AgentType(
            identity="platform.thresholddetection",
            default_config={
                "publish-settings":
                {
                    "publish-local": False,
                    "publish-remote": True,
                    "remote":
                    {
                        "serverkey": "Olx7Y7XZvSGmHDppsQKvG7BucOH8vgkRlQGZzzh5nHs",
                        "vip-address": "tcp://127.0.0.1:23916",
                        "identity": "remote.topic_watcher"
                    }
                },
                "group1": {
                    "devices/fakedriver0/all": 10
                },

                "device_group": {
                    "devices/fakedriver1/all": {
                        "seconds": 10,
                        "points": ["temperature", "PowerState"]
                    }
                }
            },
            default_config_store={},
            config_store_allowed=False,
            source="services/ops/TopicWatcher"
        ),
    }

    def get_agent(self, identity: str) -> Optional[AgentType]:
        return self.agents.get(identity)

class KeyValuePair(BaseModel):
    key: str
    value: float | int | str


class PlatformConfig(BaseModel):
    """Represents the platform configuration"""
    instance_name: str = "volttron1"
    vip_address: str = "tcp://127.0.0.1:22916"
    message_bus: Literal["zmq"] = "zmq"
    options: list[KeyValuePair] = []

    @field_validator('vip_address')
    def validate_vip_address(cls, v):
        if not re.match(r'^tcp://[\d.]+:\d+$', v):
            raise ValueError("vip_address must be in the format tcp://<ip>:<port>")
        return v

    @field_validator('instance_name')
    def validate_instance_name(cls, v):
        if not re.match(r'^[\w-]+$', v):
            raise ValueError("instance_name must contain only letters, numbers, hyphens, and underscores")
        return v

    

class PlatformDefinition(BaseModel):
    """
    Represents the platform definition with methods to add configuration items.
    
    Attributes:
        host_id (str): A reference to the `id` field of a `HostEntry` instance, 
                       representing a unique VOLTTRON instance connection point.
        config (PlatformConfig): The configuration specific to the platform.
        agents (dict[str, AgentDefinition]): A dictionary mapping agent names 
                                             to their definitions.
    """
    host_id: str
    config: PlatformConfig = PlatformConfig()
    agents: dict[str, AgentDefinition] = {}

    def __getitem__(self, item):
        return self.config[item]

class CreatePlatformRequest(PlatformDefinition):
    """Request model for creating a platform"""
    pass

class AgentStatus(BaseModel):
    """Represents the state of an agent"""
    identity: str
    state: Literal["not deployed", "deployed", "started", "stopped"] = "not deployed"
    
class PlatformDeploymentStatus(BaseModel):
    """Represents the state of a platform deployment"""
    platform_id: str
    host_configured: bool = False
    keys_verified: bool = False
    state: Literal["not deployed", "deployed", "running"] = "not deployed"
    agents: dict[str, AgentStatus] = {}

class DeployPlatformRequest(BaseModel):
    """Request model for deploying a platform"""
    platform_id: str

class PlatformDeplymentStatusRequest(BaseModel):
    """Request model for getting the state of a platform deployment"""
    platform_id: str

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
