import pytest
from aws_cdk import App
from aws_cdk.assertions import Template

from src.pipeline import PipelineStack

@pytest.fixture(scope='module')
def template():
  app = App()
  stack = PipelineStack(app, "my-stack-test")
  template = Template.from_stack(stack)
  yield template

def test_no_buckets_found(template):
  pass