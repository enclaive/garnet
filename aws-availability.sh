#!/bin/bash
# aws-availability.sh
# Queries which AZs support SEV-SNP instance types (m6a, c6a, r6a)
# Output: region | instance_type | AZs

REGIONS=(
  eu-central-1
  eu-south-1
  eu-west-1
  eu-west-2
  eu-west-3
  us-east-1
  us-east-2
  us-west-1
  us-west-2
  ca-central-1
  ap-south-1
  ap-northeast-1
  ap-southeast-1
  ap-southeast-2
  sa-east-1
)

INSTANCE_TYPES=(
  m6a.large m6a.xlarge m6a.2xlarge m6a.4xlarge m6a.8xlarge
  c6a.large c6a.xlarge c6a.2xlarge c6a.4xlarge c6a.8xlarge c6a.12xlarge c6a.16xlarge
  r6a.large r6a.xlarge r6a.2xlarge r6a.4xlarge
)

echo "region,instance_type,availability_zones"

for REGION in "${REGIONS[@]}"; do
  for INSTANCE in "${INSTANCE_TYPES[@]}"; do
    AZS=$(aws ec2 describe-instance-type-offerings \
      --location-type availability-zone \
      --filters "Name=instance-type,Values=${INSTANCE}" \
      --region "${REGION}" \
      --query 'InstanceTypeOfferings[*].Location' \
      --output text 2>/dev/null | tr '\t' ',' )

    if [ -n "$AZS" ]; then
      echo "${REGION},${INSTANCE},${AZS}"
    fi
  done
done
