from enum import Enum

import json
# Create Enum's for each attribute of agent with defaults (used for easy mapping and data modification)
class AgentName(Enum):
    """Enum of Agent Names"""

    NAME_ACTUATOR = "Actuator Agent"
    NAME_BACNET = "BACnet Proxy"
    NAME_DATA_MOVER = "Data Mover"
    NAME_DNP3 = "DNP3 Agent"
    NAME_FORWARD_HIST = "Forward Historian"
    NAME_IEEE = "IEEE 2030.5 Agent"
    NAME_MONGODB_TAGGING = "MongoDB Tagging Service"
    NAME_MQTT_HIST = "MQTT Historian"
    NAME_OPENADR_VEN = "OpenADR VEN Agent"
    NAME_PLATFORM_DRIVER = "Platform Driver Agent"
    NAME_SQL_AGG_HIST = "SQL Aggregate Historian"
    NAME_SQL_HIST = "SQL Historian"
    NAME_SQLITE_TAGGING = "SQLite Tagging Service"
    NAME_VOLTTRON_CENTRAL = "VOLTTRON Central"
    NAME_VOLTTRON_CENTRAL_PLATFORM = "VOLTTRON Central Platform"
    NAME_WEATHER_DOT_GOV = "Weather Dot Gov"

class AgentIdentity(Enum):
    """Enum of Agent Identities"""

    ID_ACTUATOR = "platform.actuator"
    ID_BACNET = "platform.bacnet_proxy"
    ID_DATA_MOVER = "platform.datamover"
    ID_DNP3 = "platform.dnp3"
    ID_FORWARD_HIST = "platform.forward"
    ID_IEEE = "IEEE2030_5agent"
    ID_MONGODB_TAGGING = "platform.mongodb"
    ID_MQTT_HIST = "platform.mqtt"
    ID_OPENADR_VEN = "platform.openadr"
    ID_PLATFORM_DRIVER = "platform.driver"
    ID_SQL_AGG_HIST = "platform.sqlagg"
    ID_SQL_HIST = "platform.sql"
    ID_SQLITE_TAGGING = "platform.sqlite"
    ID_VOLTTRON_CENTRAL = "volttron.central"
    ID_VOLTTRON_CENTRAL_PLATFORM = "platform.agent"
    ID_WEATHER_DOT_GOV = "platform.weatherdotgov"

SOURCE_PATH = "$VOLTTRON_ROOT/services/core/"
class AgentSource(Enum):
    """Enum of Agent Sources"""

    SOURCE_ACTUATOR = SOURCE_PATH + "ActuatorAgent"
    SOURCE_BACNET = SOURCE_PATH + "BACnetProxy"
    SOURCE_DATAMOVER = SOURCE_PATH + "DataMover"
    SOURCE_DNP3 = SOURCE_PATH + "DNP3Agent"
    SOURCE_FORWARDHIST = SOURCE_PATH + "ForwardHistorian"
    SOURCE_IEEE = SOURCE_PATH + "IEEE2030_5Agent"
    SOURCE_MONGODB = SOURCE_PATH + "MongodbTaggingService"
    SOURCE_MQTTHIST = SOURCE_PATH + "MQTTHistorian"
    SOURCE_OPENADR = SOURCE_PATH + "OpenADRVenAgent"
    SOURCE_PLATFORMDRIVER = SOURCE_PATH + "PlatformDriverAgent"
    SOURCE_SQLAGG = SOURCE_PATH + "SQLAggregateHistorian"
    SOURCE_SQL = SOURCE_PATH + "SQLHistorian"
    SOURCE_SQLITE = SOURCE_PATH + "SQLiteTaggingService"
    SOURCE_VC = SOURCE_PATH + "VolttronCentral"
    SOURCE_VCPLATFORM = SOURCE_PATH + "VolttronCentralPlatform"
    SOURCE_WEATHERDOTGOV = SOURCE_PATH + "WeatherDotGov"

class AgentConfig(Enum):
    """Enum of Agent Configs"""

    CONFIG_ACTUATOR = {
        "schedule_publish_interval": 30,
        "schedule_state_file": "actuator_state.pickle",
    }
    CONFIG_BACNET = {
        "device_address": "10.0.2.15",  # Need to pull ip of host computer
        "max_apdu_length": 1024,
        "object_id": 599,
        "object_name": "Volttron BACnet driver",
        "vendor_id": 15,
        "segmentation_supported": "segmentedBoth",
    }
    CONFIG_DATAMOVER = {
        "destination-serverkey": None,
        "destination-vip": "tcp://127.0.0.1:23916",
        "destination-historian-identity": "platform.historian",
        "remote-identity": "22916.datamover",
    }
    CONFIG_DNP3 = {
        "points": "config://mesa_points.config",
        "point_topic": "dnp3/point",
        "outstation_status_topic": "dnp3/outstation_status",
        "outstation_config": {"database_sizes": 10000, "log_levels": ["NORMAL"]},
        "local_ip": "0.0.0.0",
        "port": 20000,
    }
    CONFIG_FORWARDHIST = {
        "destination-serverkey": None,
        "destination-vip": "tcp://127.0.0.1:22916",
        "required_target_agents": [],
        "capture_device_data": True,
        "capture_analysis_data": True,
        "capture_log_data": True,
        "capture_record_data": True,
        "custom_topic_list": ["actuator", "alert"],
        "cache_only": False,
        "message_publish_count": 10000,
    }
    CONFIG_IEEE = {
        "devices": [
            {
                "sfdi": "097935300833",
                "lfdi": "247bd68e3378fe57ba604e3c8bdf9e3f78a3d743",
                "load_shed_device_category": "0200",
                "pin_code": "130178",
            },
            {
                "sfdi": "111576577659",
                "lfdi": "2990c58a59935a7d5838c952b1a453c967341a07",
                "load_shed_device_category": "0200",
                "pin_code": "130178",
            },
        ],
        "IEEE2030_5_server_sfdi": "413707194130",
        "IEEE2030_5_server_lfdi": "29834592834729384728374562039847629",
        "load_shed_device_category": "0020",
        "timezone": "America/Los_Angeles",
    }
    CONFIG_MONGODB = {
        "connection": {
            "type": "mongodb",
            "params": {
                "host": "localhost",
                "port": 27017,
                "database": "mongo_test",
                "user": "test",
                "passwd": "test",
            },
        }
    }
    CONFIG_MQTTHIST = {"connection": {"mqtt_hostname": "localhost", "mqtt_port": 1883}}
    CONFIG_OPENADR = {
        "ven_name": "PNNLVEN",
        "vtn_url": "https://eiss2demo.ipkeys.com/oadr2/OpenADR2/Simple/2.0b",
        "openadr_client_type": "IPKeysClient",
    }
    CONFIG_PLATFORMDRIVER = {
        "driver_scrape_interval": 0.05,
        "publish_breadth_first_all": False,
        "publish_depth_first": False,
        "publish_breadth_first": False,
    }
    CONFIG_SQLAGG = {
        "connection": {
            "type": "sqlite",
            "params": {"database": "test.sqlite", "timeout": 15},
        },
        "aggregations": [
            {
                "aggregation_period": "1m",
                "use_calendar_time_periods": "true",
                "points": [
                    {
                        "topic_names": ["device1/out_temp"],
                        "aggregation_type": "sum",
                        "min_count": 2,
                    },
                    {
                        "topic_names": ["device1/in_temp"],
                        "aggregation_type": "sum",
                        "min_count": 2,
                    },
                ],
            },
            {
                "aggregation_period": "2m",
                "use_calendar_time_periods": "false",
                "points": [
                    {
                        "topic_names": ["device1/out_temp"],
                        "aggregation_type": "sum",
                        "min_count": 2,
                    },
                    {
                        "topic_names": ["device1/in_temp"],
                        "aggregation_type": "sum",
                        "min_count": 2,
                    },
                ],
            },
        ],
    }
    CONFIG_SQL = {
        "connection": {
            "type": "sqlite",
            "params": {"database": "historian_test.sqlite"},
        },
        "all_platforms": True,
    }
    CONFIG_SQLITE = {
        "connection": {
            "type": "sqlite",
            "params": {"database": "~/.volttron/data/volttron.tags.sqlite"},
        }
    }
    CONFIG_VC = {
        "webroot": "path/to/webroot"
    }  # Default has no config; Putting in optional config to fix listing issue
    CONFIG_VCPLATFORM = {}  # Default is no config
    CONFIG_WEATHERDOTGOV = {
        "database_file": "weather.sqlite",
        "max_size_gb": 1,
        "poll_locations": [{"station": "KLAX"}, {"station": "KPHX"}],
        "poll_interval": 60,
    }

# Create list and dicts to hold specific values for agents; used for modification of platform/frontend
agent_name_list = []
agent_identity_dict = {}
agent_config_dict = {}

for count in range(len(list(AgentName))):
    agent_name_list.append(list(AgentName)[count].value)
    agent_identity_dict[list(AgentName)[count].value] = list(AgentIdentity)[count].value

    # Make config pretty print for display
    config = str(list(AgentConfig)[count].value)
    config = (config.replace("'", '"').replace("False", "false").replace("True", "true").replace("None", "null"))
    config_obj = json.loads(config)
    config_str = json.dumps(config_obj, indent=2)
    agent_config_dict[list(AgentName)[count].value] = config_str