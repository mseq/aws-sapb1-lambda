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
    logger = logging.getLogger('STARTENV')
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
    logger.debug(f"Starting script StartEnvironment {d} {h}")


    # Take the time planned to execute the script
    res = ssm.get_parameter(Name='Start-SAPB1-Environment')['Parameter']['Value']

    if res == h or res == h1 or res == h2:

        # Check if the image was already created, then if not create image/bkp and update Parameter Store
        imgName=f"WinClient-IMG-{d}"
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
            res = ssm.get_parameter(Name='CFN-NLB-WinClientInstance')['Parameter']['Value']
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
            time.sleep(30)

            state = ec2.describe_images(
                Filters=[
                        {
                            'Name': 'name', 
                            'Values': [imgName]
                        }
                    ]
                )['Images'][0]['State']

            logger.info(f"Image state is {state}")

        # Update Param Store with the right IMG
        logger.info(f"SSM Parameter CFN-NLB-WinCientAMI-Id updated with {res}")
        res = ssm.put_parameter(Name='CFN-NLB-WinCientAMI-Id', Type='String', Overwrite=True, Value=res)

        # Execute Cloud Formation Stack
        res = ssm.get_parameter(Name='CFN-NLB-StackName')['Parameter']['Value']
        url = ssm.get_parameter(Name='CFN-NLB-TemplateUrl')['Parameter']['Value']
        logger.info(f"Creating CloudFormation Stack {res}")
        res = cfn.create_stack(StackName=res, TemplateURL=url, Capabilities=['CAPABILITY_NAMED_IAM'], 
                Tags=[
                    {'Key': 'Name', 'Value': 'SAP HANA WinClient ELB'}, 
                    {'Key': 'Product', 'Value': 'SAP B1'}, 
                    {'Key': 'Department', 'Value': 'TI'}, 
                    {'Key': 'Environment', 'Value': 'Production'}
                ]
            )

        # Start NAT Instance 
        res = ssm.get_parameter(Name='NatInstance-SAPB1-Environment')['Parameter']['Value']
        logger.info(f"Starting NAT Instance {res}")
        res = ec2.start_instances(InstanceIds=[res])


if __name__ == "__main__":
    main()
