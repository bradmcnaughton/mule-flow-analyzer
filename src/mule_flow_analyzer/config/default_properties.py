from .constants import OutputFormat

DEFAULT_PROPERTIES = {
    'analyzer_properties': {
        'output_type': OutputFormat.SEQUENCE,
        # Sequence diagram syntax engine. PlantUML remains the default for
        # backwards compatibility.
        'diagram_engine': 'plantuml',
        'plantuml': {
            # mode can be:
            # - server: HTTP PlantUML server (local Docker-hosted or remote hosted)
            # - jar: local java -jar plantuml.jar rendering
            # - cli: local plantuml executable rendering
            'mode': 'server',
            'server': 'http://localhost:8087/',
            # Uncomment for prod - 
            # 'server': 'https://www.plantuml.com/plantuml/',
            'java_command': 'java',
            'jar_path': './tools/plantuml.jar',
            'cli_command': 'plantuml',
            'format': 'png',
            'output_directory': './output/plantuml'
        },
        'mermaid': {
            # mode can be:
            # - file: write Mermaid source only
            # - cli: render through Mermaid CLI (mmdc)
            'mode': 'file',
            'cli_command': 'mmdc',
            'format': 'svg',
            'output_directory': './output/mermaid',
            'source_extension': 'mmd'
        },
        'natural': {
            'output_directory': './output/natural',
            'file_extension': 'txt',
        },
        'logging': {
            'level': 'INFO',
            # Relative to process working directory unless overridden via user_config / YAML
            'file': 'mfa-logs/mule_flow_analyzer.log',
            #'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            # Uncomment for prod - 
            'format': '%(asctime)s - %(levelname)s - %(message)s'
        },
        'tag_rules':{
            # List of Tags that will always be processors of their parent tag regardless of the tag's prefix
            'always_processors': ['scheduling-strategy', 'fixed-frequency', 'cron', 'redelivery-policy', 'reconnect', 'error-mapping'],
            # List of Tags that should avoid being stored as processes, usually because they get put into a control flow element that shares a common prefix.
            # Note - don't include namespace which may lead to issues if any processors of one namespace use the same tag as another namespace's element
            'never_processors': ['transform', 'process-records', 'step', 'aggregator', 'on-complete'],
            # List of Tags that should be treated as internal targets and not an external connection
            'internal_targets': ['batch', 'ee', 'java', 'os', 'scripting', 'spring', 'tracing', 'tracking', 'validation', 'xml-module', 'mule-apikit']
        }
    },
    'diagram_formatting_properties': {
        # wrapWidth applies to notes and maxMessageSize applies to messages (sequence lines)
        'skinparam': [
            'skinparam monochrome false',
            'skinparam ArrowThickness 2',
            'skinparam participant {',
            'RoundCorner 20',
            '}',
            'skinparam {',
            'wrapWidth 200',
            'maxMessageSize 300',
            '}'
        ],
        # Default Scale
        # Without a scale, diagrams can get cut off
        # Using "max" will scale only when necessary
        # 4096 is the max width for PlantUML, but seems to truncate at that value, so we'll use 4000
        'scale': 'scale max 4000 width',
        # Don't prefix colors with #. E.G. #DD1122 should be DD1122
        # English names can be found here: https://plantuml.com/en/color
        # Gradients should be specified as color1(/|\-)color2 without hashes. E.G. LightBlue-6FBBD3
        'mule': {
            'box-color': 'LightBlue-6FBBD3',
        },
        'create_mode': False, # True creates processors at the point that are executed. False follows standard sequence diagram format of all participants at top and bottom 
        'verbose': {
            'processors': True, # Include more details about known processors,
            'logging': False, # Include logging and tracing processors in the diagram
            'errors': False, # Include the error handler processors in the diagram
            'notes': True, # Include documentation tag as a Note on the actor
            'ignored_group_note': True, # Include a fallback note when control-flow groups are omitted because all processors are ignored
        },
        'arrows': {
            'flow': '->',
            'return': '-->',
            # Async arrow will be used when an async process is started. (One line only)
            'async': '->>',
            'parallel': '-\\'
        },
        'actors': {
            # Set any combination of icon and formatting options for specific mule components, by namespace prefix
            # Icons will appear on the source/target actors outside the Mule Box
            # Icon names can be found here: https://www.plantuml.com/plantuml/png/SoWkIImgAStDuSh9B2x9BqZDoqpE1s8kXzIy5A0m0000
            'apikit': '<&compass>',
            'salesforce': '<color:#00A1E0><&cloud>',
            'email': '<&envelope-closed>',
            'scheduler': '<&clock>',
            'file': '<&file>',
            'http': '<&globe>',
            'socket': '<&link-intact>',
            'workday': '<&wrench>',
            'some-customers-sapi': '<&person>'
        },
        'transactions':
        {
            'arrows': {
                1: 'pink',
                2: '3CB371',
                3: '556B2F',
            }
        },
        'errors': {
            'color': 'DD1122'
        },
        'try': {
            'label-color': 'gold',
            'background-color': 'transparent',
        },
        # Async can be highlighted with a note or a group (or both)
        # If both are false, the async arrow will still be shown
        'async':{
            'note': False,
            'group': True,
            'background-color': 'goldenrod',
        },
        # Set Group to False to disable grouping for any level of batch elements
        # (Optionally) color the groups for any level of batch elements
        'batch': {
            'step': {
                'background-color': 'violet',
                'group': True,
            },
            'on-complete': {
                'background-color': 'lightgreen',
                'group': True,
            },
            'job': {
                'background-color': 'cyan',
                'group': False,
            },
            'process-records': {
                'background-color': 'green',
                'group': True,
            },
            'aggregator': {
                'background-color': 'lightyellow',
                'group': False,
            },
        }
    }
}


