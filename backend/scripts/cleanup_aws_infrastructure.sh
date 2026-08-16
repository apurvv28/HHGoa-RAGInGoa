#!/bin/bash
# ==============================================================================
# FULL CLEANUP — Removes all HH-Goa-Task2 AWS resources
# Terminates EC2, deletes ALB, Listeners, Target Group, Security Groups
# ==============================================================================

set -e

AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"

TAG_NAME="HH-Goa-Task2-Backend"
ALB_NAME="hh-goa-task2-alb"
TARGET_GROUP_NAME="hh-goa-task2-tg"
ALB_SG_NAME="hh-goa-alb-sg"
EC2_SG_NAME="hh-goa-ec2-sg"

echo "========================================================"
echo "🧹 FULL CLEANUP — HH-Goa-Task2 AWS ($AWS_REGION)"
echo "========================================================"

# 1. Terminate all tagged EC2 instances
echo "[1/4] Terminating EC2 instances..."
INSTANCE_IDS=$(aws ec2 describe-instances \
    --filters \
        "Name=tag:Name,Values=${TAG_NAME}*" \
        "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query "Reservations[*].Instances[*].InstanceId" \
    --output text 2>/dev/null || true)

if [ -n "$INSTANCE_IDS" ] && [ "$INSTANCE_IDS" != "None" ]; then
    echo "   Terminating: $INSTANCE_IDS"
    aws ec2 terminate-instances --instance-ids $INSTANCE_IDS > /dev/null
    echo "   Waiting for termination..."
    aws ec2 wait instance-terminated --instance-ids $INSTANCE_IDS
    echo "   ✅ EC2 instances terminated."
else
    echo "   No EC2 instances found."
fi

# 2. Delete ALB Listeners first, then ALB
echo "[2/4] Deleting ALB & Listeners..."
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names "$ALB_NAME" \
    --query "LoadBalancers[0].LoadBalancerArn" \
    --output text 2>/dev/null || echo "None")

if [ "$ALB_ARN" != "None" ] && [ -n "$ALB_ARN" ]; then
    LISTENERS=$(aws elbv2 describe-listeners \
        --load-balancer-arn "$ALB_ARN" \
        --query "Listeners[*].ListenerArn" \
        --output text 2>/dev/null || true)
    for L in $LISTENERS; do
        [ -n "$L" ] && [ "$L" != "None" ] && \
            aws elbv2 delete-listener --listener-arn "$L" 2>/dev/null || true
    done
    aws elbv2 delete-load-balancer --load-balancer-arn "$ALB_ARN"
    echo "   Waiting for ALB deletion..."
    aws elbv2 wait load-balancers-deleted --load-balancer-arns "$ALB_ARN" 2>/dev/null || sleep 20
    echo "   ✅ ALB deleted."
else
    echo "   No ALB found."
fi

# 3. Delete Target Group (retry loop — TG can't be deleted while ALB is deleting)
echo "[3/4] Deleting Target Group..."
TG_ARN=$(aws elbv2 describe-target-groups \
    --names "$TARGET_GROUP_NAME" \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text 2>/dev/null || echo "None")

if [ "$TG_ARN" != "None" ] && [ -n "$TG_ARN" ]; then
    for i in 1 2 3 4 5 6 7 8 9 10; do
        if aws elbv2 delete-target-group --target-group-arn "$TG_ARN" 2>/dev/null; then
            echo "   ✅ Target Group deleted."
            break
        fi
        echo "   Attempt $i/10: waiting 5s for ALB to detach..."
        sleep 5
    done
else
    echo "   No Target Group found."
fi

# 4. Delete Security Groups (wait for ENIs to release)
echo "[4/4] Deleting Security Groups..."
sleep 10

EC2_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$EC2_SG_NAME" \
    --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "None")
if [ "$EC2_SG_ID" != "None" ] && [ -n "$EC2_SG_ID" ]; then
    aws ec2 delete-security-group --group-id "$EC2_SG_ID" 2>/dev/null && \
        echo "   ✅ EC2 Security Group deleted." || \
        echo "   ⚠️ EC2 SG still in use — will be deleted after ENIs release."
fi

ALB_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$ALB_SG_NAME" \
    --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "None")
if [ "$ALB_SG_ID" != "None" ] && [ -n "$ALB_SG_ID" ]; then
    aws ec2 delete-security-group --group-id "$ALB_SG_ID" 2>/dev/null && \
        echo "   ✅ ALB Security Group deleted." || \
        echo "   ⚠️ ALB SG still in use — will be deleted after ENIs release."
fi

echo "========================================================"
echo "✅ CLEANUP COMPLETE!"
echo "========================================================"
