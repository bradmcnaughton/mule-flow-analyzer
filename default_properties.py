DEFAULT_PROPERTIES = {
    'analyzer_properties': {
        'plantuml': {
            'server': 'http://localhost:8087/',
            'output_directory': './output/plantuml'
        },
        'logging': {
            'level': 'INFO',
            'file': './output/logs/mule_flow_analyzer.log'
        },
        'tag_rules':{
            # List of Tags that will always be processors of their parent tag regardless of the tag's prefix
            'always_processors': ['scheduling-strategy', 'fixed-frequency', 'cron', 'redelivery-policy', 'reconnect', 'error-mapping'],
            # List of Tags that should avoid being stored as processes, usually because they get put into a control flow element that shares a common prefix.
            # Note - don't include namespace which may lead to issues if any processors of one namespace use the same tag as another namespace's element
            'never_processors': ['transform', 'process-records', 'step', 'aggregator', 'on-complete'],
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
        'scale': 'scale max 4096 width',
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
        'processors': {
            'internal': ['batch', 'ee', 'java', 'os', 'scripting', 'spring', 'tracing', 'tracking', 'validation', 'xml-module', 'mule-apikit']
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


