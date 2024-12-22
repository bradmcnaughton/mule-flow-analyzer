### Configuration Keys and Values

Overriding configuration options is possible with a YAML file. The following example shows all possible options being overriden. None are mandatory. Only include what you want to override.

Typically the most common options to override are the PlantUML server address and port, and the logging directory.

Depending on your implementation, the tag_rules may be useful to override if processors are being treated as participants or not.

For all formatting, dDon't prefix colors with '#'.

E.G. #DD1122 should be `DD1122`

A full list of English names for colors can be found here: https://plantuml.com/en/color

Gradients should be specified as color1(/|\-)color2 without hashes. E.G. `LightBlue-6FBBD3`

```yaml
analyzer_properties:
  plantuml:
    server: "http://my-plantuml-server:8080/" # A PlantUML server URL
    output_directory: "./custom-output/diagrams" # Path to the directory where output (diagrams, text) will be saved

  logging:
    level: "INFO"
    file: "/tmp/mfa-logs/mule_flow_analyzer.log"

  tag_rules:
    # A "Processor" is an action that a participant can perform on itself.
    # It adds helpful detail to the diagram
    # ------------------------------------------------------------------------------------------------
    # By default, procesors are detected by a shared xml namespace prefix.
    # Some Mule tags don't have a namespace prefix, the 'always_processors' will force them to be treated as processors.
    always_processors:
      [
        "scheduling-strategy",
        "fixed-frequency",
        "cron",
        "redelivery-policy",
        "reconnect",
        "error-mapping",
      ]
    # Inversely, the 'never_processors' will force them to be treated as participants.
    never_processors:
      ["transform", "process-records", "step", "aggregator", "on-complete"]
    # The generator will create an external connection for any connectors it detects.
    # This list defines what is considered an internal target.
    internal_targets:
      [
        "batch",
        "ee",
        "java",
        "os",
        "scripting",
        "spring",
        "tracing",
        "tracking",
        "validation",
        "xml-module",
        "mule-apikit",
      ]

  # Formatting options for the diagram
diagram_formatting_properties:
  skinparam:
    # The skinparam options format the diagram
    # Setting this property will override all skinparam defaults
    # Each entry in the array will be a new line in skinparams.
    # There is no need for indentation.
    - "skinparam monochrome true"
    - "skinparam ArrowThickness 3"
    - "skinparam participant {"
    - "RoundCorner 10"
    - "}"
    - "skinparam {"
    - "wrapWidth 150"
    - "maxMessageSize 250"
    - "}"

  create_mode: true # True creates processors at the point that are executed. False follows standard sequence diagram format of all participants at top and bottom

  verbose:
    # Verbosity can be tweaked for different aspects. Increasing verbosity leads to bigger diagrams/more output
    processors: True # Include more details about known processors
    logging: False # Include MuleSoft logging and tracing processors in the diagram (Makes diagrams bigger)
    errors: False # Include the error handler processors in the diagram
    notes: True # Include any documentation tag values as a Note on the actor

  # Controls diagram scaling to prevent cutoff. Use a smaller value if you prefer smaller diagrams.
  scale: "scale max 4096 width"

  mule:
    box-color: "LightGreen-4CAF50" # Change Mule box color(s)

  arrows:
    # Override any of the arrow styles following PlantUML styling
    # See "Change arrow style" at https://plantuml.com/sequence-diagram
    flow: "=>"
    return: "==>"
    async: "=>>"
    parallel: "=\\"

  actors:
    # Override or add new actor icons based on the processor prefix
    # Set any combination of icon and formatting options for specific mule components, by XML namespace prefix
    # Icons will appear on the source/target actors outside the Mule Box
    # Icon names can be found here: https://www.plantuml.com/plantuml/png/SoWkIImgAStDuSh9B2x9BqZDoqpE1s8kXzIy5A0m0000
    salesforce: "<color:#00A1E0><&cloud>"
    email: "<&envelope-closed>"
    scheduler: "<&clock>"
    file: "<&file>"
    http: "<&globe>"
    socket: "<&link-intact>"
    workday: "<&wrench>"
    some-customers-sapi: "<&person>"

  processors:
    # Any processors marked "internal" will not be placed on diagrams
    internal:
      - "batch"
      - "java"
      - "validation"

  transactions:
    # Formatting for distributed transactions occuring within a flow. Up to 3 levels of transactions.
    arrows:
      1: "blue"
      2: "green"
      3: "orange"

  errors:
    # Formatting for errors
    color: "FF0000"

  async:
    # Formatting for Async functionality
    note: true # Include a note indicating an async scope is starting
    group: true # Wrap the async processing in a UML group
    background-color: "yellow" # Specify the async scope's background color

  batch:
    # Formatting for Batch Processing scopes
    # Enable "groups" for whatever aspects of the batch process need to be made prominent
    # For example, if only one step, grouping steps can be disabled
    # If Aggregator is not used, the aggregator grouping can be disabled
    step:
      background-color: "purple"
      group: true
    on-complete:
      background-color: "lightblue"
      group: false
    job:
      background-color: "pink"
      group: true
    process-records:
      background-color: "lime"
      group: true
    aggregator:
      background-color: "orange"
      group: true
  try:
    # Formatting for Try scopes
    label-color: "gold" # Color of the try scope label
    background-color: "transparent" # Background color of the try scope
```
