import os

import boto3
import botocore


class IoTManager:
    _region = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IoTManager, cls).__new__(cls)
        return cls._instance

    @property
    def region(self):
        if not self._region:
            raise ValueError("Region not set")
        return self._region

    def set_region(self, region):
        self._instance._region = region
        self._instance.iot_client = boto3.client("iot", region_name=region)

    def replace_region_in_string(self, target):
        regions = self.get_all_regions()
        for region in regions:
            target = target.replace(region, self.region)
        return target

    def get_paginator(self, operation_name):
        return self._instance.iot_client.get_paginator(operation_name)

    def get_policy(self, policy_name):
        return self._instance.iot_client.get_policy(policyName=policy_name)

    def get_all_regions(self):
        return boto3.session.Session().get_available_regions("iot")

    def get_id_from_arn(self, arn):
        return arn.split("/")[-1]

    def get_cert_arn(self, cert_id):
        return self._instance.iot_client.describe_certificate(certificateId=cert_id)[
            "certificateDescription"
        ]["certificateArn"]

    def describe_thing(self, thing_name):
        return self._instance.iot_client.describe_thing(thingName=thing_name)

    def describe_certificate(self, certificate_id):
        return self._instance.iot_client.describe_certificate(
            certificateId=certificate_id
        )

    def describe_thing_group(self, thing_group_name):
        return self._instance.iot_client.describe_thing_group(
            thingGroupName=thing_group_name
        )

    def describe_thing_type(self, thing_type):
        return self._instance.iot_client.describe_thing_type(thingTypeName=thing_type)

    def describe_provisioning_template(self, template_name):
        return self._instance.iot_client.describe_provisioning_template(
            templateName=template_name
        )

    def list_thing_principals(self, thing_name):
        return self._instance.iot_client.list_thing_principals(thingName=thing_name)

    def list_attached_policies(self, target):
        return self._instance.iot_client.list_attached_policies(target=target)

    def thing_exists(self, thing_name):
        try:
            self._instance.iot_client.describe_thing(thingName=thing_name)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            else:
                raise

    def cert_exists(self, cert_id):
        try:
            self._instance.iot_client.describe_certificate(certificateId=cert_id)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            else:
                raise

    def thing_group_exists(self, thing_group_name):
        try:
            self._instance.iot_client.describe_thing_group(
                thingGroupName=thing_group_name
            )
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            else:
                raise

    def thing_type_exists(self, thing_type):
        try:
            self._instance.iot_client.describe_thing_type(thingTypeName=thing_type)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            else:
                raise

    def policy_exists(self, policy_name):
        try:
            self._instance.iot_client.get_policy(policyName=policy_name)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            else:
                raise

    def policy_attached(self, cert_arn, policy_name):
        policies = self._instance.iot_client.list_attached_policies(target=cert_arn)
        return policy_name in [policy["policyName"] for policy in policies["policies"]]

    def thing_principal_attached(self, cert_arn, thing_name):
        principals = self._instance.iot_client.list_thing_principals(
            thingName=thing_name
        )
        return cert_arn in principals["principals"]

    def create_thing(self, thing_name, thing_type_name, attributes):
        params = {
            "thingName": thing_name,
            "attributePayload": {"attributes": attributes, "merge": False},
        }
        if thing_type_name:
            # Boto3 does not allow sending None as a parameter, so we construct parameters this way
            params["thingTypeName"] = thing_type_name
        self._instance.iot_client.create_thing(**params)

    def create_provisioning_template(
        self,
        template_name,
        description,
        template_body,
        enabled,
        provisioning_role_arn,
        type,
    ):
        self._instance.iot_client.create_provisioning_template(
            templateName=template_name,
            description=description,
            templateBody=template_body,
            enabled=enabled,
            provisioningRoleArn=provisioning_role_arn,
            type=type,
        )

    def create_thing_group_with_parents(self, thing_group_name, thing_groups):
        if self.thing_group_exists(thing_group_name):
            return
        thing_group_detail = next(
            (
                group
                for group in thing_groups
                if group["thingGroupName"] == thing_group_name
            ),
            None,
        )
        params = {"thingGroupName": thing_group_name}
        parent_thing_group = thing_group_detail["thingGroupMetadata"].get(
            "parentGroupName"
        )
        if parent_thing_group:
            if not self.thing_group_exists(parent_thing_group):
                self.create_thing_group_with_parents(parent_thing_group, thing_groups)
            # Boto3 does not allow sending None as a parameter, so we construct parameters this way
            params["parentGroupName"] = parent_thing_group
        self._instance.iot_client.create_thing_group(**params)

    def create_cert(self, pem):
        self._instance.iot_client.register_certificate_without_ca(
            certificatePem=pem, status="ACTIVE"
        )

    def create_thing_type(self, thing_type, thing_type_properties):
        self._instance.iot_client.create_thing_type(
            thingTypeName=thing_type, thingTypeProperties=thing_type_properties
        )

    def create_policy(self, policy_name, policy_document):
        # When deploying policies in a new region, any hardcoded regions will need to be replaced
        policy_document = self.replace_region_in_string(policy_document)
        self._instance.iot_client.create_policy(
            policyName=policy_name, policyDocument=policy_document
        )

    def attach_policy(self, cert_arn, policy_name):
        self._instance.iot_client.attach_policy(policyName=policy_name, target=cert_arn)

    def attach_thing_principal(self, cert_arn, thing_name):
        self._instance.iot_client.attach_thing_principal(
            thingName=thing_name, principal=cert_arn
        )

    def add_thing_to_thing_group(self, thing_group_name, thing_name):
        self._instance.iot_client.add_thing_to_thing_group(
            thingGroupName=thing_group_name, thingName=thing_name
        )
