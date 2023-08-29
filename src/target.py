from aws_cdk import (
    Stack,
    Aws,
    aws_iam as iam,
    CfnOutput,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_s3 as s3
)
from constructs import Construct
from cdk_ec2_key_pair import KeyPair
    
class TargetStack(Stack):
  def __init__(self, scope: Construct, construct_id: str, pipeline, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)
    
    target_sg = ec2.SecurityGroup(self, "sec-group",security_group_name="sg_aaos_targett", 
      vpc=pipeline.vpc, 
      allow_all_outbound=True)
    
  
    # Allow SSH (TCP port 22) and 8443 traffic
    target_sg.add_ingress_rule(ec2.Peer.ipv4('0.0.0.0/0'), ec2.Port.tcp(22), 'Allow SSH traffic');
    target_sg.add_ingress_rule(ec2.Peer.ipv4('0.0.0.0/0'), ec2.Port.tcp(8443), 'Allow webUI traffic');
    target_sg.add_ingress_rule(ec2.Peer.ipv4('0.0.0.0/0'), ec2.Port.tcp(6520), 'ADB for Android Studio or shell');
    target_sg.add_ingress_rule(ec2.Peer.ipv4('0.0.0.0/0'), ec2.Port.tcp(6444), 'VNC -- if using');
    # Allow TCP and UDP traffic from port 15550 to port 15599
    target_sg.add_ingress_rule(ec2.Peer.ipv4('51.186.0.195/0'), ec2.Port.tcp_range(15550, 15599), 'Allow webrtc tcp traffic');
    target_sg.add_ingress_rule(ec2.Peer.ipv4('51.186.0.195/0'), ec2.Port.udp_range(15550, 15599), 'Allow webrtc udp traffic');
    
    role = iam.Role(self, 'ec2Role',
      assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'),
        iam.ManagedPolicy.from_aws_managed_policy_name('AdministratorAccess') # TBD: Should be reduced to what actually is needed by ansible scripts
      ])
    
    # Use Ubuntu 22.04 - CPU Type ARM64
    machine_image = ec2.MachineImage.from_ssm_parameter(
      parameter_name='/aws/service/canonical/ubuntu/server/focal/stable/current/arm64/hvm/ebs-gp2/ami-id')
    
    user_data = ec2.UserData.for_linux()
    user_data.add_commands(
      "sudo sed -i \"/#\$nrconf{restart} = 'i';/s/.*/\$nrconf{restart} = 'a';/\" /etc/needrestart/needrestart.conf",
      "sudo apt-get update -y",
      "sudo apt-get install -y libprotobuf-dev protobuf-compilerapt-get nfs-common binutils u-boot-tools",
      "sudo apt-get install -y git devscripts config-package-dev debhelper-compat golang",
      "sudo apt-get -y install awscli",
      "sudo apt-get -y install unzip",
      "cd ~",
      "cd /home/ubuntu ",
      "git clone https://github.com/google/android-cuttlefish",
      "cd android-cuttlefish ",
      "sudo apt-get install libprotobuf-dev protobuf-compiler -y",
      "sudo apt-get install dpkg-dev -y",
      "for dir in base frontend; do",
      "  pushd $dir",
      "  dpkg-buildpackage -uc -us",
      "  popd",
      "done",
      "sudo apt install -y ./cuttlefish-base_*.deb",
      "sudo apt install -y ./cuttlefish-user_*.deb",
      "sudo usermod -aG kvm,cvdnetwork,render ubuntu",
      "cd /home/ubuntu ",
      "mkdir /home/ubuntu/stage ",
      "cd /home/ubuntu/stage ",
      "aws s3 cp s3://{}/cvd-host_package.tar.gz .".format(pipeline.bucket.bucket_name),
      "aws s3 cp s3://{}/images.zip .".format(pipeline.bucket.bucket_name),
      "tar xvf ./cvd-host_package.tar.gz",
      "unzip ./images.zip",
      "aws s3 cp s3://{}/u-boot.bin ./bootloader".format(pipeline.bucket.bucket_name),
      "sudo cp /usr/bin/mkenvimage ./bin/mkenvimage",
      "sudo chown -R ubuntu:ubuntu /home/ubuntu/stage",
      "cat <<EOF >> /etc/systemd/system/cvd.service",
      "[Unit]",
      "Description=Cuttlefish Virtual Device",
      "After=multi-user.target",
      "[Service]",
      "Environment='HOME=/home/ubuntu/stage'",
      "Type=simple",
      "User=ubuntu",
      "Group=ubuntu",
      "ExecStart=/bin/sh -c 'yes Y | /home/ubuntu/stage/bin/launch_cvd'",
      "ExecStop=/home/ubuntu/stage/bin/stop_cvd",
      "[Install]",
      "WantedBy=multi-user.target",
      "EOF",
      "sudo chmod 644 /etc/systemd/system/cvd.service",
      "systemctl daemon-reload",
      "systemctl enable cvd.service",
      "systemctl restart cvd.service",
      "systemctl status cvd.service",
      "sudo reboot"
  )
    
    # Key pair to access to target
    key = KeyPair(self, "MyKey",
      name='target-key',
      description='target key',
      store_public_key=True)

    # Create the target
    instance = ec2.Instance(self, 'Target',
      vpc=pipeline.vpc,
      instance_type=ec2.InstanceType('m6g.metal'),
      machine_image=machine_image,
      block_devices=[
        ec2.BlockDevice(
          device_name='/dev/sda1',
          volume=ec2.BlockDeviceVolume.ebs(50)
        ),
      ],
      security_group=target_sg,
      key_name=key.key_pair_name,
      vpc_subnets=ec2.SubnetSelection(
        subnet_type=ec2.SubnetType.PUBLIC
      ),
      role=role,
      user_data=user_data)

    # Use EIP to avoid changes
    eip = ec2.CfnEIP(self, "Ip");
    ec2.CfnEIPAssociation(self, "Ec2Association",
        eip=eip.ref,
        instance_id=instance.instance_id)
    
    #Tag.add(self, key="Name", value="MyCodePipelineDemo")
    CfnOutput(self, 'Key Download Command',
      value='aws secretsmanager get-secret-value --secret-id ec2-ssh-key/{1}/private --query SecretString --output text > {2}.pem && chmod 400 {2}.pem'.
        format(Aws.STACK_NAME, key.key_pair_name, key.key_pair_name))
    CfnOutput(self, 'Target SSH command', value='ssh -i {}.pem -o IdentitiesOnly=yes ubuntu@{}'.
        format(key.key_pair_name, instance.instance_public_ip))
