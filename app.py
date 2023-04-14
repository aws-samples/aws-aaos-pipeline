import os
from aws_cdk import App, Environment
from src.pipeline import PipelineStack
from src.target import TargetStack

# for development, use account/region from cdk cli
dev_env = Environment(
  account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION')
)

app = App()
pipeline = PipelineStack(app, "aws-aaos-pipeline", env=dev_env)
TargetStack(app, "aws-aaos-target", env=dev_env, pipeline=pipeline)

app.synth()