from sly import Lexer

class MyLexer(Lexer):
    tokens = {
        PID,
        NUM,
        PROCEDURE,
        IS,
        PROGRAM,

        IF, 
        THEN, 
        ELSE, 
        ENDIF,

        FOR, 
        ENDFOR,
        FROM,
        TO,
        DOWNTO, 
        REPEAT, 
        UNTIL,
        WHILE,
        ENDWHILE,
        DO,

        BEGIN,
        READ,
        WRITE,
        ASSIGN,

        END, 
        LE, 
        GE, 
        NEQ,
        GT, 
        LT, 
        EQ
    }

    PROCEDURE = r'PROCEDURE'
    IS = r'IS'
    PROGRAM = r'PROGRAM'


    IF = r'IF'
    THEN = r'THEN'
    ELSE = r'ELSE'
    ENDIF = r'ENDIF'

    FOR = r'FOR'
    ENDFOR = r'ENDFOR'
    FROM = r'FROM'
    TO = r'TO'
    DOWNTO = r'DOWNTO'
    REPEAT = r'REPEAT'
    UNTIL = r'UNTIL'
    WHILE = r'WHILE'
    ENDWHILE = r'ENDWHILE'
    DO = r'DO'

    BEGIN = r'BEGIN'
    READ = r'READ'
    WRITE = r'WRITE'
    ASSIGN = r':='

    END = r'END'

    PID = r'[_a-z]+'

    GE = r'>='
    LE = r'<='
    NEQ = r'!='
    GT = r'>'
    LT = r'<'
    EQ = r'='

    literals = {':', '+', '-', '*', '/', '%', ';', ',', '(', ')', '[', ']', 'T'}

    ignore = ' \t'
    ignore_comment = r'\#.*'


    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    def error(self, t):
        print(f"Line {self.lineno + 1}: Unrecognized symbol: {t.value[0]}")
        self.index += 1


if __name__ == '__main__':
    lexer = MyLexer()
    for token in lexer.tokenize("PROCEDURE foo(T t, s) IS"):
        print(token)