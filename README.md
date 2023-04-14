# Android Automotive OS pipeline (DRAFT)

## Getting started

Install both cdk and projen

```
npm install -g aws-cdk projen
```

Run projen to install all dependencies and install the pipeline stack

```
cd aws-aaos-pipeline
projen
pip install -r requirements-dev.txt
cdk deploy -- aws-aaos-pipeline
```

once the stack has been deployed and the pipeline has run successfully (about 2.5h) you can deploy the target stack

```
cdk deploy -- aws-aaos-target
```

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

- [Changelog](CHANGELOG.md) of the project.
- [License](LICENSE) of the project.
- [Code of Conduct](CODE_OF_CONDUCT.md) of the project.
- [CONTRIBUTING](CONTRIBUTING.md) for more information.
