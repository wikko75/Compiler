from sly import Parser
from lexer import MyLexer
from generator import Generator

class MyParser(Parser):
    tokens = MyLexer.tokens
    code_generator = Generator()
    
    @_('procedures main')
    def program_all(self, p):
        for procedure in p.procedures:
            self.code_generator.gen_procedure(head=procedure[0], declarations=procedure[1], commands=procedure[2])
        self.code_generator.gen(*p.main)

    @_('procedures PROCEDURE proc_head IS declarations BEGIN commands END')
    def procedures(self, p):
        return (p.procedures + [(p.proc_head, p.declarations, p.commands)])
    
    @_('procedures PROCEDURE proc_head IS BEGIN commands END')
    def procedures(self, p):
        return (p.procedures + [(p.proc_head, [], p.commands)])
    
    @_('')
    def procedures(self, p):
        return []

    @_('PROGRAM IS declarations BEGIN commands END')
    def main(self, p):
        return (p.declarations, p.commands)
    
    @_('PROGRAM IS BEGIN commands END')
    def main(self, p):
        return ([], p.commands)
    
    # commands

    @_('commands command')
    def commands(self, p):
        return (p.commands + [p.command])
    
    @_('command')
    def commands(self, p):
        return [p.command]
    
    @_('identifier ASSIGN expression ";"')
    def command(self, p):
        return ('assign', p.identifier, p.expression, p.lineno)

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        return ('ifelse', p.condition, p.commands0, p.commands1)

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        return ('ifelse', p.condition, p.commands, [])

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        return ('while', p.condition, p.commands)

    @_('REPEAT commands UNTIL condition ";"')
    def command(self, p):
        return ('repeat', p.condition, p.commands)
    
    @_('FOR PID FROM value TO value DO commands ENDFOR')
    def command(self, p):
        return ('for_to', p.PID, p.value0, p.value1, p.commands, p.lineno)
   
    @_('FOR PID FROM value DOWNTO value DO commands ENDFOR')
    def command(self, p):
        return ('for_downto', p.PID, p.value0, p.value1, p.commands, p.lineno)


    @_('proc_call ";"')
    def command(self, p):
        return ('call', p.proc_call)

    @_('READ identifier ";"')
    def command(self, p):
        return ('read', p.identifier, p.lineno)

    @_('WRITE value ";"')
    def command(self, p):
        return ('write', p.value, p.lineno)

    
    @_('PID "(" args_decl ")"')
    def proc_head(self, p):
        return (p.PID, p.args_decl, p.lineno)
    
    @_('PID "(" args ")"')
    def proc_call(self, p):
        return (p.PID, p.args, p.lineno)
    
    # declarations

    @_('declarations "," PID')
    def declarations(self, p):
        return (p.declarations + [("variable", p.PID, p.lineno)])

    @_('declarations "," PID "[" range "]"')
    def declarations(self, p):
        return (p.declarations + [("array", p.PID, p.range[0], p.range[1] , p.lineno)])

    @_('PID')
    def declarations(self, p):
        return ([("variable", p.PID, p.lineno)])
    
    @_('PID "[" range "]"')
    def declarations(self, p):
        return ([("array", p.PID, p.range[0], p.range[1],  p.lineno)])
    

    @_('NUM ":" NUM')
    def range(self, p):
        return (p.NUM0, p.NUM1)

    @_('"-" NUM ":" NUM')
    def range(self, p):
        return (-p.NUM0, p.NUM1)

    @_('NUM ":" "-" NUM')
    def range(self, p):
        return (p.NUM0, -p.NUM1)

    @_('"-" NUM ":" "-" NUM')
    def range(self, p):
        return (-p.NUM0, -p.NUM1)
    
    # arg_decl

    @_('args_decl "," PID')
    def args_decl(self, p):
        return (p.args_decl + [('variable', p.PID)])
    
    @_('args_decl "," "T" PID')
    def args_decl(self, p):
        return (p.args_decl + [('array', p.PID)])

    @_('PID')
    def args_decl(self, p):
        return  [('variable', p.PID)]

    @_('"T" PID')
    def args_decl(self, p):
        return [('array', p.PID)]

    # args 

    @_('args "," PID')
    def args(self, p):
        return (p.args + [p.PID])

    @_('PID')
    def args(self, p):
        return [p.PID]

    # expression

    @_('value')
    def expression(self, p):
        return ('exp', p.value)

    @_('value "+" value')
    @_('value "-" value')
    @_('value "*" value')
    @_('value "/" value')
    @_('value "%" value')
    def expression(self, p):
        return ('exp', (p[1], p.value0, p.value1))

    # condition

    @_('value GT value')
    @_('value LT value')
    @_('value GE value')
    @_('value LE value')
    @_('value EQ value')
    @_('value NEQ value')
    def condition(self, p):
        return ('comparison', p[1], p.value0, p.value1)

    # value

    @_('"-" NUM')
    def value(self, p):
        return ('number', -p.NUM)
    
    @_('NUM')
    def value(self, p):
        return ('number', p.NUM)
    
    @_('identifier')
    def value(self, p):
        return ('load', p.identifier)

    # identifier 

    @_('PID')
    def identifier(self, p):
        return ('variable', p.PID)
    
    @_('PID "[" PID "]"')
    def identifier(self, p):
        return ('array', p.PID0, ('load', p.PID1))
    
    @_('PID "[" NUM "]"')
    def identifier(self, p):
        return ('array', p.PID, ('number', p.NUM))
    
    @_('PID "[" "-" NUM "]"')
    def identifier(self, p):
        return ('array', p.PID, ('number', -p.NUM))
    


    def error(self, p):
        if p:
            print(f"Syntax error at {p.type} ({p.value})")
        else:
            print("Syntax error at EOF")
