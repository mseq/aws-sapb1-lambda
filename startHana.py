from datetime import datetime, timedelta
import boto3
import logging
import time
import json

def lambda_handler(event, context):

    # Take boto3 clients
    ssm = boto3.client('ssm')
    cfn = boto3.client('cloudformation')
    ec2 = boto3.client('ec2')

    # create logger
    logger = logging.getLogger('STARTHANA')
    ch = logging.StreamHandler()

    # set debug level
    res = ssm.get_parameter(Name='DebugLevel-LambdaScripts')['Parameter']['Value']
    if res == "DEBUG":
        logger.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
    elif res == "INFO":
        logger.setLevel(logging.INFO)
        ch.setLevel(logging.INFO)
    elif res == "WARNING":
        logger.setLevel(logging.WARNING)
        ch.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.NOTSET)
        ch.setLevel(logging.NOTSET)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    tz = int(ssm.get_parameter(Name='Environment-TimeZone')['Parameter']['Value'])

    d = str((datetime.utcnow() + timedelta(hours=tz)).strftime('%Y%m%d'))
    h = str((datetime.utcnow() + timedelta(hours=tz)).strftime('%H:%M'))
    h1 = str((datetime.utcnow() + timedelta(hours=tz) + timedelta(minutes=-1)).strftime('%H:%M'))
    h2 = str((datetime.utcnow() + timedelta(hours=tz) + timedelta(minutes=-2)).strftime('%H:%M'))
    logger.debug(f"Starting script StartHana {d} {h}")


    # Take the time planned to execute the script
    sch = json.loads(ssm.get_parameter(Name='Environment-Schedule')['Parameter']['Value'])

    for weekday in sch['weekdays']:
        if weekday['weekday'] == str(((datetime.utcnow() + timedelta(hours=tz)).weekday())):
            if weekday['enabled'] == True:
                res = weekday['start-hana']

                if res == h or res == h1 or res == h2:
                    # Check if the image was already created, then if not create image/bkp
                    imgName=f"SAPHanaMaster-IMG-{d}"
                    res = ec2.describe_images(
                        Filters=[
                                {
                                    'Name': 'name', 
                                    'Values': [imgName]
                                }
                            ]
                        )['Images']

                    if res:
                        logger.warning(f"Image already exists {res[0]['ImageId']}")
                        res = res[0]['ImageId']
                    else:
                        res = ssm.get_parameter(Name='HanaInstance-SAPB1-Environment')['Parameter']['Value']
                        res = ec2.create_image(InstanceId=res, Name=imgName)['ImageId']
                        logger.info(f"Creating img {imgName}")

                    # Make sure the image is available
                    state = ec2.describe_images(
                        Filters=[
                                {
                                    'Name': 'name', 
                                    'Values': [imgName]
                                }
                            ]
                        )['Images'][0]['State']

                    logger.info(f"Image state is {state}")
                    while state != "available":
                        time.sleep(300)

                        state = ec2.describe_images(
                            Filters=[
                                    {
                                        'Name': 'name', 
                                        'Values': [imgName]
                                    }
                                ]
                            )['Images'][0]['State']

                        logger.info(f"Image state is {state}")


                    state = 'stopped'

                    while state == 'stopped':
                        # Start HANA Instance
                        res = ssm.get_parameter(Name='HanaInstance-SAPB1-Environment')['Parameter']['Value']
                        logger.info(f"Starting HANA Instance {res}")

                        try:
                            res = ec2.start_instances(InstanceIds=[res])
                        except Exception as e:
                            logger.error(f"Error starting HANA Instance {e}")
                            if e.response['Error']['Code'] == 'InsufficientInstanceCapacity':
                                pass
                            else:
                                raise e

                        # Wait for HANA Instance to be running
                        state = ec2.describe_instances(
                            InstanceIds=[ssm.get_parameter(Name='HanaInstance-SAPB1-Environment')['Parameter']['Value']]
                            )['Reservations'][0]['Instances'][0]['State']['Name']
                        
                        time.sleep(30)        

if __name__ == "__main__":
    lambda_handler(None, None)