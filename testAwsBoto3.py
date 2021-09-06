import boto3
import json
from datetime import datetime, timedelta

ssm = boto3.client('ssm')

tz = int(ssm.get_parameter(Name='Environment-TimeZone')['Parameter']['Value'])

d = str((datetime.utcnow() + timedelta(hours=tz)).strftime('%Y%m%d'))
h = str((datetime.utcnow() + timedelta(hours=tz)).strftime('%H:%M'))
h1 = str((datetime.utcnow() + timedelta(hours=tz) + timedelta(minutes=-1)).strftime('%H:%M'))
h2 = str((datetime.utcnow() + timedelta(hours=tz) + timedelta(minutes=-2)).strftime('%H:%M'))

sch = json.loads(ssm.get_parameter(Name='Environment-Schedule')['Parameter']['Value'])

for weekday in sch['weekdays']:
    if weekday['weekday'] == str(((datetime.utcnow() + timedelta(hours=tz)).weekday())):
        if weekday['enabled'] == True:
            print(weekday['start-img-bkp'])
