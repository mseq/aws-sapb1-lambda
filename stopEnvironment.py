from datetime import datetime, timedelta
import boto3
import logging
import json
import time

def lambda_handler(event, context):

    # Take boto3 clients
    ssm = boto3.client('ssm')
    cfn = boto3.client('cloudformation')
    ec2 = boto3.client('ec2')
    asg = boto3.client('autoscaling')

    # create logger
    logger = logging.getLogger('STOPENV')
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
    logger.debug(f"Starting script StopEnvironment {d} {h}")


    # Take the time planned to execute the script
    sch = json.loads(ssm.get_parameter(Name='Environment-Schedule')['Parameter']['Value'])

    for weekday in sch['weekdays']:
        if weekday['weekday'] == str(((datetime.utcnow() + timedelta(hours=tz)).weekday())):
            if weekday['enabled'] == True:
                res = weekday['stop-environment']

                if res == h or res == h1 or res == h2:

                    # # Kill Cloud Formation Stack
                    res = ssm.get_parameter(Name='CFN-NLB-StackName')['Parameter']['Value']
                    logger.info(f"Deleting Cloud Formation Stack: {res}")
                    res = cfn.delete_stack(StackName=res)

                    # Expunge Image Backup with Expiring Retention Period for 3 consecutive days
                    extdays = ssm.get_parameter(Name='RetentionPeriod-SAPB1-Environment')['Parameter']['Value']
                    for i in [0, 1, 2]:
                        days = int(extdays) + i
                        d = str((datetime.utcnow() + timedelta(hours=tz) - timedelta(days=days)).strftime('%Y%m%d'))

                        # Find and deregister the older Images
                        for imgName in [f"WinClient-IMG-{d}", f"SAPHanaMaster-IMG-{d}", f"ADServer-IMG-{d}"]:
                            results = ec2.describe_images(
                                Filters=[
                                        {
                                            'Name': 'name', 
                                            'Values': [imgName]
                                        }
                                ]
                            )['Images']

                            for res in results:
                                logger.info(f"Deleting WinClient IMG {imgName} {res['ImageId']}")

                                ec2.deregister_image(ImageId=res['ImageId'])

                                for block_device in res['BlockDeviceMappings']:
                                    if 'SnapshotId' in block_device['Ebs']:
                                        ec2.delete_snapshot(SnapshotId=block_device['Ebs']['SnapshotId'])


                    # Stop NAT Intance
                    res = ssm.get_parameter(Name='NatInstance-SAPB1-Environment')['Parameter']['Value']
                    logger.info(f"Stoping NAT Instance {res}")
                    res = ec2.stop_instances(InstanceIds=[res])

                    # # Shutdown WinClient Instance
                    # res = ssm.get_parameter(Name='CFN-NLB-WinClientInstance')['Parameter']['Value']
                    # logger.info(f"Stoping WinClient Instance {res}")
                    # res = ec2.stop_instances(InstanceIds=[res])

                    # # Shutdown RDP Instance
                    # res = ssm.get_parameter(Name='RDPInstance-SAPB1-Environment')['Parameter']['Value']
                    # logger.info(f"Stoping RDP Instance {res}")
                    # res = ec2.stop_instances(InstanceIds=[res])

                    # Shutdown AD Server
                    res = ssm.get_parameter(Name='ADInstance-SAPB1-Environment')['Parameter']['Value']
                    logger.info(f"Stoping RDP Instance {res}")
                    res = ec2.stop_instances(InstanceIds=[res])

                    # Shutdown ASG Fleet Instances and Remove their ScaleIn Protection
                    res = asg.describe_auto_scaling_groups()
                    for autoscalinggroup in res['AutoScalingGroups']:
                        if (autoscalinggroup['AutoScalingGroupName'].find("WinClientELB-FleetASG") >= 0):
                            for instance in autoscalinggroup['Instances']:
                                # logger.info(f"Stoping ASG Instance {instance['InstanceId']}")
                                # ec2.stop_instances(InstanceIds=instance['InstanceId'])

                                logger.info(f"Removing ScaleIn Protection from ASG Instance {instance['InstanceId']}")
                                asg.set_instance_protection(
                                    InstanceIds=[instance['InstanceId']],
                                    AutoScalingGroupName=autoscalinggroup['AutoScalingGroupName'],
                                    ProtectedFromScaleIn=False)

                                logger.info(f"Terminating the ASG Instance {instance['InstanceId']}")
                                ec2.terminate_instances(InstanceIds=[instance['InstanceId']])


if __name__ == "__main__":
    lambda_handler(None, None)