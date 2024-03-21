import os
import sys

from lib.iot_manager import IoTManager
from lib.s3_manager import S3Manager


def ensure_certificates(thing_name):
    principal_assignments = S3Manager().get(f"principals-assignments.json")
    certs_arns = principal_assignments[thing_name]
    cert_ids = [IoTManager().get_id_from_arn(arn) for arn in certs_arns]
    cert_details = [S3Manager().get(f"certs/{cert_id}.json") for cert_id in cert_ids]
    for cert_id in cert_ids:
        if not IoTManager().cert_exists(cert_id):
            IoTManager().create_cert(
                cert_details[cert_ids.index(cert_id)]["certificatePem"]
            )
        cert_arn = IoTManager().replace_region_in_string(
            cert_details[cert_ids.index(cert_id)]["certificateArn"]
        )
        ensure_policies(cert_id, cert_arn)
        if not IoTManager().thing_principal_attached(cert_arn, thing_name):
            IoTManager().attach_thing_principal(cert_arn, thing_name)


def ensure_policies(cert_id, cert_arn):
    policy_assignments = S3Manager().get("policy-assignments.json")
    cert_policies = policy_assignments[cert_id]
    for policy in cert_policies:
        if not IoTManager().policy_exists(policy["policyName"]):
            policy_details = S3Manager().get(f"policies/{policy['policyName']}.json")
            IoTManager().create_policy(
                policy["policyName"], policy_details["policyDocument"]
            )
        if not IoTManager().policy_attached(cert_arn, policy["policyName"]):
            IoTManager().attach_policy(cert_arn, policy["policyName"])


def ensure_thing_groups(thing_name):
    thing_groups = S3Manager().get(f"thing_groups.json")
    thing_groups_names = [group["thingGroupName"] for group in thing_groups]
    for group_name in thing_groups_names:
        things_in_group = S3Manager().get(f"thing_groups/{group_name}.json")
        if thing_name in things_in_group:
            if not IoTManager().thing_group_exists(group_name):
                IoTManager().create_thing_group_with_parents(group_name, thing_groups)
            IoTManager().add_thing_to_thing_group(
                thing_group_name=group_name, thing_name=thing_name
            )


def ensure_thing_type(thing_type):
    thing_type_details = S3Manager().get(f"thing-types/{thing_type}.json")
    if not IoTManager().thing_type_exists(thing_type):
        IoTManager().create_thing_type(
            thing_type, thing_type_details["thingTypeProperties"]
        )


def restore_thing(thing_name):
    if IoTManager().thing_exists(thing_name):
        sys.exit(f"Thing {thing_name} already exists, exiting")
    thing_description = S3Manager().get(f"things/{thing_name}.json")
    thing_type = thing_description.get("thingTypeName")
    if thing_type:
        ensure_thing_type(thing_type)
    IoTManager().create_thing(
        thing_name,
        thing_description.get("thingTypeName"),
        thing_description["attributes"],
    )
    ensure_certificates(thing_name)
    ensure_thing_groups(thing_name)


if __name__ == "__main__":
    thing_name = os.environ["THING_NAME"]
    BACKUP_BUCKET = os.environ["BACKUP_BUCKET"]
    BACKUP_DATE_PREFIX = os.environ["BACKUP_DATE_PREFIX"]
    RESTORE_REGION = os.environ["RESTORE_REGION"]
    IoTManager().set_region(RESTORE_REGION)
    S3Manager().set_bucket(BACKUP_BUCKET)
    S3Manager().set_prefix(BACKUP_DATE_PREFIX)
    restore_thing(thing_name)
