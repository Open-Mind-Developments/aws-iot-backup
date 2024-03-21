import os
from concurrent.futures import ThreadPoolExecutor

from lib.futures_helper import run_futures_raising_failures_after_completion
from lib.iot_manager import IoTManager
from lib.logging import get_logger
from lib.s3_manager import S3Manager

logger = get_logger(__name__)


def restore_certs():
    def restore_cert(cert_details, _):
        IoTManager().create_cert(cert_details["certificatePem"])
        logger.debug(f"Restored cert {cert_details['certificateId']}")

    S3Manager().map("certs", restore_cert)


def restore_policies():
    def restore_policy(policy_details, _):
        policy_document = IoTManager().replace_region_in_string(
            policy_details["policyDocument"]
        )
        IoTManager().create_policy(policy_details["policyName"], policy_document)
        logger.debug(f"Restored policy {policy_details['policyName']}")

    S3Manager().map("policies", restore_policy)


def restore_things():
    restore_thing_types()

    def restore_thing(thing_details, _):
        IoTManager().create_thing(
            thing_details["thingName"],
            thing_details.get("thingTypeName"),
            thing_details["attributes"],
        )
        logger.debug(f"Restored thing {thing_details['thingName']}")

    S3Manager().map("things", restore_thing)


def restore_thing_groups():
    thing_group_details = S3Manager().get("thing_groups.json")
    for thing_group in thing_group_details:
        IoTManager().create_thing_group_with_parents(
            thing_group["thingGroupName"], thing_group_details
        )
        logger.debug(f"Restored thing group {thing_group['thingGroupName']}")


def restore_thing_types():
    def restore_thing_type(thing_type_details, _):
        IoTManager().create_thing_type(
            thing_type_details["thingTypeName"],
            thing_type_details["thingTypeProperties"],
        )
        logger.debug(f"Restored thing type {thing_type_details['thingTypeName']}")

    S3Manager().map("thing_types", restore_thing_type)


def restore_provisioning_templates():
    def restore_provisioning_template(template_details, _):
        IoTManager().create_provisioning_template(
            template_details["templateName"],
            template_details["description"],
            template_details["templateBody"],
            template_details["enabled"],
            template_details["provisioningRoleArn"],
            template_details["type"],
        )
        logger.debug(
            f"Restored provisioning template {template_details['templateName']}"
        )

    S3Manager().map("provisioning_templates", restore_provisioning_template)


def restore_policy_assignments():
    policy_assignments = S3Manager().get("policy-assignments.json")
    for cert_id, policies in policy_assignments.items():
        for policy in policies:
            IoTManager().attach_policy(
                IoTManager().get_cert_arn(cert_id), policy["policyName"]
            )
            logger.debug(
                f"Restored policy assignment {policy['policyName']} to cert {cert_id}"
            )


def restore_principal_assignments():
    principal_assignments = S3Manager().get("principals-assignments.json")
    for thing_name, certs_arns in principal_assignments.items():
        for cert_arn in certs_arns:
            IoTManager().attach_thing_principal(cert_arn, thing_name)
            logger.debug(
                f"Restored principal assignment {thing_name} to cert {cert_arn}"
            )


def restore_thing_group_assignments():
    thing_groups = S3Manager().get("thing_groups.json")
    for thing_group in thing_groups:
        things_in_group = S3Manager().get(
            f"thing_groups/{thing_group['thingGroupName']}.json"
        )
        for thing in things_in_group:
            IoTManager().add_thing_to_thing_group(thing_group["thingGroupName"], thing)
            logger.debug(
                f"Restored thing group assignment {thing} to group {thing_group['thingGroupName']}"
            )


def restore_all():
    with ThreadPoolExecutor() as executor:
        resource_creation_futures = [
            executor.submit(restore_policies),
            executor.submit(restore_certs),
            executor.submit(restore_things),
            executor.submit(restore_thing_groups),
            executor.submit(restore_provisioning_templates),
        ]
        resource_matching_futures = [
            executor.submit(restore_policy_assignments),
            executor.submit(restore_principal_assignments),
            executor.submit(restore_thing_group_assignments),
        ]
        try:
            run_futures_raising_failures_after_completion(resource_creation_futures)
            run_futures_raising_failures_after_completion(resource_matching_futures)
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            raise


if __name__ == "__main__":
    BACKUP_BUCKET = os.environ["BACKUP_BUCKET"]
    BACKUP_DATE_PREFIX = os.environ["BACKUP_DATE_PREFIX"]
    RESTORE_REGION = os.environ["RESTORE_REGION"]
    IoTManager().set_region(RESTORE_REGION)
    S3Manager().set_bucket(BACKUP_BUCKET)
    S3Manager().set_prefix(BACKUP_DATE_PREFIX)
    restore_all()
