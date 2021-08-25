from datetime import datetime, timedelta
import boto3
import logging
import time
import json

def main():
# def lambda_handler(event, context):

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


    d = str((datetime.utcnow() + timedelta(hours=-3)).strftime('%Y%m%d'))
    h = str((datetime.utcnow() + timedelta(hours=-3)).strftime('%H:%M'))
    logger.debug(f"Starting script StopEnvironment {d} {h}")


    # Take the time planned to execute the script
    res = ssm.get_parameter(Name='Start-HANA-Environment')['Parameter']['Value']

    if res == h:
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


        # Start HANA Instance
        res = ssm.get_parameter(Name='HanaInstance-SAPB1-Environment')['Parameter']['Value']
        logger.info(f"Starting HANA Instance {res}")
        res = ec2.start_instances(InstanceIds=[res])


if __name__ == "__main__":
    main()