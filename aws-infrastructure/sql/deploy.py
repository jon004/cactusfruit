import argparse
import json
import os
import subprocess
import psycopg2
import re
import boto3
import time
import base64

def get_available_envs():
    """Load keys from deploy-to.json for the help message."""
    try:
        with open('deploy-to.json', 'r') as f:
            return list(json.load(f).keys())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def load_env_path(env_key):
    with open('deploy-to.json', 'r') as f:
        mapping = json.load(f)
    if env_key not in mapping:
        raise ValueError(f"Environment '{env_key}' not found in deploy-to.json")
    return mapping[env_key]

def get_terraform_output(output_name, terraform_dir):
    result = subprocess.run(
        ['terraform', 'output', '-json', output_name],
        cwd=terraform_dir,
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(result.stdout)

def run_via_ephemeral_ec2(env_key, terraform_dir):
    """Spins up an ephemeral EC2 runner inside the VPC to execute migrations safely every time."""
    print("Initializing ephemeral EC2 migration runner inside the VPC...")
    
    ec2 = boto3.client('ec2', region_name='us-east-1')
    ssm = boto3.client('ssm', region_name='us-east-1')

    # Get infrastructure details and outputs locally before launching instance
    print("[1/5] Fetching infrastructure metadata from Terraform outputs...")
    try:
        vpc_id = get_terraform_output('vpc_id', terraform_dir)
        db_endpoint = get_terraform_output('db_endpoint', terraform_dir)
        secret_arn = get_terraform_output('db_secret_arn', terraform_dir)
    except Exception as e:
        print(f"Error fetching data from Terraform: {e}")
        raise

    subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    if not subnets['Subnets']:
        raise ValueError(f"No subnets found for VPC {vpc_id}")
    target_subnet_id = subnets['Subnets'][0]['SubnetId']

    security_groups = ec2.describe_security_groups(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'group-name', 'Values': ['localdoby-app-sg']}
    ])
    if not security_groups['SecurityGroups']:
        raise ValueError("Security group 'localdoby-app-sg' not found in VPC")
    sg_id = security_groups['SecurityGroups'][0]['GroupId']

    # Get latest Amazon Linux 2023 AMI
    print("[2/5] Resolving latest Amazon Linux 2023 AMI...")
    ami_param = ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')
    ami_id = ami_param['Parameter']['Value']

    # Read local migration scripts
    print("[3/5] Packaging local SQL migration files...")
    sql_files = {f: open(f, 'r').read() for f in os.listdir('.') if f.endswith('.sql') and re.match(r'^\d+\.sql$', f)}
    print(f"Found {len(sql_files)} migration file(s) to include.")
    
    # Build user data script that executes on the remote instance
    user_data_script = f"""#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "=== EC2 Migration Runner Bootstrap Started ==="
dnf update -y
dnf install -y python3 python3-pip git
pip3 install boto3 psycopg2-binary

mkdir -p /app/sql
cd /app/sql
"""
    for fname, content in sql_files.items():
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        user_data_script += f"echo '{encoded_content}' | base64 -d > {fname}\n"

    # Embed Python logic using pre-resolved Terraform values (no local terraform binary needed on instance)
    user_data_script += f"""
cat << 'EOF' > runner.py
import os, psycopg2, re, boto3, json

def execute():
    print("Remote Runner: Starting database evolution process...")
    
    db_endpoint = "{db_endpoint}"
    secret_arn = "{secret_arn}"

    def get_db_credentials_local(secret_arn):
        client = boto3.client('secretsmanager', region_name='us-east-1')
        resp = client.get_secret_value(SecretId=secret_arn)
        return json.loads(resp['SecretString'])

    creds = get_db_credentials_local(secret_arn)
    host = db_endpoint.split(':')[0] if ':' in db_endpoint else db_endpoint

    print("Remote Runner: Connecting to PostgreSQL database...")
    conn = psycopg2.connect(
        host=host,
        port=5432,
        user=creds['username'],
        password=creds['password'],
        dbname="localdoby"
    )
    conn.autocommit = False
    cur = conn.cursor()
    
    print("Remote Runner: Ensuring schema_evolutions tracking table exists...")
    cur.execute("CREATE TABLE IF NOT EXISTS schema_evolutions (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    conn.commit()

    files = [f for f in os.listdir('.') if f.endswith('.sql') and re.match(r'^\d+\.sql$', f)]
    sorted_files = sorted(files, key=lambda f: int(re.match(r'^(\d+)', f).group(1)))
    
    cur.execute("SELECT version FROM schema_evolutions")
    applied_versions = {{row[0] for row in cur.fetchall()}}
    
    for filename in sorted_files:
        version = int(re.match(r'^(\d+)', filename).group(1))
        if version in applied_versions:
            print(f"Remote Runner: Skipping already applied evolution: {{filename}}")
            continue

        print(f"Remote Runner: Applying evolution: {{filename}}")
        try:
            with open(filename, 'r') as f:
                cur.execute(f.read())
            cur.execute("INSERT INTO schema_evolutions (version) VALUES (%s)", (version,))
            conn.commit()
            print(f"Remote Runner: Successfully applied {{filename}}")
        except Exception as e:
            conn.rollback()
            print(f"Remote Runner: Failed to apply {{filename}}: {{e}}")
            break
            
    cur.close()
    conn.close()
    print("Remote Runner: Database evolutions finished successfully.")

if __name__ == '__main__':
    execute()
EOF

python3 runner.py
echo "=== EC2 Migration Runner Completed Successfully ==="
"""

    print(f"[4/5] Launching temporary t3.micro instance in subnet {target_subnet_id}...")
    run_instances_response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType='t3.micro',
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{
            'SubnetId': target_subnet_id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [sg_id]
        }],
        IamInstanceProfile={
            'Name': 'localdoby-migration-runner-profile'
        },
        InstanceInitiatedShutdownBehavior='terminate',
        UserData=user_data_script,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': f'localdoby-migration-runner-{env_key}'}]
        }]
    )
    
    instance_id = run_instances_response['Instances'][0]['InstanceId']
    print(f"[5/5] Runner instance {instance_id} started. Waiting for network initialization...")
    
    running_waiter = ec2.get_waiter('instance_running')
    running_waiter.wait(InstanceIds=[instance_id])
    print("-> Runner instance is up and executing migrations internally. Waiting for completion and self-termination...")

    terminated_waiter = ec2.get_waiter('instance_terminated')
    terminated_waiter.wait(InstanceIds=[instance_id])
    print("Success: Migrations completed and ephemeral runner terminated cleanly.")

def run_evolutions():
    available_envs = get_available_envs()
    
    parser = argparse.ArgumentParser(description="Run DB evolutions via ephemeral EC2.")
    parser.add_argument(
        "--env", 
        required=True, 
        help=f"Target environment key. Available: {', '.join(available_envs) if available_envs else 'None defined'}"
    )
    args = parser.parse_args()

    terraform_dir = load_env_path(args.env)
    print(f"Targeting environment: {args.env} at {terraform_dir}")

    run_via_ephemeral_ec2(args.env, terraform_dir)

if __name__ == "__main__":
    run_evolutions()
