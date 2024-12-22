# Mulesoft Flow Analyzer

A library for analyzing Mulesoft integration projects to generate sequence diagrams or natural language descriptions of each flow.

Before analysis, placeholders in code will attempt to be replaced using values from the property files in the project directory. If there are multiple properties files, you can supply a hierarchy to follow and any omitted properties will not be referenced. This can be helpful if multiple environment property files are in the project.

Depending on your output format, text files and/or diagrams will be generated with file names based on the flow name (with special characters replaced with underscores).

## Usage

The library is available as a pip package from a private repository.

```bash
pip install https://{GIT_ACCESS_TOKEN}@raw.githubusercontent.com/bradmcnaughton/private-python-packages/main/mulesoft-flow-analyzer/1.0.0/mulesoft_flow_analyzer-1.0.0-py3-none-any.whl
```

An CLI implementing the library is at https://github.com/bradmcnaughton/mulesoft-flow-analyzer-cli

## Diagram Generation

A PlantUML server is required to generate the diagrams. This can either be run locally or using a public service.

### Running the PlantUML server locally with Docker

No MuleSoft code is required to be sent to a public server, only the generated UML. If you don't want to send the UML to a public server, you can run the PlantUML server locally.

Pull the PlantUML server image:

```bash
docker pull plantuml/plantuml-server
```

Run the PlantUML server. (In this example, the server will be available on port 8087)

```bash
docker run -d -p 8087:8080 plantuml/plantuml-server:jetty
```

Refer to the [Overriding Configuration](#overriding-configuration) section for how to specify the server address and port in the configuration file under analyzer_properties -> plantuml.

Alternatively, use the `-s` argument to specify the server address and port when running the analyzer.

## Overriding Configuration

For detailed configuration options, see [Configuration Documentation](docs/configuration.md).

## Troubleshooting

If you encounter an error, check the log file for more information. The log file is located at the path specified in the configuration file (default is /tmp/mfa-logs/mule_flow_analyzer.log).

If the log file is not found, check the default properties file for the correct path.

The log level can be set to DEBUG to get more information in the configuration file.
