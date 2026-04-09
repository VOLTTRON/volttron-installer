"""Agent catalog with default agent configurations."""

from typing import Optional
from pydantic import BaseModel

from .agent import AgentType
from .tool import ConfigStoreEntry


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
            source="volttron-listener",
            monolithic_source="examples/ListenerAgent"
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
            source="volttron-platform-driver",
            monolithic_source="services/core/PlatformDriverAgent"
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
            source="volttron-platform-actuator",
            monolithic_source="services/core/ActuatorAgent"
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
            source="volttron-bacnet-proxy",
            monolithic_source="services/core/BACnetProxy"
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
            source="volttron-data-mover",
            monolithic_source="services/core/DataMover"
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
            source="volttron-dnp3-outstation",
            monolithic_source="services/core/DNP3OutstationAgent"
        ),
        "forward.historian": AgentType(
            identity="forward.historian",
            default_config={
                "destination-vip": "tcp://127.0.0.1:22916",
                "destination-serverkey": None
            },
            default_config_store={},
            config_store_allowed=True,
            source="volttron-forward-historian",
            monolithic_source="services/core/ForwardHistorian"
        ),
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

    @property
    def modular_agents(self) -> dict[str, "AgentType"]:
        """Return only agents with a proper modular VOLTTRON pip package source."""
        return {
            k: v for k, v in self.agents.items()
            if v.source and v.source.startswith("volttron-")
        }


class GitHubAgentsResponse(BaseModel):
    """Response model for the GitHub agent catalog endpoint."""
    agents: list[AgentType]
    offline: bool = False  # True when GitHub was unreachable and fallback catalog is returned