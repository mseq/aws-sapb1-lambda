import boto3
import json

# Create a connection to the EC2 service
EC2 = boto3.client('ec2')

snapshots = []
response = EC2.describe_images(Owners=['self'])

imgCounter = 0
snapshotCounter = 0

for image in response['Images']:
    print(f"Found image: {image['Name']}")

    for block_device in image['BlockDeviceMappings']:
        if 'Ebs' in block_device and 'SnapshotId' in block_device['Ebs']:
            print(f"   Found snapshot: {block_device['Ebs']['SnapshotId']}")
            snapshots.append(block_device['Ebs']['SnapshotId'])
            snapshotCounter += 1

    imgCounter += 1

print(f"\nTotal Images: {imgCounter}")
print(f"Total Snapshots: {snapshotCounter}\n\n")

print(snapshots)

# Get all snapshots
all_snapshots = EC2.describe_snapshots(OwnerIds=['self'])['Snapshots']
totalSnapshots = len(list(all_snapshots))

print(f"\n\nFound {totalSnapshots} snapshots in the account\n")

deletedSnapshots = 0
# Delete any snapshots that are not in the array of IDs
for snapshot in all_snapshots:
    if snapshot['SnapshotId'] not in snapshots:
        deletedSnapshots += 1
        print(f"...Deleting snapshot {snapshot['SnapshotId']} ({str(round(deletedSnapshots/totalSnapshots*100, 2))}%)")
        EC2.delete_snapshot(SnapshotId=snapshot['SnapshotId'])


print(f"\n\nDeleted {deletedSnapshots} snapshots\n\n")