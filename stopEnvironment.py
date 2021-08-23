from datetime import datetime, timedelta
import json
import boto3
import logging

# create logger
logger = logging.getLogger('STOPENV')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


d = str(datetime.today().strftime('%Y%m%d'))
h = str(datetime.today().strftime('%H:%M'))
logger.debug(f"Starting script StopEnvironment {d} {h}")

# Take boto3 clients
ssm = boto3.client('ssm')
cfn = boto3.client('cloudformation')
ec2 = boto3.client('ec2')

# Take the time planned to execute the script
res = ssm.get_parameter(Name='ShutDown-SAPB1-Environment')['Parameter']['Value']

if res == h:
    # Kill Cloud Formation Stack
    res = ssm.get_parameter(Name='CFN-NLB-StackName')['Parameter']['Value']
    logger.info(f"Deleting Cloud Formation Stack: {res}")
    res = cfn.delete_stack(StackName=res)

    # Expunge Image Backup with Expiring Retention Period for 3 consecutive days
    extdays = ssm.get_parameter(Name='RetentionPeriod-SAPB1-Environment')['Parameter']['Value']
    for i in [0, 1, 2]:
        days = int(extdays) + i
        d = str((datetime.today() - timedelta(days=days)).strftime('%Y%m%d'))

        # Find and deregister the WinClientImg
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
            logger.info(f"Deleting IMG {d} {res[0]['ImageId']}")
            ec2.deregister_image(res[0]['ImageId'])
        else:
            logger.warning(f"No WinClient image to delete {d}")

        # Find and deregister the HanaImg
        imgName=f"SAPHanaMaster-IMG-{d}"
        resh = ec2.describe_images(
            Filters=[
                    {
                        'Name': 'name', 
                        'Values': [imgName]
                    }
            ]
        )['Images']
        if res:
            logger.info(f"Deleting IMG {d} {res[0]['ImageId']}")
            ec2.deregister_image(res[0]['ImageId'])
        else:
            logger.warning(f"No Hana Master image to delete {d}")

    # Stop NAT Intance
    res = ssm.get_parameter(Name='NatInstance-SAPB1-Environment')['Parameter']['Value']
    logger.info(f"Stoping NAT Instance {res}")
    res = ec2.stop_instances(InstanceIds=[res])

    # Shutdown WinClient Instance
    res = ssm.get_parameter(Name='CFN-NLB-WinClientInstance')['Parameter']['Value']
    logger.info(f"Stoping WinClient Instance {res}")
    res = ec2.stop_instances(InstanceIds=[res])

    # Shutdown RDP Instance
    res = ssm.get_parameter(Name='RDPInstance-SAPB1-Environment')['Parameter']['Value']
    logger.info(f"Stoping RDP Instance {res}")
    res = ec2.stop_instances(InstanceIds=[res])
