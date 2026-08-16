#!/bin/bash
# ==============================================================================
# AWS CloudShell 1-Click Infrastructure Deployment Script — Task-2 Backend
# Provisions: VPC/Subnets, ALB, Target Group (Port 8000, /health), 
# Security Groups, and 3x t3.micro EC2 Instances across 3 Availability Zones
# ==============================================================================

set -e

# Region & Defaults (Mumbai / ap-south-1 by default for lowest Indic latency)
AWS_REGION="${AWS_REGION:-ap-south-1}"
AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_REGION AWS_DEFAULT_REGION

INSTANCE_TYPE="t3.micro"
NUM_INSTANCES=3
BACKEND_PORT=8000
HEALTH_CHECK_PATH="/health"

TAG_NAME="HH-Goa-Task2-Backend"
ALB_NAME="hh-goa-task2-alb"
TARGET_GROUP_NAME="hh-goa-task2-tg"
ALB_SG_NAME="hh-goa-alb-sg"
EC2_SG_NAME="hh-goa-ec2-sg"

echo "========================================================================"
echo "🚀 Deploying Task-2 Backend Architecture on AWS ($AWS_REGION)"
echo "   - Application Load Balancer (Port 80 -> Target Group 8000)"
echo "   - 3x EC2 Instances ($INSTANCE_TYPE) across Multi-AZ"
echo "========================================================================"

# 1. Detect Default VPC & Subnets
echo "[1/7] Querying Default VPC and Subnets in $AWS_REGION..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo "Default VPC not found. Fetching first available VPC..."
    VPC_ID=$(aws ec2 describe-vpcs --query "Vpcs[0].VpcId" --output text)
fi

echo "   - Using VPC ID: $VPC_ID"

SUBNETS=($(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text))

if [ ${#SUBNETS[@]} -lt 2 ]; then
    echo "ERROR: At least 2 subnets are required in VPC for ALB deployment."
    exit 1
fi

echo "   - All Subnets enabled for ALB Multi-AZ: ${SUBNETS[*]}"

# 2. Create ALB Security Group (Public HTTP 80 & HTTPS 443)
echo "[2/7] Provisioning ALB Security Group ($ALB_SG_NAME)..."
ALB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$ALB_SG_NAME" "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)

if [ "$ALB_SG_ID" == "None" ] || [ -z "$ALB_SG_ID" ]; then
    ALB_SG_ID=$(aws ec2 create-security-group \
        --group-name "$ALB_SG_NAME" \
        --description "Public ALB Security Group for HH Goa Task 2" \
        --vpc-id "$VPC_ID" \
        --query "GroupId" --output text)

    aws ec2 authorize-security-group-ingress --group-id "$ALB_SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 > /dev/null
    aws ec2 authorize-security-group-ingress --group-id "$ALB_SG_ID" --protocol tcp --port 443 --cidr 0.0.0.0/0 > /dev/null
    echo "   - Created ALB Security Group: $ALB_SG_ID"
else
    echo "   - Existing ALB Security Group found: $ALB_SG_ID"
fi

# 3. Create EC2 Target Security Group (Port 8000 allowed from ALB SG & 0.0.0.0/0)
echo "[3/7] Provisioning EC2 Target Security Group ($EC2_SG_NAME)..."
EC2_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$EC2_SG_NAME" "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)

if [ "$EC2_SG_ID" == "None" ] || [ -z "$EC2_SG_ID" ]; then
    EC2_SG_ID=$(aws ec2 create-security-group \
        --group-name "$EC2_SG_NAME" \
        --description "EC2 Target Security Group allowing traffic from ALB" \
        --vpc-id "$VPC_ID" \
        --query "GroupId" --output text)

    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" --protocol tcp --port 8000 --source-group "$ALB_SG_ID" > /dev/null 2>&1 || true
    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" --protocol tcp --port 8000 --cidr 0.0.0.0/0 > /dev/null 2>&1 || true
    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0 > /dev/null 2>&1 || true
    echo "   - Created EC2 Security Group: $EC2_SG_ID"
else
    echo "   - Existing EC2 Security Group found: $EC2_SG_ID"
    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" --protocol tcp --port 8000 --cidr 0.0.0.0/0 > /dev/null 2>&1 || true
fi

# 4. Create Target Group (Port 8000, /health check with 200-399 matcher & 3min startup grace)
echo "[4/7] Provisioning Target Group ($TARGET_GROUP_NAME)..."
TG_ARN=$(aws elbv2 describe-target-groups --names "$TARGET_GROUP_NAME" --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null || true)

if [ "$TG_ARN" == "None" ] || [ -z "$TG_ARN" ]; then
    TG_ARN=$(aws elbv2 create-target-group \
        --name "$TARGET_GROUP_NAME" \
        --protocol HTTP \
        --port "$BACKEND_PORT" \
        --vpc-id "$VPC_ID" \
        --health-check-protocol HTTP \
        --health-check-path "$HEALTH_CHECK_PATH" \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 10 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 6 \
        --matcher "HttpCode=200-399" \
        --target-type instance \
        --query "TargetGroups[0].TargetGroupArn" --output text)
    echo "   - Created Target Group ARN: $TG_ARN"
else
    echo "   - Existing Target Group found: $TG_ARN"
    aws elbv2 modify-target-group \
        --target-group-arn "$TG_ARN" \
        --health-check-protocol HTTP \
        --health-check-path "$HEALTH_CHECK_PATH" \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 10 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 6 \
        --matcher "HttpCode=200-399" > /dev/null
fi

# 5. Create Application Load Balancer across ALL Subnets
echo "[5/7] Provisioning Application Load Balancer ($ALB_NAME)..."
ALB_ARN=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null || true)

if [ "$ALB_ARN" == "None" ] || [ -z "$ALB_ARN" ]; then
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name "$ALB_NAME" \
        --subnets "${SUBNETS[@]}" \
        --security-groups "$ALB_SG_ID" \
        --scheme internet-facing \
        --type application \
        --query "LoadBalancers[0].LoadBalancerArn" --output text)
    echo "   - Created ALB ARN: $ALB_ARN"

    aws elbv2 create-listener \
        --load-balancer-arn "$ALB_ARN" \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn="$TG_ARN" > /dev/null
    echo "   - Created HTTP Port 80 Listener forwarding to Target Group."
else
    echo "   - Existing ALB found: $ALB_ARN"
fi

ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns "$ALB_ARN" --query "LoadBalancers[0].DNSName" --output text)

# 6. Launch 3x EC2 t3.micro Instances
echo "[6/7] Launching 3x $INSTANCE_TYPE EC2 Instances across Availability Zones..."
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=al2023-ami-2023.*-x86_64" "Name=state,Values=available" \
    --query "reverse(sort_by(Images, &CreationDate))[0].ImageId" --output text)

if [ -z "$AMI_ID" ] || [ "$AMI_ID" == "None" ]; then
    AMI_ID=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" --query "reverse(sort_by(Images, &CreationDate))[0].ImageId" --output text)
fi

echo "   - Selected AMI ID: $AMI_ID"

USER_DATA_FILE="$(dirname "$0")/user_data_ec2.sh"
if [ ! -f "$USER_DATA_FILE" ]; then
    USER_DATA_FILE="user_data_ec2.sh"
fi

INSTANCE_IDS=()

EXISTING_INSTANCES=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=${TAG_NAME}*" "Name=instance-state-name,Values=pending,running" \
    --query "Reservations[*].Instances[*].InstanceId" --output text 2>/dev/null || true)

if [ -n "$EXISTING_INSTANCES" ] && [ "$EXISTING_INSTANCES" != "None" ]; then
    echo "   - Found existing running instances: $EXISTING_INSTANCES"
    INSTANCE_IDS=($EXISTING_INSTANCES)
else
    for i in $(seq 1 $NUM_INSTANCES); do
        SUBNET_INDEX=$(( (i - 1) % ${#SUBNETS[@]} ))
        TARGET_SUBNET="${SUBNETS[$SUBNET_INDEX]}"

        INSTANCE_ID=$(aws ec2 run-instances \
            --image-id "$AMI_ID" \
            --instance-type "$INSTANCE_TYPE" \
            --security-group-ids "$EC2_SG_ID" \
            --subnet-id "$TARGET_SUBNET" \
            --associate-public-ip-address \
            --user-data "file://$USER_DATA_FILE" \
            --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${TAG_NAME}-Server-${i}}]" \
            --query "Instances[0].InstanceId" --output text)

        echo "   - Server $i launched: $INSTANCE_ID (Subnet: $TARGET_SUBNET)"
        INSTANCE_IDS+=("$INSTANCE_ID")
    done
fi

echo "   - Waiting for EC2 instances to enter 'running' state..."
aws ec2 wait instance-running --instance-ids "${INSTANCE_IDS[@]}"
echo "   - All EC2 instances are now running!"

# 7. Register Instances into Target Group
echo "[7/7] Registering 3 EC2 Instances into Target Group..."
TARGETS_PARAM=""
for id in "${INSTANCE_IDS[@]}"; do
    TARGETS_PARAM="$TARGETS_PARAM Id=$id,Port=$BACKEND_PORT"
done

aws elbv2 register-targets --target-group-arn "$TG_ARN" --targets $TARGETS_PARAM
echo "   - Successfully registered instances to Target Group."

echo "========================================================================"
echo "🎉 AWS INFRASTRUCTURE DEPLOYMENT COMPLETE!"
echo "========================================================================"
echo "  • AWS Region:             $AWS_REGION"
echo "  • Load Balancer DNS:      http://$ALB_DNS"
echo "  • Target Group Port:      $BACKEND_PORT"
echo "  • EC2 Instances (3x):     ${INSTANCE_IDS[*]}"
echo ""
echo "👉 Update your frontend NEXT_PUBLIC_BACKEND_URL to:"
echo "   http://$ALB_DNS"
echo "========================================================================"
