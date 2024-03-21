# AWS IoT Backup

This repo provides example code, a dockerfile and cloudformation template to backup and restore AWS IoT resources to S3.

## Installation

Use git to clone the repository

```bash
git clone https://github.com/Lomi-OpenSource/aws-iot-backup.git
```

Use pipenv to install the required packages

```bash
pipenv install
```

## Command Line Usage
Backup All IoT Resources
```bash
BACKUP_BUCKET=MY_S3_BUCKET BACKUP_REGION=AWS_REGION python3 src/export.py
```
Restore Single IoT Resource
```bash
BACKUP_BUCKET=MY_S3_BUCKET BACKUP_DATE_PREFIX=2024/03/12 RESTORE_REGION=AWS_REGION THING_NAME=MY_IOT_THING python3 src/restore_single.py
```
Restore All IoT Resources
```bash
BACKUP_BUCKET=MY_S3_BUCKET BACKUP_DATE_PREFIX=2024/03/12 RESTORE_REGION=AWS_REGION python3 src/restore_all.py
```

## Docker Usage Usage
Build docker image
```bash
docker build --platform=linux/amd64 -t aws-iot-backup .
```
Run docker image to backup all IoT resources
```bash
docker run -d -e BACKUP_BUCKET=MY_S3_BUCKET -e BACKUP_REGION=AWS_REGION -v ~/.aws:/root/.aws aws-iot-backup
```
Run docker image to restore single IoT resource
```bash
docker run -d -e BACKUP_BUCKET=MY_S3_BUCKET -e BACKUP_DATE_PREFIX=2024/03/12 -e RESTORE_REGION=AWS_REGION -e THING_NAME=MY_IOT_THING -v ~/.aws:/root/.aws aws-iot-backup restore_single.py
```
Run docker image to restore all IoT resources
```bash
docker run -d -e BACKUP_BUCKET=MY_S3_BUCKET -e BACKUP_DATE_PREFIX=2024/03/12 -e RESTORE_REGION=AWS_REGION -v ~/.aws:/root/.aws aws-iot-backup restore_all.py
```

## AWS Automated Usage
Upload docker image to ECR, ensure image is already built. Replace account id and region
```bash
docker tag aws-iot-backup 123456789.dkr.ecr.us-east-1.amazonaws.com/aws-iot-backup:latest
docker login -u AWS -p $(aws ecr get-login-password --region us-east-1) 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/aws-iot-backup:latest
```
Deploy cloudformation stack.

The backup script will run on AWS fargate, to run an AWS fargate container, VPC and Subnets are required. They are not handled by this stack and should be provided as parameters to the stack. 
```bash
aws cloudformation deploy --stack-name iot-backup --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --template-file template.yaml --parameter-overrides VpcId=vpc-123abc PrivateSubnets=subnet-123abc,subnet-123abc

```

## Limitations
This is not a complete AWS IoT Backup. Things not backed up include, but are not limited to:
- Jobs
- Shadows
- Rules
- Greengrass
- Certificate Authorities
- Authorizers


## Notes

Speeding up the export can be done by setting the environment variable `MAX_WORKERS`. Be advised raising this to more than 1 without applying for quota increases may result in a failed backup. 

## License

[MIT](https://opensource.org/license/mit)

