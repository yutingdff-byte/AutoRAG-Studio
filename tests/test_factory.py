from parser.parser_factory import parse_file



files = [

    "tests/data/test.docx",

    "tests/data/test.xlsx",

    "tests/data/test.pdf"

]



for file in files:


    print(
        "\n================"
    )


    print(
        file
    )


    result = parse_file(
        file
    )


    print(
        result[:300]
    )