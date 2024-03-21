import datetime
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.futures_helper import run_futures_raising_failures_after_completion
from lib.iot_manager import IoTManager
from lib.logging import get_logger
from lib.s3_manager import S3Manager

logger = get_logger(__name__)

MAX_WORKERS = os.environ.get("MAX_WORKERS", 1)

def describe_thing_and_upload_returning_principals(thing):
    thing_name = thing["thingName"]
    detail = IoTManager().describe_thing(thing_name=thing_name)
    del detail["ResponseMetadata"]
    S3Manager().upload(f"things/{thing_name}.json", detail)
    logger.debug(f"Exported thing {thing_name}")
    thing_principals = IoTManager().list_thing_principals(thing_name=thing_name)
    return {thing_name: thing_principals["principals"]}


def describe_all_things_and_principles():
    paginator = IoTManager().get_paginator("list_things")
    principals = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(describe_thing_and_upload_returning_principals, thing)
            for page in paginator.paginate()
            for thing in page["things"]
        ]
        for future in as_completed(futures):
            principals.update(future.result())
    S3Manager().upload(f"principals-assignments.json", principals)
    logger.info("Exported all things and their principals")


def describe_cert_and_upload_returning_policies(cert):
    cert_id = cert["certificateId"]
    detail = IoTManager().describe_certificate(certificate_id=cert_id)
    del detail["ResponseMetadata"]
    S3Manager().upload(f"certs/{cert_id}.json", detail["certificateDescription"])
    logger.debug(f"Exported cert {cert_id}")
    cert_policies = IoTManager().list_attached_policies(
        target=detail["certificateDescription"]["certificateArn"]
    )
    return {cert_id: cert_policies["policies"]}


def describe_all_certs_and_policies():
    paginator = IoTManager().get_paginator("list_certificates")
    policies = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(describe_cert_and_upload_returning_policies, cert)
            for page in paginator.paginate()
            for cert in page["certificates"]
        ]
        for future in as_completed(futures):
            policies.update(future.result())
        S3Manager().upload(f"policy-assignments.json", policies)
        logger.info("Exported all certs and their policies")


def describe_all_thing_groups():
    paginator = IoTManager().get_paginator("list_thing_groups")
    groups = []
    for page in paginator.paginate():
        for group in page["thingGroups"]:
            detail = IoTManager().describe_thing_group(
                thing_group_name=group["groupName"]
            )
            del detail["ResponseMetadata"]
            groups.append(detail)
            paginator = IoTManager().get_paginator("list_things_in_thing_group")
            things = []
            for page in paginator.paginate(thingGroupName=group["groupName"]):
                things.extend(page["things"])
            S3Manager().upload(f'thing_groups/{group["groupName"]}.json', things)
            logger.info(f"Exported thing group {group['groupName']}")
    S3Manager().upload(f"thing_groups.json", groups)
    logger.info("Exported all thing groups")


def describe_all_thing_types():
    paginator = IoTManager().get_paginator("list_thing_types")
    for page in paginator.paginate():
        for thingType in page["thingTypes"]:
            detail = IoTManager().describe_thing_type(
                thing_type=thingType["thingTypeName"]
            )
            del detail["ResponseMetadata"]
            S3Manager().upload(f'thing_types/{thingType["thingTypeName"]}.json', detail)


def describe_all_policies():
    paginator = IoTManager().get_paginator("list_policies")
    for page in paginator.paginate():
        for policy in page["policies"]:
            detail = IoTManager().get_policy(policy_name=policy["policyName"])
            del detail["ResponseMetadata"]
            S3Manager().upload(f'policies/{policy["policyName"]}.json', detail)
            logger.debug(f"Exported policy {policy['policyName']}")
    logger.info("Exported all policies")


def describe_all_provisioning_templates():
    paginator = IoTManager().get_paginator("list_provisioning_templates")
    for page in paginator.paginate():
        for template in page["templates"]:
            detail = IoTManager().describe_provisioning_template(
                template_name=template["templateName"]
            )
            S3Manager().upload(
                f'provisioning_templates/{template["templateName"]}.json', detail
            )
            logger.debug(f"Exported provisioning template {template['templateName']}")


def export_described_data():
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(describe_all_things_and_principles),
            executor.submit(describe_all_certs_and_policies),
            executor.submit(describe_all_thing_groups),
            executor.submit(describe_all_thing_types),
            executor.submit(describe_all_policies),
            executor.submit(describe_all_provisioning_templates),
        ]
        try:
            run_futures_raising_failures_after_completion(futures)
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            raise


if __name__ == "__main__":
    BACKUP_REGION = os.environ["BACKUP_REGION"]
    BACKUP_BUCKET = os.environ["BACKUP_BUCKET"]
    BACKUP_DATE_PREFIX = datetime.datetime.now().strftime("%Y/%m/%d")
    IoTManager().set_region(BACKUP_REGION)
    S3Manager().set_bucket(BACKUP_BUCKET)
    S3Manager().set_prefix(BACKUP_DATE_PREFIX)
    export_described_data()
