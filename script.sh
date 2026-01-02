#!/bin/bash

# ==========================================
# SETUP AWS S3 BUCKET & ENV
# ==========================================

echo "☁️  Starting AWS S3 Setup..."

# 1. Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# 2. Get Default Region or Prompt
CONFIGURED_REGION=$(aws configure get region)
read -p "Enter AWS Region [Default: $CONFIGURED_REGION]: " AWS_REGION
AWS_REGION=${AWS_REGION:-$CONFIGURED_REGION}

if [ -z "$AWS_REGION" ]; then
    echo "❌ Region is required."
    exit 1
fi

# 3. Get Bucket Name
read -p "Enter a UNIQUE Bucket Name (e.g., gramsahayak-uploads-2025): " AWS_BUCKET_NAME

if [ -z "$AWS_BUCKET_NAME" ]; then
    echo "❌ Bucket Name is required."
    exit 1
fi

echo "-------------------------------------"
echo "🛠️  Creating Bucket: $AWS_BUCKET_NAME in $AWS_REGION..."

# 4. Create Bucket
if [ "$AWS_REGION" == "us-east-1" ]; then
    aws s3api create-bucket --bucket "$AWS_BUCKET_NAME" --region "$AWS_REGION"
else
    aws s3api create-bucket --bucket "$AWS_BUCKET_NAME" --region "$AWS_REGION" --create-bucket-configuration LocationConstraint="$AWS_REGION"
fi

if [ $? -ne 0 ]; then
    echo "❌ Failed to create bucket. Name might be taken. Try again."
    exit 1
fi

# 5. Disable "Block Public Access" (Required for Public URLs)
echo "🔓 Unblocking Public Access..."
aws s3api put-public-access-block \
    --bucket "$AWS_BUCKET_NAME" \
    --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# 6. Apply Public Read Policy
echo "📜 Applying Bucket Policy..."
POLICY_JSON=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$AWS_BUCKET_NAME/*"
        }
    ]
}
EOF
)

aws s3api put-bucket-policy --bucket "$AWS_BUCKET_NAME" --policy "$POLICY_JSON"

if [ $? -eq 0 ]; then
    echo "✅ Bucket Policy Applied (Public Read Enabled)."
else
    echo "❌ Failed to apply policy."
    exit 1
fi

# 7. Update .env File
echo "📝 Updating .env file..."

# Fetch credentials from AWS CLI config
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)

# Function to update or append variable in .env
update_env() {
    key=$1
    value=$2
    file=".env"

    if grep -q "^$key=" "$file"; then
        # Replace existing value (using | as delimiter to handle slashes)
        sed -i "s|^$key=.*|$key=$value|" "$file"
    else
        # Append new value
        echo "$key=$value" >> "$file"
    fi
}

# Ensure .env exists
touch .env

update_env "AWS_ACCESS_KEY_ID" "$AWS_ACCESS_KEY_ID"
update_env "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET_ACCESS_KEY"
update_env "AWS_REGION" "$AWS_REGION"
update_env "AWS_BUCKET_NAME" "$AWS_BUCKET_NAME"

echo "-------------------------------------"
echo "🎉 SUCCESS: S3 Bucket Configured!"
echo "-------------------------------------"
echo "Bucket: $AWS_BUCKET_NAME"
echo "Region: $AWS_REGION"
echo "Policy: Public Read Access"
echo "Creds:  Updated in .env"
echo "-------------------------------------"
echo "👉 You can now try uploading files via the API."