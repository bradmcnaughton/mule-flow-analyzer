### Configuration Keys and Values

Overriding configuration options is possible with a YAML file. The following is a comprehensive example of common and advanced options. None are mandatory. Only include what you want to override.

Typically the most common options to override are the sequence diagram engine, PlantUML or Mermaid renderer settings, and the log file path (`analyzer_properties.logging.file`). PlantUML is the recommended sequence diagram output. Mermaid support is experimental and may not represent every Mule flow construct or formatting feature as accurately as PlantUML. The default log file path is relative to the current working directory when the process starts.

Depending on your implementation, the tag_rules may be useful to override if processors are being treated as participants or not.

For most color properties, don't prefix colors with `#`.

E.G. `#DD1122` should be `DD1122`

A full list of English names for colors can be found here: https://plantuml.com/en/color

Gradients should be specified as color1(/|\-)color2 without hashes. E.G. `LightBlue-6FBBD3`

```yaml
analyzer_properties:
  diagram_engine: "plantuml" # "plantuml" (default, recommended) or "mermaid" (experimental)

  output_type: "SEQUENCE" # Optional output type

  plantuml:
    mode: "server" # "server" (HTTP), "jar" (local java -jar), or "cli" (local plantuml executable)
    server: "http://my-plantuml-server:8080/" # A PlantUML server URL
    java_command: "java" # Only used in mode: jar
    jar_path: "./tools/plantuml.jar" # Only used in mode: jar
    cli_command: "plantuml" # Only used in mode: cli
    format: "png"
    output_directory: "./custom-output/diagrams" # Path to the directory where output (diagrams, text) will be saved

  mermaid: # Experimental sequence diagram output
    mode: "file" # "file" writes .mmd only, "cli" renders with Mermaid CLI
    cli_command: "mmdc" # Only used in mode: cli
    format: "svg" # Only used in mode: cli
    output_directory: "./custom-output/mermaid"
    source_extension: "mmd"

  logging:
    level: "INFO"
    file: "mfa-logs/mule_flow_analyzer.log" # relative to cwd, or use an absolute path
    format: "%(asctime)s - %(levelname)s - %(message)s"

  tag_rules:
    # A "Processor" is an action that a participant can perform on itself.
    # It adds helpful detail to the diagram
    # ------------------------------------------------------------------------------------------------
    # By default, processors are detected by a shared xml namespace prefix.
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

  # Formatting options for the diagram.
  # These are fully supported by PlantUML. Mermaid uses the semantic parts
  # where possible, but ignores PlantUML-only styling such as skinparam,
  # colors, scale, and actor icons.
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
    logging: False # Include Mule logging and tracing processors in the diagram (Makes diagrams bigger)
    errors: False # Include the error handler processors in the diagram
    notes: True # Include any documentation tag values as a Note on the actor
    ignored_group_note: True # Include a fallback note when control-flow groups are omitted because all processors are ignored

  # Controls diagram scaling to prevent cutoff. Use a smaller value if you prefer smaller diagrams.
  scale: "scale max 4000 width"

  mule:
    box-color: "LightGreen-4CAF50" # Change Mule box color(s)

  arrows:
    # Override any of the arrow styles following PlantUML styling
    # See "Change arrow style" at https://plantuml.com/sequence-diagram
    flow: "->"
    return: "-->"
    async: "->>"
    parallel: "-\\"

  actors:
    # Override or add new actor icons based on the processor prefix
    # Set any combination of icon and formatting options for specific mule components, by XML namespace prefix
    # Icons will appear on the source/target actors outside the Mule Box
    # Icon names can be found here: https://www.plantuml.com/plantuml/png/SoWkIImgAStDuSh9B2x9BqZDoqpE1s8kXzIy5A0m0000
    apikit: "<&compass>"
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

## Mermaid Compatibility Notes

Mermaid sequence output focuses on preserving the flow structure and interactions. It maps choices to `alt` / `else`, scatter-gather routes to `par` / `and`, loops to `loop`, and documentation to `Note over`.

Some PlantUML features do not have direct Mermaid equivalents:

- Custom actor icons from `diagram_formatting_properties.actors` are rendered as plain `actor` or `participant` declarations.
- `skinparam`, `scale`, rounded corners, arrow thickness, and most color settings are ignored.
- Colored transaction arrows, colored error notes, and colored groups are rendered as plain messages or notes.
- PlantUML `database`, `queue`, and other participant shapes are rendered as labeled Mermaid participants.
- The PlantUML legend is skipped for Mermaid.
- Mermaid CLI rendering depends on the installed Mermaid version. Use a recent `@mermaid-js/mermaid-cli` if you rely on `par`, `actor`, or future Mermaid syntax features.

### Notes on color values

- For color fields that are inserted as `#<value>` by the generator (for example `diagram_formatting_properties.errors.color` and transaction arrow colors), provide values without `#`.
- Inline PlantUML formatting strings may include `#` where PlantUML expects it (for example: `diagram_formatting_properties.actors.salesforce: "<color:#00A1E0><&cloud>"`).
