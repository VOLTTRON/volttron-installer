TEMPLATES = {
    "SQLite Historian": {
        "name": "config",
        "type": "application/json",
        "content": {
            "connection": {
                "type": "sqlite",
                "params": {
                    "database": "data/historian.sqlite"
                }
            }
        }
    },
    "PostgreSQL Historian": {
        "name": "config",
        "type": "application/json",
        "content": {
            "connection": {
                "type": "postgresql",
                "params": {
                    "dbname": "test_historian",
                    "host": "127.0.0.1",
                    "port": 5432,
                    "user": "historian",
                    "password": "historian"
                }
            }
        }
    },
    "Fake Driver — Device Config": {
        "name": "devices/fake-campus/fake-building/fake-device",
        "type": "application/json",
        "content": {
            "driver_config": {
                "remote_id": "fake-campus-building-1"
            },
            "registry_config": "config://fake.csv",
            "interval": 5,
            "timezone": "US/Pacific",
            "heart_beat_point": "Heartbeat",
            "driver_type": "fake",
            "publish_depth_first_multi": True,
            "publish_depth_first_all": True,
            "publish_breadth_first_all": False,
            "publish_breadth_first_multi": False,
            "all_publish_interval": 5
        }
    },
    "Fake Driver — Registry CSV": {
        "name": "fake.csv",
        "type": "text/csv",
        "content": "Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes\nEKG,EKG,waveform,waveform,TRUE,sin,float,Sine wave for baseline output\nHeartbeat,Heartbeat,On/Off,On/Off,TRUE,0,boolean,Point for heartbeat toggle\nOutsideAirTemperature1,OutsideAirTemperature1,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm\nSampleWritableFloat1,SampleWritableFloat1,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation\nSampleLong1,SampleLong1,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch\nSampleWritableShort1,SampleWritableShort1,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode\nSampleBool1,SampleBool1,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1\nSampleWritableBool1,SampleWritableBool1,On / Off,on/off,TRUE,TRUE,boolean,Status indicator\nOutsideAirTemperature2,OutsideAirTemperature2,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm\nSampleWritableFloat2,SampleWritableFloat2,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation\nSampleLong2,SampleLong2,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch\nSampleWritableShort2,SampleWritableShort2,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode\nSampleBool2,SampleBool2,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1\nSampleWritableBool2,SampleWritableBool2,On / Off,on/off,TRUE,TRUE,boolean,Status indicator\nOutsideAirTemperature3,OutsideAirTemperature3,F,-100 to 300,FALSE,50,float,CO2 Reading 0.00-2000.0 ppm\nSampleWritableFloat3,SampleWritableFloat3,PPM,1000.00 (default),TRUE,10,float,Setpoint to enable demand control ventilation\nSampleLong3,SampleLong3,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch\nSampleWritableShort3,SampleWritableShort3,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode\nSampleBool3,SampleBool3,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1\nSampleWritableBool3,SampleWritableBool3,On / Off,on/off,TRUE,TRUE,boolean,Status indicator\nHPWH_Phy0_PowerState,PowerState,1/0,1/0,TRUE,0,int,Power on off status\nERWH_Phy0_ValveState,ValveState,1/0,1/0,TRUE,0,int,power on off status\nEKG_Sin,EKG_Sin,1-0,SIN Wave,TRUE,sin,float,SIN wave\nEKG_Cos,EKG_Cos,1-0,COS Wave,TRUE,sin,float,COS wave"
    }
}