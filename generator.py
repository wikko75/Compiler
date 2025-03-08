class Variable:
    def __init__(self, location):
        self.location = location
        self.initialized = False

    def __repr__(self):
        return f'Type: variable, Initialized: {"True" if self.initialized else "False"}, Location: {self.location}'

class Array:
    def __init__(self, name, location, lower_bound, upper_bound):
        self.name = name
        self.location = location
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.size = upper_bound - lower_bound + 1

    def __repr__(self):
        return f'Type: array, Location: {self.location}, Size: {self.size}, Lower bound: {self.lower_bound}, Upper bound: {self.upper_bound}'

    def get(self, index):
        if self.lower_bound <= index <= self.upper_bound:
            return self.location + (index - self.lower_bound) + 1   # + 1 because first cell stores lower bound value
        else:
            raise Exception(f"Index '{index}' is out of bounds for array '{self.name}'")
        
class Pointer:
    def __init__(self, location, type):
        self.location = location
        self.type = type

    def __repr__(self):
        return f'Type: {self.type}, Location: {self.location}'

class Iterator:
    def __init__(self, location):
        self.location = location
        self.active = True

    def __repr__(self):
        return f'Type: iterator, Location: {self.location}'

TEMP_CELL_A = 0
TEMP_CELL_B = 1     # gen_body

TEMP_CELL_C = 2     # gen_condition
TEMP_CELL_D = 3     # gen_condition

TEMP_CELL_E = 4     # calculate_expression
TEMP_CELL_F = 5     # calculate_expression
TEMP_CELL_G = 6     # calculate_expression
TEMP_CELL_H = 7     # calculate_expression
TEMP_CELL_I = 8     # calculate_expression
TEMP_CELL_J = 9     # calculate_expression
TEMP_CELL_K = 10    # calculate_expression
TEMP_CELL_L = 11    # calculate_expression

TEMP_CELL_M = 12    # for temporary address of variable in load_address function
TEMP_CELL_V = 13    # for temporary address of variable in load_value function
TEMP_CELL_V2= 14    # for temporary address of variable in load_value function


class Memory(dict):
    def __init__(self, offset):
        super().__init__()
        self.offset = offset
    
    def add_variable(self, name):
        if name in self:
            raise Exception(f"variable '{name}' is already declared")
        self.setdefault(name, Variable(self.offset))
        self.offset += 1

    def add_array(self, name, lower_bound, upper_bound):
        size = upper_bound - lower_bound + 1
        if name in self:
            raise Exception(f"array '{name}' is already declared")
        elif size <= 0:
            raise Exception(f"array '{name}' can not be declared with lower bound: '{lower_bound}' greater that upper bound: '{upper_bound}' -> size; '{size}'")
        self.setdefault(name, Array(name, self.offset, lower_bound, upper_bound))
        self.offset += (size + 1)  # + 1 because we store lower bound as a first element of array (needed for proper index calculation)

    def add_pointer(self, name, type):
        if name in self:
            raise Exception(f"pointer '{name}' already declared")
        self.setdefault(name, Pointer(self.offset, type))
        self.offset += 1

    def add_iterator(self, name):
        if name in self:
            if not isinstance(self[name], Iterator):
                raise Exception(f"Variable '{name}' can not be declared as iterator - name collision")
            if self[name].active:
                raise Exception(f"Iterator '{name}' is already declared - check for name collision")
            else:
                self[name].active = True
        else:
            self.setdefault(name, Iterator(self.offset))
            self.setdefault(f'{name}_iter_end', Iterator(self.offset + 1))
            self.offset += 2   # why 2? because we need to store  !END! value of iterator,
                               # and that might come from variable, that might be changed inside BODY 
                               # and iterator doesn't care about that change is saves only initial value

    def delete_iterator(self, name):
        if name not in self:
            raise Exception(f"Can't free iterator - Iterator '{name}' is undeclared")
        self[name].active = False


    def is_pointer(self, name):
        if name in self:
            if not isinstance(self[name], Pointer):
                return False
            if self[name].type != 'variable':
                raise Exception(f"pointer '{name}' points to array")
            return True
        else:
            raise Exception(f"undeclared variable '{name}'")
        
    def is_array_pointer(self, name):
        if name in self:
            if not isinstance(self[name], Pointer):
                return False
            if self[name].type != 'array':
                raise Exception(f"pointer '{name}' points to variable")
            return True
        else:
            raise Exception(f"undeclared array '{name}'")
        
    def get_type(self, name):
        if name in self:
            if isinstance(self[name], Variable):
                return 'variable'
            if isinstance(self[name], Array):
                return 'array'
            if isinstance(self[name], Pointer):
                return 'pointer'
            if isinstance(self[name], Iterator):
                return 'iterator'
        else:
            raise Exception(f"undeclared identifier '{name}'")
        
    def get_pointer_type(self, name):
        if name in self:
            if not isinstance(self[name], Pointer):
                raise Exception(f"'{name}' is not pointer")
            return self[name].type
        else:
            raise Exception(f"undeclared pointer '{name}'")

    def get_variable(self, name):
        if name in self:
            return self[name].location
        else:
            raise Exception(f"undeclared variable '{name}'")
        
    def get_array_at_index(self, name, index, get_array_start_location = False):
        if name in self:
            a = self[name]
            
            if isinstance(a, Array):
                if get_array_start_location:
                    return a.location
                return a.get(index)
            else:
                raise Exception(f"'{name}' is not array")
        else:
            raise Exception(f"Undeclared array '{name}'")
        
class Procedure:
    def __init__(self, name, location, callback):
        self.name = name
        self.pointers = []
        self.location = location
        self.callback = callback
    
    def add_pointer(self, location, type):
        self.pointers.append(Pointer(location, type))

    def __repr__(self):
        return f'Procedure: {self.name}, location: {self.location}'

        
class Generator:
    def __init__(self):
        self.debug = True
        self.offset = 15  # since first 15 cells are reserved look: 'TEMP_CELLS_' above
        self.memory = None
        self.procedures = dict()
        self.code = []
        self.errorMode = False
        self.loopDepth = 0
        self.lineno = 1

    def gen_procedure(self, head, declarations, commands):
        name = head[0]
        args = head[1]
        
        if name in self.procedures:
            print(f"Error: Line {head[2]}: procedure '{name}' already declared")
            return
        if len(self.code) == 0:
            self.code.append('PLACEHOLDER')
        procedure = Procedure(name, len(self.code), self.offset)
        self.memory = Memory(self.offset + 1)

        # gen pointers
        for arg in args:
            self.memory.add_pointer(arg[1], arg[0])
            procedure.add_pointer(self.memory.get_variable(arg[1]), arg[0])
        
        self.gen_declarations(declarations)
        self.gen_body(commands)
        self.procedures.setdefault(name, procedure)
        self.offset = self.memory.offset

        # return
        self.code.append(f'RTRN {procedure.callback}')

    def gen(self, declarations, commands):
        if len(self.code) > 0:
            self.code[0] = f'JUMP {len(self.code)}'

        self.memory = Memory(self.offset)
        self.gen_declarations(declarations)
        self.gen_body(commands)
        self.code.append("HALT")

    def gen_declarations(self, declarations):
        for declaration in declarations:
            if declaration[0] == "variable":
                try:
                    self.memory.add_variable(name=declaration[1])
                except Exception as e:
                    print(f'Error: Line {declaration[2]}: {e}')
                    self.errorMode = True
            else: # declaration[0] == "array"
                try:
                    self.memory.add_array(name=declaration[1], lower_bound=declaration[2], upper_bound=declaration[3])
                    
                    #! need to store lower bound in memory cell, so that index dereferencing is properly computed in pointers to array
                    address = self.memory.get_array_at_index(declaration[1], 0, get_array_start_location=True)
                    self.code.append(f'SET {declaration[2]}')
                    self.code.append(f'STORE {address}')
                
                except Exception as e:
                    print(f'Error: Line {declaration[4]}: {e}')
                    self.errorMode = True

    def gen_body(self, commands):
        for command in commands:
            if command[0] == 'assign':
                target = command[1]
                expression = command[2]
                self.lineno = command[3]
               
                try:
                    if self.memory.get_type(target[1]) == 'iterator':
                        raise Exception(f"can not modify local iterator '{target[1]}'")
                    
                    self.load_address(target)
                    self.code.append(f'STORE {TEMP_CELL_B}')
                    self.calculate_expression(expression[1], command[3])
                    self.code.append(f'STOREI {TEMP_CELL_B}')

                except Exception as e:
                    print(f'Error: Line {command[3]}: {e}')
                    self.errorMode = True

                self.initialize(target)
                  
            elif command[0] == 'write':
                target = command[1]
                if target[0] == 'number':
                    self.code.append(f'SET {target[1]}')
                    self.code.append('PUT 0')
                else: # target[0] == 'load'
                    self.lineno = command[2]
                    try:
                        self.load_value(target[1])
                        self.code.append('PUT 0')
                    except Exception as e:
                        print(f'Error: Line {command[2]}: {e}')
                        self.errorMode = True

            elif command[0] == 'read':
                target = command[1]
                self.lineno = command[2]
                try:
                    self.load_address(target)
                    self.code.append(f'STORE {TEMP_CELL_B}')
                    self.code.append(f'GET 0')
                    self.code.append(f'STOREI {TEMP_CELL_B}')
                except Exception as e:
                    print(f'Error Line: {command[2]}: {e}')
                    self.errorMode = True

                self.initialize(target)

            elif command[0] == 'ifelse':
                condition = command[1]
                (condition, swap) = self.simplify_condition(condition)

                if not swap:
                    block_a = command[2]
                    block_b = command[3]
                else:
                    block_b = command[2]
                    block_a = command[3]
                
                self.generate_condition(condition)

                before_block_a = len(self.code)
                self.code.append('JUMP to block_b')

                self.gen_body(block_a)

                after_block_a = len(self.code)
                self.code.append('JUMP to block_b_end')

                self.gen_body(block_b)

                after_block_b = len(self.code)
                self.code[before_block_a] = f'JUMP {after_block_a - before_block_a + 1}'
                self.code[after_block_a] = f'JUMP {after_block_b - after_block_a}'

            elif command[0] == 'while':
                condition = command[1]
                block = command[2]
                (condition, negation) = self.simplify_condition(condition)
                
                before_condition = len(self.code)
                self.generate_condition(condition)

                if not negation:
                    before_block = len(self.code)
                    self.code.append('JUMP to block end')
                    self.loopDepth += 1
                    self.gen_body(block)
                    self.loopDepth -= 1
                    self.code.append(f'JUMP { before_condition - len(self.code) }')
                    after_block = len(self.code)
                    self.code[before_block] = f'JUMP {after_block - before_block}'
                else: # negation
                    before_block = len(self.code) - 1
                    self.loopDepth += 1
                    self.gen_body(block)
                    self.loopDepth -= 1
                    self.code.append(f'JUMP { before_condition - len(self.code)}')
                    after_block = len(self.code)
                    if condition[1] == '>':
                        self.code[before_block] = f'JPOS {after_block - before_block}'
                    else: # condition[0] =='='
                        self.code[before_block] = f'JZERO {after_block - before_block}'

            elif command[0] == 'repeat':
                condition = command[1]
                block = command[2]
                (condition, negation) = self.simplify_condition(condition)

                block_start = len(self.code)
                self.loopDepth += 1
                self.gen_body(block)
                self.loopDepth -= 1
                
                self.generate_condition(condition)
                if not negation:
                    self.code.append(f'JUMP {block_start - len(self.code)}')
                else: # negation
                    last_jump = len(self.code) - 1
                    if condition[1] == '>':
                        self.code[last_jump] = (f'JPOS {block_start - last_jump}')
                    else: # condition[0] = '='
                        self.code[last_jump] = (f'JZERO {block_start - last_jump}')
            
            elif command[0] == 'for_to':
                iterator = command[1]
                start = command[2]
                end = command[3]
                block = command[4]

                try:
                    self.memory.add_iterator(iterator)
                except Exception as e:
                    print(f'Error: Line {command[5]}: {e}')
                    self.errorMode = True

                iterator_address = self.memory.get_variable(iterator)

                # store initial values of iterator
                if start[0] == 'number':
                    self.code.append(f'SET {start[1]}')
                    self.code.append(f'STORE {iterator_address}')
                else: # load 
                    self.load_value(start[1])
                    self.code.append(f'STORE {iterator_address}')
                
                if end[0] == 'number':
                    self.code.append(f'SET {end[1]}')
                    self.code.append(f'STORE {iterator_address + 1}')
                else: # load
                    self.load_value(end[1])
                    self.code.append(f'STORE {iterator_address + 1}')
              

                condition = ('comparison', '<=', ('load', ('iterator', iterator)), ('load', ('iterator', f'{iterator}_iter_end')) )
                block = command[4]
                (condition, negation) = self.simplify_condition(condition)
                
                before_condition = len(self.code)
                self.generate_condition(condition)

                before_block = len(self.code) - 1
                self.loopDepth += 1
                self.gen_body(block)
                self.loopDepth -= 1
                
                # increment iterator 
                self.code.append(f'SET 1')
                self.code.append(f'ADD {iterator_address}')
                self.code.append(f'STORE {iterator_address}')

                self.code.append(f'JUMP { before_condition - len(self.code)}')
                after_block = len(self.code)
                self.code[before_block] = f'JPOS {after_block - before_block}'
            
                self.memory.delete_iterator(iterator[0])
            
            elif command[0] == 'for_downto':
                iterator = command[1]
                start = command[2]
                end = command[3]
                block = command[4]

                try:
                    self.memory.add_iterator(iterator)
                except Exception as e:
                    print(f'Error: Line {command[5]}: {e}')
                    self.errorMode = True

                iterator_address = self.memory.get_variable(iterator)

                if start[0] == 'number':
                    self.code.append(f'SET {start[1]}')
                    self.code.append(f'STORE {iterator_address}')
                else: # load 
                    self.load_value(start[1])
                    self.code.append(f'STORE {iterator_address}')
                
                if end[0] == 'number':
                    self.code.append(f'SET {end[1]}')
                    self.code.append(f'STORE {iterator_address + 1}')
                else: # load
                    self.load_value(end[1])
                    self.code.append(f'STORE {iterator_address + 1}')
              

                condition = ('comparison', '>=', ('load', ('iterator', iterator)), ('load', ('iterator', f'{iterator}_iter_end')) )
                block = command[4]
                (condition, negation) = self.simplify_condition(condition)
                
                before_condition = len(self.code)
                self.generate_condition(condition)

                before_block = len(self.code) - 1
                self.loopDepth += 1
                self.gen_body(block)
                self.loopDepth -= 1
                
                # decrement iterator 
                self.code.append(f'SET -1')
                self.code.append(f'ADD {iterator_address}')
                self.code.append(f'STORE {iterator_address}')

                self.code.append(f'JUMP { before_condition - len(self.code)}')
                after_block = len(self.code)
                self.code[before_block] = f'JPOS {after_block - before_block}'

                self.memory.delete_iterator(iterator[0])
            
            elif command[0] == 'call':
                name = command[1][0]
                args = command[1][1]
                lineno = command[1][2]

                for arg in args:
                    try:
                        type = self.memory.get_type(arg)
                        self.initialize((type, arg))
                    except:
                        pass

                if not name in self.procedures:
                    print(f"Error: Line {lineno}: undeclared procedure '{name}' (watch out for recursive calls - these are not allowed!)")
                    self.errorMode = True
                    continue
                procedure = self.procedures[name]
                if len(args) != len(procedure.pointers):
                    print(f"Error: Line {lineno}: procedure '{name}' expects: {len(procedure.pointers)} parameter(s), provided: {len(args)}")
                    self.errorMode = True
                    continue
                for i in range(len(args)):
                    type = self.memory.get_type(args[i])
                    if type == 'pointer':
                        type = self.memory.get_pointer_type(args[i])
                    
                    if type != procedure.pointers[i].type:
                        print(f"Error: Line {lineno}: incorect type of argument provided to procedure '{name}'\n\tExpected: '{procedure.pointers[i].type}' but '{type}' was provided")
                        self.errorMode = True
                        continue
                    
                    if type == 'variable':
                        self.load_address((type, args[i]))
                    else: # type == 'array'
                        # load and store lower bound as first memory cell of array
                        self.code.append(f'SET {self.memory.get_variable(args[i])}')
                    
                    self.code.append(f'STORE {procedure.pointers[i].location}')
                
                # saving location for return
                self.code.append(f'SET {len(self.code) + 3}')
                self.code.append(f'STORE {procedure.callback}')
                self.code.append(f'JUMP {procedure.location - len(self.code)}')

    def multiply(self, factor_address1, factor_address2, flag_address = TEMP_CELL_G):
       
        # r30:  multiplicand    factor_address1
        # r31:  multiplier      factor_address2
        # r32:  result          TEMP_CELL_H
        # r37:  negative flag   TEMP_CELL_G

        self.code.append(f'SET 0')
        self.code.append(f'STORE {TEMP_CELL_H}')  # result
        self.code.append(f'SET 1')
        self.code.append(f'STORE {flag_address}')  # negative flag

        # multiplicand flag setup
        self.code.append(f'LOAD {factor_address1}')
        self.code.append(f'JPOS 10')
        self.code.append(f'JZERO 9')
        self.code.append(f'LOAD {flag_address}')
        self.code.append(f'SUB {flag_address}')
        self.code.append(f'SUB {flag_address}')
        self.code.append(f'STORE {flag_address}')

        # flag setup
        self.code.append(f'LOAD {factor_address1}')
        self.code.append(f'SUB {factor_address1}')
        self.code.append(f'SUB {factor_address1}')
        self.code.append(f'STORE {factor_address1}')

        # multiplier flag setup
        self.code.append(f'LOAD {factor_address2}')
        self.code.append(f'JPOS 10')
        self.code.append(f'JZERO 9')
        self.code.append(f'LOAD {flag_address}')
        self.code.append(f'SUB {flag_address}')
        self.code.append(f'SUB {flag_address}')
        self.code.append(f'STORE {flag_address}')

        # make multiplier positive
        self.code.append(f'LOAD {factor_address2}')
        self.code.append(f'SUB {factor_address2}')
        self.code.append(f'SUB {factor_address2}')
        self.code.append(f'STORE {factor_address2}')

        # if multiplicand < multiplier: swap them
        self.code.append(f'LOAD {factor_address1}')
        self.code.append(f'SUB {factor_address2}')
        self.code.append(f'JPOS 10')
        self.code.append(f'LOAD {factor_address1}')
        self.code.append(f'ADD {factor_address2}')
        self.code.append(f'STORE {factor_address1}')
        self.code.append(f'LOAD {factor_address1}')
        self.code.append(f'SUB {factor_address2}')
        self.code.append(f'STORE {factor_address2}')
        self.code.append(f'LOAD {factor_address1}')
        self.code.append(f'SUB {factor_address2}')
        self.code.append(f'STORE {factor_address1}')

        # while multiplier > 0:
        self.code.append(f'LOAD {factor_address2}')
        self.code.append(f'JZERO 17')
        self.code.append(f'JNEG 16')

        # if multiplier % 2 == 1:
        self.code.append(f'LOAD {factor_address2}')
        self.code.append(f'HALF')
        self.code.append(f'ADD 0')
        self.code.append(f'SUB {factor_address2}')
        self.code.append(f'JZERO 4')

        # result = result + multiplicand
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'ADD {factor_address1}')
        self.code.append(f'STORE {TEMP_CELL_H}')

        # multiplicand = multiplicand * 2
        self.code.append(f'LOAD {factor_address1}')
        self.code.append(f'ADD {factor_address1}')
        self.code.append(f'STORE {factor_address1}')

        # multiplier = multiplier / 2
        self.code.append(f'LOAD {factor_address2}')
        self.code.append(f'HALF')
        self.code.append(f'STORE {factor_address2}')

        self.code.append(f'JUMP -17')

        # if flag < 0; change result sign
        self.code.append(f'LOAD {flag_address}')
        self.code.append(f'JPOS 5')
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_H}')
        self.code.append(f'STORE {TEMP_CELL_H}')

        # load result
        self.code.append(f'LOAD {TEMP_CELL_H}')


    def divide(self, dividend_address, divisor_address):

        
        # r30:  dividend            dividend_address    
        # r31:  divisor             divisor_address     


        # r32:  quotient - Q        TEMP_CELL_G = 8     
        # r33:  remainder - R       TEMP_CELL_H = 9  

        # r34:  temp divisor - D    TEMP_CELL_I = 10  

        # r35:  1                   TEMP_CELL_J

        # r36:  multiple - M        TEMP_CELL_K

        # r37:  negative flag       TEMP_CELL_L = 11   


        # setup
        self.code.append(f'SET 1') # 1 to TEMP_CELL_J
        self.code.append(f'STORE {TEMP_CELL_J}') 
        self.code.append(f'SET 1') # negative flag to TEMP_CELL_L
        self.code.append(f'STORE {TEMP_CELL_L}')
        
        # # dividend flag setup
        self.code.append(f'LOAD {dividend_address}') 
        self.code.append(f'JPOS 10') 
        self.code.append(f'JZERO 9')
        self.code.append(f'LOAD {TEMP_CELL_L}') 
        self.code.append(f'SUB {TEMP_CELL_L}')
        self.code.append(f'SUB {TEMP_CELL_L}')
        self.code.append(f'STORE {TEMP_CELL_L}')
        #  dividend pos
        self.code.append(f'LOAD {dividend_address}')
        self.code.append(f'SUB {dividend_address}')
        self.code.append(f'SUB {dividend_address}')
        self.code.append(f'STORE {dividend_address}')
        
        # divisor flag setup
        self.code.append(f'LOAD {divisor_address}') 
        self.code.append(f'JPOS 10')
        self.code.append(f'JZERO 9')
        self.code.append(f'LOAD {TEMP_CELL_L}')
        self.code.append(f'SUB {TEMP_CELL_L}')
        self.code.append(f'SUB {TEMP_CELL_L}')
        self.code.append(f'STORE {TEMP_CELL_L}')
        # make dividend pos
        self.code.append(f'LOAD {divisor_address}')
        self.code.append(f'SUB {divisor_address}') 
        self.code.append(f'SUB {divisor_address}') 
        self.code.append(f'STORE {divisor_address}') 

        # setup Q and R
        self.code.append(f'SET 0') # Q = 0 to r32
        self.code.append(f'STORE {TEMP_CELL_G}')
        self.code.append(f'LOAD {dividend_address}') # R = dividend to r33
        self.code.append(f'STORE {TEMP_CELL_H}')

        # if divisor == 0; return TODO
        self.code.append(f'LOAD {divisor_address}') 
        self.code.append(f'JZERO 32')

        # BEGIN WHILE_2
        # while divisor <= remainder:
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {divisor_address}')
        self.code.append(f'JNEG 23')

        # before loop1
        # temp_divisor = divisor
        self.code.append(f'LOAD {divisor_address}') # D = divisor to r34
        self.code.append(f'STORE {TEMP_CELL_I}')
        # multiple = 1
        self.code.append(f'LOAD {TEMP_CELL_J}')
        self.code.append(f'STORE {TEMP_CELL_K}') # M = 1 to r36
        
        # BEGIN WHILE_1                
        # while temp_divisor * 2 <= remainder:
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_I}')
        self.code.append(f'SUB {TEMP_CELL_I}')
        self.code.append(f'JNEG 8') # if D > R, escape loop
        
        # temp_divisor = temp_divisor * 2
        self.code.append(f'LOAD {TEMP_CELL_I}')
        self.code.append(f'ADD {TEMP_CELL_I}')
        self.code.append(f'STORE {TEMP_CELL_I}')
        
        # multiple = multiple * 2
        self.code.append(f'LOAD {TEMP_CELL_K}')
        self.code.append(f'ADD {TEMP_CELL_K}')
        self.code.append(f'STORE {TEMP_CELL_K}')
        
        # jump back to loop1
        self.code.append(f'JUMP -10')
        # END WHILE_1
        
        # after loop1
        # remainder = remainder - temp_divisor
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_I}')
        self.code.append(f'STORE {TEMP_CELL_H}')
        # quotient = quotient + multiple
        self.code.append(f'LOAD {TEMP_CELL_G}')
        self.code.append(f'ADD {TEMP_CELL_K}')
        self.code.append(f'STORE {TEMP_CELL_G}')
        
        # jump back to loop2
        self.code.append(f'JUMP -24')
        # END WHILE_2
        
        # if flag < 0; change result sign
        self.code.append(f'LOAD {TEMP_CELL_L}')
        self.code.append(f'JPOS 5')
        self.code.append(f'LOAD {TEMP_CELL_G}')
        self.code.append(f'SUB {TEMP_CELL_G}')
        self.code.append(f'SUB {TEMP_CELL_G}')
        self.code.append(f'STORE {TEMP_CELL_G}')

        # return quotient
        self.code.append(f'LOAD {TEMP_CELL_G}')


    def modulo(self, dividend_address, divisor_address):
 
        
        # r30:  dividend dividend_address    
        # r31:  divisor  divisor_address     # calculate_expression


        # r32:  quotient - Q   TEMP_CELL_G = 8     # calculate_expression
        # r33:  remainder - R  TEMP_CELL_H = 9     # calculate_expression

        # r34:  temp divisor - D  TEMP_CELL_I = 10    # calculate_expression

        # r35:  1 TEMP_CELL_J

        # r36:  multiple - M TEMP_CELL_K

        # r37:  negative flag
        # TEMP_CELL_L = 11    # calculate_expression


        # setup
        self.code.append(f'SET 1') # 1 to TEMP_CELL_J
        self.code.append(f'STORE {TEMP_CELL_J}') 
        self.code.append(f'SET 1') # negative flag to TEMP_CELL_L
        self.code.append(f'STORE {TEMP_CELL_L}')
        
        # # dividend flag setup
        self.code.append(f'LOAD {dividend_address}') 
        self.code.append(f'JPOS 6')
        self.code.append(f'JZERO 5')
       
        #  dividend pos
        self.code.append(f'LOAD {dividend_address}')
        self.code.append(f'SUB {dividend_address}')
        self.code.append(f'SUB {dividend_address}')
        self.code.append(f'STORE {dividend_address}')
        
        #flag setup
        self.code.append(f'LOAD {divisor_address}') 
        self.code.append(f'JPOS  10')
        self.code.append(f'JZERO  9')
        self.code.append(f'LOAD {TEMP_CELL_L}')
        self.code.append(f'SUB {TEMP_CELL_L}')
        self.code.append(f'SUB {TEMP_CELL_L}')
        self.code.append(f'STORE {TEMP_CELL_L}')
        # make dividend pos
        self.code.append(f'LOAD {divisor_address}')
        self.code.append(f'SUB {divisor_address}') 
        self.code.append(f'SUB {divisor_address}') 
        self.code.append(f'STORE {divisor_address}') 

        # setup Q and R
        self.code.append(f'SET  0') # Q = 0 to r32
        self.code.append(f'STORE {TEMP_CELL_G}')
        self.code.append(f'LOAD {dividend_address}') # R = dividend to r33
        self.code.append(f'STORE {TEMP_CELL_H}')

        # if divisor == 0; return TODO
        self.code.append(f'LOAD {divisor_address}') 
        self.code.append(f'JZERO 32')

        # BEGIN WHILE_2
        # while divisor <= remainder:
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {divisor_address}')
        self.code.append(f'JNEG 23')

        # before loop1
        # temp_divisor = divisor
        self.code.append(f'LOAD {divisor_address}') # D = divisor to r34
        self.code.append(f'STORE {TEMP_CELL_I}')
        # multiple = 1
        self.code.append(f'LOAD {TEMP_CELL_J}')
        self.code.append(f'STORE {TEMP_CELL_K}') # M = 1 to r36
        
        # BEGIN WHILE_1                
        # while temp_divisor * 2 <= remainder:
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_I}')
        self.code.append(f'SUB {TEMP_CELL_I}')
        self.code.append(f'JNEG  8') # if D > R, escape loop
        
        # temp_divisor = temp_divisor * 2
        self.code.append(f'LOAD {TEMP_CELL_I}')
        self.code.append(f'ADD {TEMP_CELL_I}')
        self.code.append(f'STORE {TEMP_CELL_I}')
        
        # multiple = multiple * 2
        self.code.append(f'LOAD  {TEMP_CELL_K}')
        self.code.append(f'ADD {TEMP_CELL_K}')
        self.code.append(f'STORE  {TEMP_CELL_K}')
        
        # jump back to loop1
        self.code.append(f'JUMP -10')
        # END WHILE_1
        
        # after loop1
        # remainder = remainder - temp_divisor
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_I}')
        self.code.append(f'STORE {TEMP_CELL_H}')
        # quotient = quotient + multiple
        self.code.append(f'LOAD {TEMP_CELL_G}')
        self.code.append(f'ADD {TEMP_CELL_K}')
        self.code.append(f'STORE {TEMP_CELL_G}')
        
        # jump back to loop2
        self.code.append(f'JUMP -24')
        # END WHILE_2
        
        # if flag < 0; change result sign
        self.code.append(f'LOAD  {TEMP_CELL_L}')
        self.code.append(f'JPOS 5')
        self.code.append(f'LOAD {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_H}')
        self.code.append(f'SUB {TEMP_CELL_H}')
        self.code.append(f'STORE {TEMP_CELL_H}')

        # return remainder
        self.code.append(f'LOAD {TEMP_CELL_H}')


    def generate_condition(self, condition):
        operator = condition[1]
        first_value = condition[2]
        second_value = condition[3]


        if first_value[0] == 'number':
            self.code.append(f'SET  {first_value[1]}')
            self.code.append(f'STORE {TEMP_CELL_C}')
        else: #first_value[0] == 'load'
            self.load_value(first_value[1])
            self.code.append(f'STORE {TEMP_CELL_C}')
        
        if second_value[0] == 'number':
            self.code.append(f'SET  {second_value[1]}')
            self.code.append(f'STORE {TEMP_CELL_D}')
        else: #second_value[0] == 'load'
            self.load_value(second_value[1])
            self.code.append(f'STORE {TEMP_CELL_D}')
        
        if operator == '>':
            self.code.append(f'LOAD {TEMP_CELL_C}')
            self.code.append(f'SUB  {TEMP_CELL_D}')
            self.code.append(f'JPOS 2')

        elif operator == '=':
            self.code.append(f'LOAD  {TEMP_CELL_C}')
            self.code.append(f'SUB   {TEMP_CELL_D}')
            self.code.append(f'JZERO 2')


    def simplify_condition(self, condition):
        operator = condition[1]
        first_value = condition[2]
        second_value = condition[3]

        if operator == '=':
            return condition, False
        elif operator == '!=':
            return ('comparison', '=', first_value, second_value), True
        elif operator == '>':
            return condition, False
        elif operator == '<':
            return ('comparison', '>', second_value, first_value), False
        elif operator == '>=':
            return ('comparison', '>', second_value, first_value), True
        else: # operator == '<='
            return ('comparison', '>', first_value, second_value), True

    # result to accumulator
    def calculate_expression(self, expression, lineno):
        # single argument expressions:
        if expression[0] == 'load' and self.notInitialized(expression[1]):
            if self.loopDepth == 0:
                print(f"Error: Line {lineno}: variable '{expression[1][1]}' not initialized")
                self.errorMode = True
            else:
                print(f"Warning: Line {lineno}: variable '{expression[1][1]}' may be not initialized")
        
        if expression[0] == "number":
            self.code.append(f'SET {expression[1]}') # load number

        elif expression[0] == "load":
            self.load_value(expression[1]) #  load variable value
        
        # double argument expressions:
        else:
            operation = expression[0]
            first_arg = expression[1]
            second_arg = expression[2]

            if first_arg[0] == 'load' and self.notInitialized(first_arg[1]):
                if self.loopDepth == 0:
                    print(f"Error: Line {lineno}: variable '{first_arg[1][1]}' not initialized")
                    self.errorMode = True
                else:
                    print(f"Warning: Line {lineno}: variable '{first_arg[1][1]}' may be not initialized")

            if second_arg[0] == 'load' and self.notInitialized(second_arg[1]):
                if self.loopDepth == 0:
                    print(f"Error: Line {lineno}: variable '{second_arg[1][1]}' not initialized")
                    self.errorMode = True
                else:
                    print(f"Warning: Line {lineno}: variable '{second_arg[1][1]}' may be not initialized")

            # two numbers
            if first_arg[0] == 'number' and second_arg[0] == 'number':
                if operation == '+':
                    result = first_arg[1] + second_arg[1]
                elif operation == '-':
                    result = first_arg[1] - second_arg[1]
                elif operation == '*':
                    result = first_arg[1] * second_arg[1]
                elif operation == '/':
                    if second_arg[1] == 0:
                        result = 0
                    else:
                        result = first_arg[1] // second_arg[1]
                else: # operation == '%:
                    if second_arg[1] == 0:
                        result = 0
                    else:
                        result = first_arg[1] % second_arg[1]

                self.code.append(f'SET {result}')

            # at least one variable/array
            else:

                # special cases
                if (first_arg[0] == 'number' and second_arg[0] == 'load') or (first_arg[0] == 'load' and second_arg[0] == 'number'):
                    if first_arg[0] == 'number':
                        num_arg = first_arg
                        var_arg = second_arg
                    else:
                        num_arg = second_arg
                        var_arg = first_arg
                        
                        # efficient division by 2
                        if num_arg[1] == 2 and operation == '/':
                            self.load_value(var_arg[1])
                            self.code.append('HALF')
                            return
                    

                    # efficient multiplication by 2
                    if num_arg[1] == 2 and operation == '*':
                        self.load_value(var_arg[1])
                        self.code.append(f'ADD 0')
                        return

                # load second value
                if second_arg[0] == 'number':
                    self.code.append(f'SET {second_arg[1]}')
                    self.code.append(f'STORE {TEMP_CELL_F}')
                else: #second_arg[0] == 'load'
                    self.load_value(second_arg[1])
                    self.code.append(f'STORE {TEMP_CELL_F}')
                
                # load first value
                if first_arg[0] == 'number':
                    self.code.append(f'SET {first_arg[1]}')
                    self.code.append(f'STORE {TEMP_CELL_E}')
                else: #first_arg[0] == 'load'
                    self.load_value(first_arg[1])
                    self.code.append(f'STORE {TEMP_CELL_E}')

                if operation == '+':
                    self.code.append(f'ADD {TEMP_CELL_F}') # since first still in accu
                
                elif operation == '-':
                    self.code.append(f'SUB {TEMP_CELL_F}') # since first still in accu

                elif operation == '*':
                    self.multiply(factor_address1=TEMP_CELL_E, factor_address2=TEMP_CELL_F)

                else: # operation == '/' or operation == '%'
                    if operation == '/':
                        self.divide(dividend_address=TEMP_CELL_E, divisor_address=TEMP_CELL_F)
                    else: # operation == '%'
                        self.modulo(dividend_address=TEMP_CELL_E, divisor_address=TEMP_CELL_F)


    # load address to accumulator
    def load_address(self, memory_cell, temp_address = TEMP_CELL_M):
        if memory_cell[0] == 'number':
            raise Exception('can not load address of literal')
        elif memory_cell[0] == 'variable' or memory_cell[0] == 'iterator':
            address = self.memory.get_variable(memory_cell[1])

            if isinstance(self.memory[memory_cell[1]], Array):
                raise Exception(f"'{memory_cell[1]}' is array, consider: '{memory_cell[1]}[INDEX]'")

            # pointers 
            if self.memory.is_pointer(memory_cell[1]):
                self.code.append(f'LOAD {address}')
                return
            
            self.code.append(f'SET {address}')
        else: # memory_cell[0] == 'array'
            index = memory_cell[2]

            if index[0] == 'load':
                var = index[1]
                if var in self.memory and isinstance(self.memory[var], Variable) and not self.memory[var].initialized:
                    if self.loopDepth == 0:
                        print(f"Error: Line {self.lineno}: variable '{var}' not initialized")
                        self.errorMode = True
                    else:
                        print(f"Warning: Line {self.lineno}: variable '{var}' may be not initialized")
                
                if var in self.memory and isinstance(self.memory[var], Iterator) and not self.memory[var].active:
                    print(f"Error: Line {self.lineno}: trying to access local iterator '{var}' that went out out scope")
                    self.errorMode = True
            
            
            # pointer to array
            if self.memory.is_array_pointer(memory_cell[1]):
                
                pointer_address = self.memory.get_variable(memory_cell[1])

                if index[0] == 'number':
                    # load value from first cell of array (lower_bound)
                    self.code.append(f'LOADI {pointer_address}')
                    self.code.append(f'STORE {temp_address}')
                    # load index value
                    self.load_value(index)
                    # substract lower bound
                    self.code.append(f'SUB {temp_address}')
                    self.code.append(f'STORE {temp_address}')
                    # add array's start address + 1
                    self.code.append(f'SET 1')
                    self.code.append(f'ADD {pointer_address}')
                    self.code.append(f'ADD {temp_address}')

                else: # index[0] == 'load'

                    # load value from first cell of array (lower_bound)
                    self.code.append(f'LOADI {pointer_address}')
                    self.code.append(f'STORE {temp_address}')

                    # index is pointer
                    if self.memory.is_pointer(index[1]):
                        self.load_value((self.memory.get_pointer_type(index[1]), index[1]))
                        # substract lower bound                        
                        self.code.append(f'SUB {temp_address}')
                        self.code.append(f'STORE {temp_address}')
                        # add array's start address + 1
                        self.code.append(f'SET 1')
                        self.code.append(f'ADD {pointer_address}')
                        self.code.append(f'ADD {temp_address}')

                    # simple variable / iterator
                    else:
                        self.load_value((self.memory.get_type(index[1]), index[1]))
                        # substract lower bound                        
                        self.code.append(f'SUB {temp_address}')
                        self.code.append(f'STORE {temp_address}')
                        # add array's start address + 1
                        self.code.append(f'SET 1')
                        self.code.append(f'ADD {pointer_address}')
                        self.code.append(f'ADD {temp_address}')

            # local array
            else:
                if index[0] == 'number':
                    address = self.memory.get_array_at_index(memory_cell[1], index[1])
                    self.code.append(f'SET {address}')
                else: # index[0] == 'load'

                    if self.memory.is_pointer(index[1]):
                        array_address = self.memory.get_array_at_index(memory_cell[1], 0, get_array_start_location=True)
                        # load and store lower bound of array
                        self.code.append(f'LOAD {array_address}')
                        self.code.append(f'STORE {temp_address}')
                        # load value of 'offset value' pointer
                        self.load_value((self.memory.get_pointer_type(index[1]), index[1]))
                        # substract lower bound
                        self.code.append(f'SUB {temp_address}')
                        self.code.append(f'STORE {temp_address}')
                        # add base address + 1
                        self.code.append(f'SET {array_address + 1}')
                        self.code.append(f'ADD {temp_address}')
                    else:
                        # get start address of array in memory
                        array_address = self.memory.get_array_at_index(memory_cell[1], 0,  get_array_start_location=True)
                        # first load and store array's !lower bound value!
                        self.code.append(f'LOAD {array_address}')
                        self.code.append(f'STORE {temp_address}')
                        # walkaround to get value of index (it's just PID, so we take it from memory)
                        memory_cell = (self.memory.get_type(index[1]), index[1])
                        self.load_value(memory_cell)
                        # substract lower bound
                        self.code.append(f'SUB {temp_address}')
                        self.code.append(f'STORE {temp_address}')
                        # add base address + 1
                        self.code.append(f'SET {array_address + 1}')
                        self.code.append(f'ADD {temp_address}')
                        # load proper address to acc

    
    # load value from memory to accumulator
    def load_value(self, memory_cell, temporary_address = TEMP_CELL_V):
        if memory_cell[0] == 'number':
            self.code.append(f'SET {memory_cell[1]}')
        elif memory_cell[0] == 'variable' or memory_cell[0] == 'iterator':
            address = self.memory.get_variable(memory_cell[1])

            if isinstance(self.memory[memory_cell[1]], Array):
                raise Exception(f'{memory_cell[1]} is an array')

            # pointer 
            if self.memory.is_pointer(memory_cell[1]):
                self.code.append(f'LOADI {address}')
                return

            # non pointer
            self.code.append(f'LOAD {address}')
        else: # memory_cell[0] == 'array'
            index = memory_cell[2]

            if index[0] == 'load':
                var = index[1]
                if var in self.memory and isinstance(self.memory[var], Variable) and not self.memory[var].initialized:
                    if self.loopDepth == 0:
                        print(f"Error: Line {self.lineno}: variable '{var}' not initialized")
                        self.errorMode = True
                    else:
                        print(f"Warning: Line {self.lineno}: variable '{var}' may be not initialized")

                if var in self.memory and isinstance(self.memory[var], Iterator) and not self.memory[var].active:
                    print(f"Error: Line {self.lineno}: trying to access local iterator '{var}' that went out out scope")
                    self.errorMode = True
            
            # pointer to array
            if self.memory.is_array_pointer(memory_cell[1]):

                pointer_address = self.memory.get_variable(memory_cell[1])

                if index[0] == 'number':
                    # first load and store array's !lower bound value!
                    self.code.append(f'LOADI {pointer_address}')
                    self.code.append(f'STORE {temporary_address}')
                    self.load_value(index)
                    # substract lower bond
                    self.code.append(f'SUB {temporary_address}')
                    self.code.append(f'STORE {temporary_address}')
                    # add array address + 1
                    self.code.append(f'SET 1')
                    self.code.append(f'ADD {temporary_address}')
                    self.code.append(f'STORE {temporary_address}')
                    self.code.append(f'LOAD {pointer_address}') # array address
                    self.code.append(f'ADD {temporary_address}')
                    self.code.append(f'LOADI 0')
                
                else: # index[0] == 'load'
                    # index is pointer
                    if self.memory.is_pointer(index[1]):
                        # first load and store array's !lower bound value!
                        self.code.append(f'LOADI {pointer_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # load value of offset value pointer
                        self.load_value((self.memory.get_pointer_type(index[1]), index[1]))
                        # substract lower bond
                        self.code.append(f'SUB {temporary_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # add array address + 1
                        self.code.append(f'SET 1')
                        self.code.append(f'ADD {temporary_address}')
                        self.code.append(f'STORE {temporary_address}')
                        self.code.append(f'LOAD {pointer_address}') # array address
                        self.code.append(f'ADD {temporary_address}')
                        self.code.append(f'LOADI 0')
                    else: # simple variable / iterator
                        # first load and store array's !lower bound value!
                        self.code.append(f'LOADI {pointer_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # load value of offset value pointer
                        self.load_value((self.memory.get_type(index[1]), index[1]))
                        # substract lower bond
                        self.code.append(f'SUB {temporary_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # add array address + 1
                        self.code.append(f'SET 1')
                        self.code.append(f'ADD {temporary_address}')
                        self.code.append(f'STORE {temporary_address}')
                        self.code.append(f'LOAD {pointer_address}') # array address
                        self.code.append(f'ADD {temporary_address}')
                        self.code.append(f'LOADI 0')
            
            else: # local array
                if index[0] == 'number':
                    #  indexes by literal value are handled by function -> no need for manual work
                    address = self.memory.get_array_at_index(memory_cell[1], index[1])
                    self.code.append(f'LOAD {address}')
                else: # index[0] == 'load'

                    array_address = self.memory.get_array_at_index(memory_cell[1], 0, get_array_start_location=True)
                    
                    # pointer
                    if self.memory.is_pointer(index[1]):
                        # first load and store array's !lower bound value!
                        self.code.append(f'LOAD {array_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # load value of 'offset value' pointer
                        self.load_value((self.memory.get_pointer_type(index[1]), index[1]))
                        # substract by !lower bound value!
                        self.code.append(f'SUB {temporary_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # then add array's start address + 1
                        self.code.append(f'SET {array_address + 1}')
                        self.code.append(f'ADD {temporary_address}')
                        # load value from address stored in acc (like pointer)
                        self.code.append(f'LOADI 0')
                    
                    else: # simple variable / iterator                        
                        # first load and store array's !lower bound value!
                        self.code.append(f'LOAD {array_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # walkaround to get !value of index! (it's just PID, so we take it from memory)
                        self.load_value((self.memory.get_type(index[1]), index[1]), temporary_address=TEMP_CELL_V2)
                        # substract by !lower bound value!
                        self.code.append(f'SUB {temporary_address}')
                        self.code.append(f'STORE {temporary_address}')
                        # then add array's start address + 1
                        self.code.append(f'SET {array_address + 1}')
                        self.code.append(f'ADD {temporary_address}')
                        # load value from address stored in acc (like pointer)
                        self.code.append(f'LOADI 0')



    def initialize(self, target):
        if target[0] != 'variable':
            return
        name = target[1]

        if name in self.memory:
                    if isinstance(self.memory[name], Variable):
                        self.memory[name].initialized = True

    def notInitialized(self, target):
        if target[0] != 'variable':
            return False
        name = target[1]

        if name in self.memory:
                    if isinstance(self.memory[name], Variable):
                        return not self.memory[name].initialized