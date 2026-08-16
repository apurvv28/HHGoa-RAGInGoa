#!/bin/bash
# ==============================================================================
# DEPLOY — HH-Goa-Task2 Backend on AWS
# ALB: ap-south-1a + ap-south-1b  |  3x t3.micro
#       Server 1: ap-south-1a
#       Server 2: ap-south-1b
#       Server 3: ap-south-1b
# ==============================================================================

set -e

AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"

INSTANCE_TYPE="t3.micro"
BACKEND_PORT=8000
HEALTH_CHECK_PATH="/health"

TAG_NAME="HH-Goa-Task2-Backend"
ALB_NAME="hh-goa-task2-alb"
TARGET_GROUP_NAME="hh-goa-task2-tg"
ALB_SG_NAME="hh-goa-alb-sg"
EC2_SG_NAME="hh-goa-ec2-sg"

echo "========================================================"
echo "🚀 DEPLOY — HH-Goa-Task2 Backend on AWS ($AWS_REGION)"
echo "   ALB + 3x EC2 t3.micro"
echo "   Server 1: ap-south-1a  |  Servers 2&3: ap-south-1b"
echo "========================================================"

# ── Step 1: Get VPC ──────────────────────────────────────────────
echo "[1/7] Fetching VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" --output text)

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    VPC_ID=$(aws ec2 describe-vpcs --query "Vpcs[0].VpcId" --output text)
fi
echo "   VPC: $VPC_ID"

# ── Step 2: Get specific subnets for ap-south-1a and ap-south-1b ──
echo "[2/7] Finding subnets in ap-south-1a and ap-south-1b..."

SUBNET_1A=$(aws ec2 describe-subnets \
    --filters \
        "Name=vpc-id,Values=$VPC_ID" \
        "Name=availabilityZone,Values=ap-south-1a" \
    --query "Subnets[0].SubnetId" --output text)

SUBNET_1B=$(aws ec2 describe-subnets \
    --filters \
        "Name=vpc-id,Values=$VPC_ID" \
        "Name=availabilityZone,Values=ap-south-1b" \
    --query "Subnets[0].SubnetId" --output text)

if [ "$SUBNET_1A" = "None" ] || [ -z "$SUBNET_1A" ] || \
   [ "$SUBNET_1B" = "None" ] || [ -z "$SUBNET_1B" ]; then
    echo "ERROR: Could not find subnets in ap-south-1a or ap-south-1b."
    echo "Available subnets:"
    aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VPC_ID" \
        --query "Subnets[*].{ID:SubnetId,AZ:AvailabilityZone}" \
        --output table
    exit 1
fi

echo "   Subnet ap-south-1a: $SUBNET_1A"
echo "   Subnet ap-south-1b: $SUBNET_1B"

# ── Step 3: ALB Security Group ───────────────────────────────────
echo "[3/7] Provisioning ALB Security Group ($ALB_SG_NAME)..."
ALB_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$ALB_SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "None")

if [ "$ALB_SG_ID" = "None" ] || [ -z "$ALB_SG_ID" ]; then
    ALB_SG_ID=$(aws ec2 create-security-group \
        --group-name "$ALB_SG_NAME" \
        --description "ALB SG — HH Goa Task 2" \
        --vpc-id "$VPC_ID" \
        --query "GroupId" --output text)
    aws ec2 authorize-security-group-ingress --group-id "$ALB_SG_ID" \
        --protocol tcp --port 80 --cidr 0.0.0.0/0 > /dev/null
    aws ec2 authorize-security-group-ingress --group-id "$ALB_SG_ID" \
        --protocol tcp --port 443 --cidr 0.0.0.0/0 > /dev/null
    echo "   Created: $ALB_SG_ID"
else
    echo "   Exists: $ALB_SG_ID"
fi

# ── Step 4: EC2 Security Group ────────────────────────────────────
echo "[4/7] Provisioning EC2 Security Group ($EC2_SG_NAME)..."
EC2_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$EC2_SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "None")

if [ "$EC2_SG_ID" = "None" ] || [ -z "$EC2_SG_ID" ]; then
    EC2_SG_ID=$(aws ec2 create-security-group \
        --group-name "$EC2_SG_NAME" \
        --description "EC2 SG — HH Goa Task 2" \
        --vpc-id "$VPC_ID" \
        --query "GroupId" --output text)
    # Allow port 8000 from ALB SG
    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" \
        --protocol tcp --port 8000 --source-group "$ALB_SG_ID" > /dev/null 2>&1 || true
    # Allow port 8000 from anywhere (for health check probes)
    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" \
        --protocol tcp --port 8000 --cidr 0.0.0.0/0 > /dev/null 2>&1 || true
    # Allow SSH
    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" \
        --protocol tcp --port 22 --cidr 0.0.0.0/0 > /dev/null 2>&1 || true
    echo "   Created: $EC2_SG_ID"
else
    # Ensure port 8000 is open
    aws ec2 authorize-security-group-ingress --group-id "$EC2_SG_ID" \
        --protocol tcp --port 8000 --cidr 0.0.0.0/0 > /dev/null 2>&1 || true
    echo "   Exists: $EC2_SG_ID"
fi

# ── Step 5: Target Group ──────────────────────────────────────────
echo "[5/7] Provisioning Target Group ($TARGET_GROUP_NAME)..."
TG_ARN=$(aws elbv2 describe-target-groups \
    --names "$TARGET_GROUP_NAME" \
    --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null || echo "None")

if [ "$TG_ARN" = "None" ] || [ -z "$TG_ARN" ]; then
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
        --unhealthy-threshold-count 5 \
        --matcher "HttpCode=200-399" \
        --target-type instance \
        --query "TargetGroups[0].TargetGroupArn" --output text)
    echo "   Created TG: $TG_ARN"
else
    echo "   Exists TG: $TG_ARN"
fi

# ── Step 6: ALB (ap-south-1a + ap-south-1b only) ─────────────────
echo "[6/7] Provisioning ALB ($ALB_NAME)..."
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names "$ALB_NAME" \
    --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null || echo "None")

if [ "$ALB_ARN" = "None" ] || [ -z "$ALB_ARN" ]; then
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name "$ALB_NAME" \
        --subnets "$SUBNET_1A" "$SUBNET_1B" \
        --security-groups "$ALB_SG_ID" \
        --scheme internet-facing \
        --type application \
        --query "LoadBalancers[0].LoadBalancerArn" --output text)
    echo "   Created ALB: $ALB_ARN"

    # HTTP Listener Port 80 → Target Group
    aws elbv2 create-listener \
        --load-balancer-arn "$ALB_ARN" \
        --protocol HTTP --port 80 \
        --default-actions Type=forward,TargetGroupArn="$TG_ARN" > /dev/null
    echo "   HTTP:80 Listener → Target Group created."
else
    echo "   Exists ALB: $ALB_ARN"
fi

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns "$ALB_ARN" \
    --query "LoadBalancers[0].DNSName" --output text)

# ── Step 7: Launch 3 EC2 Instances ────────────────────────────────
echo "[7/7] Launching EC2 instances (1a×1, 1b×2)..."

# Use Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters \
        "Name=name,Values=al2023-ami-2023.*-x86_64" \
        "Name=state,Values=available" \
    --query "reverse(sort_by(Images, &CreationDate))[0].ImageId" \
    --output text)

echo "   AMI: $AMI_ID"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_DATA_FILE="$SCRIPT_DIR/user_data_ec2.sh"

if [ ! -f "$USER_DATA_FILE" ]; then
    echo "ERROR: user_data_ec2.sh not found at $USER_DATA_FILE"
    exit 1
fi

echo "   Using user_data: $USER_DATA_FILE"

launch_instance() {
    local SUBNET="$1"
    local AZ="$2"
    local NUM="$3"
    local ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" \
        --instance-type "$INSTANCE_TYPE" \
        --security-group-ids "$EC2_SG_ID" \
        --subnet-id "$SUBNET" \
        --associate-public-ip-address \
        --user-data "file://$USER_DATA_FILE" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${TAG_NAME}-${AZ}-Server-${NUM}}]" \
        --query "Instances[0].InstanceId" --output text)
    echo "$ID"
}

echo "   Launching Server-1 in ap-south-1a..."
ID_1=$(launch_instance "$SUBNET_1A" "1a" "1")
echo "   Server-1: $ID_1 (ap-south-1a)"

echo "   Launching Server-2 in ap-south-1b..."
ID_2=$(launch_instance "$SUBNET_1B" "1b" "2")
echo "   Server-2: $ID_2 (ap-south-1b)"

echo "   Launching Server-3 in ap-south-1b..."
ID_3=$(launch_instance "$SUBNET_1B" "1b" "3")
echo "   Server-3: $ID_3 (ap-south-1b)"

echo "   Waiting for all instances to reach 'running' state..."
aws ec2 wait instance-running --instance-ids "$ID_1" "$ID_2" "$ID_3"
echo "   ✅ All instances running!"

# Register into Target Group
echo "   Registering instances into Target Group..."
aws elbv2 register-targets \
    --target-group-arn "$TG_ARN" \
    --targets \
        "Id=$ID_1,Port=$BACKEND_PORT" \
        "Id=$ID_2,Port=$BACKEND_PORT" \
        "Id=$ID_3,Port=$BACKEND_PORT"

echo "   ✅ Instances registered."

echo ""
echo "========================================================"
echo "🎉 DEPLOYMENT COMPLETE!"
echo "========================================================"
echo "  AWS Region:         $AWS_REGION"
echo "  Load Balancer DNS:  http://$ALB_DNS"
echo "  Target Group Port:  $BACKEND_PORT"
echo "  Health Check Path:  $HEALTH_CHECK_PATH"
echo ""
echo "  EC2 Instances:"
echo "    $ID_1  →  ap-south-1a  (Server 1)"
echo "    $ID_2  →  ap-south-1b  (Server 2)"
echo "    $ID_3  →  ap-south-1b  (Server 3)"
echo ""
echo "  ⏳ Wait 4-5 mins for user-data to run and model to load."
echo "  Then all 3 targets should show HEALTHY in the console."
echo ""
echo "  👉 Update Vercel NEXT_PUBLIC_BACKEND_URL to:"
echo "     http://$ALB_DNS"
echo "========================================================"
