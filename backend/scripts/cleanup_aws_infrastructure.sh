#!/bin/bash
# ==============================================================================
# AWS CloudShell Teardown & Cleanup Script — Task-2 Backend
# Safely terminates EC2 instances, Target Group, ALB & Security Groups
# ==============================================================================

set -e

AWS_REGION="${AWS_REGION:-ap-south-1}"
AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_REGION AWS_DEFAULT_REGION

TAG_NAME="HH-Goa-Task2-Backend"
ALB_NAME="hh-goa-task2-alb"
TARGET_GROUP_NAME="hh-goa-task2-tg"
ALB_SG_NAME="hh-goa-alb-sg"
EC2_SG_NAME="hh-goa-ec2-sg"

echo "========================================================================"
echo "🧹 Cleaning up Task-2 AWS Infrastructure ($AWS_REGION)..."
echo "========================================================================"

# 1. Terminate EC2 Instances
echo "[1/4] Finding and terminating Task-2 EC2 instances..."
INSTANCE_IDS=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=${TAG_NAME}*" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query "Reservations[*].Instances[*].InstanceId" --output text 2>/dev/null || true)

if [ -n "$INSTANCE_IDS" ] && [ "$INSTANCE_IDS" != "None" ]; then
    echo "   - Terminating instances: $INSTANCE_IDS"
    aws ec2 terminate-instances --instance-ids $INSTANCE_IDS > /dev/null
    echo "   - Waiting for instances to terminate..."
    aws ec2 wait instance-terminated --instance-ids $INSTANCE_IDS 2>/dev/null || sleep 15
    echo "   - EC2 instances terminated."
else
    echo "   - No active EC2 instances found."
fi

# 2. Delete ALB Listeners & ALB
echo "[2/4] Deleting Application Load Balancer ($ALB_NAME)..."
ALB_ARN=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null || true)

if [ -n "$ALB_ARN" ] && [ "$ALB_ARN" != "None" ]; then
    LISTENERS=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query "Listeners[*].ListenerArn" --output text 2>/dev/null || true)
    for listener in $LISTENERS; do
        if [ -n "$listener" ] && [ "$listener" != "None" ]; then
            aws elbv2 delete-listener --listener-arn "$listener" 2>/dev/null || true
        fi
    done

    echo "   - Deleting ALB: $ALB_ARN"
    aws elbv2 delete-load-balancer --load-balancer-arn "$ALB_ARN"
    echo "   - Waiting for ALB deletion..."
    aws elbv2 wait load-balancers-deleted --load-balancer-arns "$ALB_ARN" 2>/dev/null || sleep 15
    echo "   - ALB deleted."
else
    echo "   - No ALB found."
fi

# 3. Delete Target Group with retry loop
echo "[3/4] Deleting Target Group ($TARGET_GROUP_NAME)..."
TG_ARN=$(aws elbv2 describe-target-groups --names "$TARGET_GROUP_NAME" --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null || true)

if [ -n "$TG_ARN" ] && [ "$TG_ARN" != "None" ]; then
    echo "   - Deleting Target Group: $TG_ARN"
    for i in {1..6}; do
        if aws elbv2 delete-target-group --target-group-arn "$TG_ARN" 2>/dev/null; then
            echo "   - Target Group deleted successfully."
            break
        else
            echo "   - Target Group still detaching, waiting 5 seconds... ($i/6)"
            sleep 5
        fi
    done
else
    echo "   - No Target Group found."
fi

# 4. Delete Security Groups
echo "[4/4] Deleting Security Groups..."
sleep 5

EC2_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$EC2_SG_NAME" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)
if [ -n "$EC2_SG_ID" ] && [ "$EC2_SG_ID" != "None" ]; then
    aws ec2 delete-security-group --group-id "$EC2_SG_ID" 2>/dev/null || true
    echo "   - EC2 Security Group deleted."
fi

ALB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$ALB_SG_NAME" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)
if [ -n "$ALB_SG_ID" ] && [ "$ALB_SG_ID" != "None" ]; then
    aws ec2 delete-security-group --group-id "$ALB_SG_ID" 2>/dev/null || true
    echo "   - ALB Security Group deleted."
fi

echo "========================================================================"
echo "✅ AWS INFRASTRUCTURE CLEANUP COMPLETE!"
echo "========================================================================"
