from projen.awscdk import AwsCdkPythonApp

project = AwsCdkPythonApp(
    author_email="salamida@amazon.com",
    author_name="Francesco Salamida",
    cdk_version="2.74.0",
    module_name="src",
    name="aws-aaos-pipeline",
    version="0.1.0",
)
project.add_dev_dependency('cdk-ec2-key-pair')
project.add_git_ignore('*.pem')
project.add_git_ignore('cdk.context.json')

project.synth()