# TODO: Make this configurable via properties file
analyzer_properties = {
    'plantuml': {
        'server': 'http://localhost:8087/',
        'output_directory': './output/plantuml'
    }
}

skimparam_options = [
    'skinparam monochrome false',
    'skinparam ArrowThickness 2',
    'skinparam participant {',
    'RoundCorner 20',
    '}'
]

# All colors should be in CSS format with no hash
# e.g. #DD1122 should be DD1122
# English names can be found here: https://plantuml.com/en/color
# Gradients should be specified as color1(/|\-)color2 without hashes
diagram_formatting_options = {
    'transactions':
    {
        'arrows': {
            1: '66CDAA',
            2: '3CB371',
            3: '556B2F',
        }
    },
    'errors': {
        'color': 'DD1122'
    },
    'mule': {
        'box-color': 'LightBlue-6FBBD3',
    },
    'processors': {
        'internal': ['batch', 'ee', 'java', 'os', 'scripting', 'spring', 'tracing', 'tracking', 'validation', 'xml-module']
    }
}

