# TODO: Make this configurable via properties file
analyzer_properties = {
    'plantuml': {
        'server': 'http://localhost:8087/',
        'output_directory': './output/plantuml'
    }
}

# wrapWidth applies to notes and maxMessageSize applies to messages (sequence lines)
skimparam_options = [
    'skinparam monochrome false',
    'skinparam ArrowThickness 2',
    'skinparam participant {',
    'RoundCorner 20',
    '}',
    'skinparam {',
    'wrapWidth 200',
    'maxMessageSize 200',
    '}'
]

# All colors should be in CSS format with no hash
# e.g. #DD1122 should be DD1122
# English names can be found here: https://plantuml.com/en/color
# Gradients should be specified as color1(/|\-)color2 without hashes
diagram_formatting_options = {
    'mule': {
        'box-color': 'LightBlue-6FBBD3',
    },
    'create_mode': False, # True creates processors at the point that are executed. False follows standard sequence diagram format of all participants at top and bottom 
    'verbose': {
        'processors': True, # Include more details about known processors
        'errors': False, # Include the error handler processors in the diagram
        'notes': True, # Include documentation tag as a Note on the actor
    },
    'actors': {
        # Set any combination of icon and formatting options for specific actors
        # Icon names can be found here: https://www.plantuml.com/plantuml/png/SoWkIImgAStDuSh9B2x9BqZDoqpE1s8kXzIy5A0m0000
        'salesforce': '<color:#00A1E0><&cloud>',
        'email': '<&envelope-closed>',
        'scheduler': '<&clock>',
        'file': '<&file>',
        'http': '<&globe>',
        'socket': '<&link-intact>',
    },
    'processors': {
        'internal': ['batch', 'ee', 'java', 'os', 'scripting', 'spring', 'tracing', 'tracking', 'validation', 'xml-module']
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
    }
}

