import sys
from lexer import MyLexer
from parser import MyParser

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f'Usage: python <input_program> <out_compiled_program>')
        exit(1)

    with open(sys.argv[1], 'r') as input_file:
        source_code = input_file.read()

        lexer  = MyLexer()
        parser = MyParser()
        parser.parse(lexer.tokenize(source_code))
        
        with open(sys.argv[2], 'w') as output_file:
            if not parser.code_generator.errorMode:
                for line in parser.code_generator.code:
                    output_file.write(line + '\n')