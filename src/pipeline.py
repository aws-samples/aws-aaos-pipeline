import os
from aws_cdk import (
    Aws,
    Stack,
    aws_codecommit as cc,
    aws_codebuild as cb,
    aws_codepipeline as cp,
    aws_codepipeline_actions as cpa,
    aws_codedeploy as cd,
    aws_iam as iam,
    aws_s3 as s3,
    Duration,
    aws_efs as efs,
    aws_ec2 as ec2
)
from constructs import Construct


class PipelineStack(Stack):
  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    repo = cc.Repository(self, "Repo1",
      repository_name='aaos',
      code = cc.Code.from_directory(
        directory_path = os.path.join(os.path.dirname(__file__), 'repo_seed/')))
    
    self.bucket = s3.Bucket(self, "Bucket")
    
    self.vpc = ec2.Vpc(self, "VPC",
      max_azs=1,
      nat_gateways=1)
    
    security_group = ec2.SecurityGroup(self, 'SecurityGroup1',
      allow_all_outbound=True,
      description='SecurityGroup1',
      security_group_name='SecurityGroup1',
      vpc=self.vpc)
    
    fs = efs.FileSystem(self, "FS",
      vpc=self.vpc,
      throughput_mode=efs.ThroughputMode.ELASTIC)
    fs.connections.allow_default_port_from(security_group)
        
    source_artifact = cp.Artifact("SourceArtifact")
    source_action = cpa.CodeCommitSourceAction(
        action_name="Source",
        repository=repo,
        output=source_artifact,
        branch='main')
    
    build_role = iam.Role(self, "BuildRole", 
      assumed_by=iam.ServicePrincipal(
        "codebuild.amazonaws.com"),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
            "AWSCodeCommitPowerUser")])
    
    self.bucket.grant_write(build_role)

    build_project = cb.PipelineProject(self, "BuildProject",
      role=build_role,
      environment=cb.BuildEnvironment(
        privileged=True,
        compute_type=cb.ComputeType.X2_LARGE,
        #build_image=cb.LinuxBuildImage.from_docker_registry('public.ecr.aws/lts/ubuntu:18.04')),
        build_image=cb.LinuxBuildImage.STANDARD_5_0),
      environment_variables={
        "BUCKET_NAME": cb.BuildEnvironmentVariable(value=self.bucket.bucket_name)
      },
      build_spec=cb.BuildSpec.from_source_filename('buildspec.yml'),
      timeout=Duration.minutes(300),
      vpc=self.vpc,
      security_groups=[security_group],
      grant_report_group_permissions=False,
      file_system_locations=[
        cb.FileSystemLocation.efs(
        identifier='myid',
        location="{}.efs.{}.amazonaws.com:/".format(fs.file_system_id,Aws.REGION),
        mount_point="/cache",
        mount_options="nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2")])

    build_action = cpa.CodeBuildAction(
        action_name="build",
        project=build_project,
        input=source_artifact)

    cp.Pipeline(
        self, "android-pipeline",
        stages=[
        cp.StageProps(stage_name="Source",
            actions=[source_action]),
        cp.StageProps(stage_name="Build",
            actions=[build_action])])

