import boto3
import json
import botocore

from .datetime_serializer import serialize_datetime

client_config = botocore.config.Config(
    max_pool_connections=20,
)


class S3Manager:
    _instance = None
    _bucket = None
    _prefix = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(S3Manager, cls).__new__(cls)
            cls._instance.s3_client = boto3.client("s3", config=client_config)
        return cls._instance

    @property
    def bucket(self):
        if not self._bucket:
            raise ValueError("Bucket not set")
        return self._bucket

    def set_bucket(self, bucket):
        self._bucket = bucket

    @property
    def prefix(self):
        if not self._bucket:
            raise ValueError("Bucket not set")
        return self._prefix

    def set_prefix(self, prefix):
        self._prefix = prefix

    def upload(self, key, data):
        """Serializes data to JSON and uploads to S3 bucket with the given key."""
        key = f"{self.prefix}/{key}"
        self._instance.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(data, indent=2, default=serialize_datetime),
        )

    def get(self, key, without_prefix=False):
        """Downloads the object from S3 bucket with the given key and deserializes it from JSON."""
        if not without_prefix:
            key = f"{self.prefix}/{key}"
        response = self._instance.s3_client.get_object(Bucket=self.bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))

    def map(self, prefix, func):
        """Iterates over all objects in the S3 bucket with the given prefix and applies the given function to each
        object. Returning an array of results"""
        results = []
        paginator = self._instance.s3_client.get_paginator("list_objects_v2")
        prefix = f"{self.prefix}/{prefix}"
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                obj = self.get(key, without_prefix=True)
                result = func(obj, key)
                results.append(result)
        return results
