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

diagram_formatting_options = {
    'transactions':
    {
        'arrows': {
            1: '66CDAA',
            2: '3CB371',
            3: '556B2F',
        }
    }
}

