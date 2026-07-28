#!/bin/bash
# aws_auth_for_mac.sh - Install dependencies and trigger authentication

set -e

echo "Starting AWS environment setup for macOS..."

# 1. Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 2. Install AWS CLI if not present
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    # -y flag automatically confirms the installation
    brew install awscli
else
    echo "AWS CLI is already installed."
fi

# 3. Trigger Authentication
echo "--------------------------------------------------------"
echo "Starting AWS configuration..."
echo "You will be prompted for your AWS Access Key, Secret Key, and region."
echo "--------------------------------------------------------"

aws configure

echo "--------------------------------------------------------"
echo "Authentication complete."
echo "Your credentials are now stored in ~/.aws/credentials"
echo "--------------------------------------------------------"
