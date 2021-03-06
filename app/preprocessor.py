import ply.lex as lex
import ply.yacc as yacc
import re

# Classes
class Program(object):
    def __init__(self, items):
        self.items = items
    def get_lookup(self):
        return dict((item.name, item) for item in self.items
            if isinstance(item, MacroDefinition))
    def preprocess(self, lookup):
        items = []
        count = 0
        line = 1
        for item in self.items:
            newlines = item.line - line
            if newlines:
                items.append('\n' * (newlines))
                line = item.line
            if isinstance(item, MacroCall):
                if item.name not in lookup:
                    raise Exception('Call to undefined macro: %s'
                        % item.name)
                macro = lookup[item.name]
                items.extend(macro.invoke(item.arguments))
                count += 1
            elif isinstance(item, Token):
                if item.name in lookup:
                    macro = lookup[item.name]
                    items.extend(macro.invoke(()))
                    count += 1
                else:
                    items.append(item.name)
        lines = ' '.join(items).split('\n')
        result = '\n'.join(line.strip() for line in lines)
        return count, result

class MacroDefinition(object):
    def __init__(self, line, name, parameters, tokens):
        self.line = line
        self.name = name
        self.parameters = parameters
        self.tokens = tokens
    def invoke(self, arguments):
        if len(arguments) != len(self.parameters):
            raise Exception('Incorrect number of arguments for macro: %s'
                % self.name)
        lookup = dict(zip(self.parameters, arguments))
        tokens = []
        for token in self.tokens:
            tokens.extend(lookup.get(token.name, [token]))
        result = [token.name for token in tokens]
        return result

class MacroCall(object):
    def __init__(self, line, name, arguments):
        self.line = line
        self.name = name
        self.arguments = arguments

class Token(object):
    def __init__(self, line, name):
        self.line = line
        self.name = name

# Lexer Rules
tokens = [
    'MACRO',
    'COMMA',
    'LBRACE',
    'RBRACE',
    'LBRACK',
    'RBRACK',
    'LPAREN',
    'RPAREN',
    'STRING',
    'ID',
    'OTHER',
]

t_ignore = ' \t\r'
t_ignore_COMMENT = r';.*'

t_MACRO = r'\#macro'
t_COMMA = r'\,'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACK = r'\['
t_RBRACK = r'\]'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_STRING = r'"[^"]*"'
t_ID = r'[_a-zA-Z][_a-zA-Z0-9]*'
t_OTHER = r'[^_a-zA-Z\s\;\,\{\}\[\]\(\)\"\#][^\s\;\,\{\}\[\]\(\)\"\#]*'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    raise Exception(t)

# Parser Rules
def p_program(t):
    'program : items'
    t[0] = Program(t[1])

def p_items1(t):
    'items : item items'
    t[0] = (t[1],) + t[2]

def p_items2(t):
    'items : item'
    t[0] = (t[1],)

def p_item(t):
    '''item : macro_definition
            | macro_call
            | token'''
    t[0] = t[1]

def p_macro_definition(t):
    'macro_definition : MACRO ID parameter_list LBRACE tokens RBRACE'
    t[0] = MacroDefinition(t.lineno(1), t[2], t[3], t[5])

def p_parameter_list1(t):
    'parameter_list : LPAREN parameters RPAREN'
    t[0] = t[2]

def p_parameter_list2(t):
    'parameter_list : empty'
    t[0] = ()

def p_parameters1(t):
    'parameters : ID COMMA parameters'
    t[0] = (t[1],) + t[3]

def p_parameters2(t):
    'parameters : ID'
    t[0] = (t[1],)

def p_macro_call(t):
    'macro_call : ID argument_list'
    t[0] = MacroCall(t.lineno(1), t[1], t[2])

def p_argument_list1(t):
    'argument_list : LPAREN arguments RPAREN'
    t[0] = t[2]

def p_argument_list2(t):
    'argument_list : empty'
    t[0] = ()

def p_arguments1(t):
    'arguments : argument COMMA arguments'
    t[0] = (t[1],) + t[3]

def p_arguments2(t):
    'arguments : argument'
    t[0] = (t[1],)

def p_argument1(t):
    'argument : argument_token argument'
    t[0] = (t[1],) + t[2]

def p_argument2(t):
    'argument : argument_token'
    t[0] = (t[1],)

def p_argument_token(t):
    '''argument_token : LBRACK
                      | RBRACK
                      | STRING
                      | ID
                      | OTHER'''
    t[0] = Token(t.lineno(1), t[1])

def p_tokens1(t):
    'tokens : token tokens'
    t[0] = (t[1],) + t[2]

def p_tokens2(t):
    'tokens : token'
    t[0] = (t[1],)

def p_token(t):
    '''token : COMMA
             | LBRACK
             | RBRACK
             | LPAREN
             | RPAREN
             | STRING
             | ID
             | OTHER'''
    t[0] = Token(t.lineno(1), t[1])

def p_empty(t):
    'empty :'
    pass

def p_error(t):
    raise Exception(t)

# Preprocessor Functions
def create_lexer():
    lexer = lex.lex()
    return lexer

def create_parser():
    parser = yacc.yacc(debug=False, write_tables=False)
    return parser

LEXER = create_lexer()
PARSER = create_parser()

def include_files(text):
    lines = []
    pattern = re.compile(r'\#include\s+\"([^"]+)\"')
    for line in text.split('\n'):
        match = pattern.match(line.strip())
        if match is None:
            lines.append(line)
        else:
            path = match.group(1)
            with open(path) as fp:
                lines.extend(fp.read().split('\n'))
    result = '\n'.join(lines)
    return result

def convert_defines(text):
    lines = []
    pattern = re.compile(r'\#define\s+([_a-zA-Z][_a-zA-Z0-9]*)\s+(.+)')
    for line in text.split('\n'):
        match = pattern.match(line.strip())
        if match is None:
            lines.append(line)
        else:
            name = match.group(1)
            value = match.group(2)
            macro = '#macro %s { %s }' % (name, value)
            print macro
            lines.append(macro)
    result = '\n'.join(lines)
    return result

def preprocess(text):
    text = convert_defines(text)
    lookup = None
    while True:
        LEXER.lineno = 1
        program = PARSER.parse(text)
        if lookup is None:
            lookup = program.get_lookup()
        count, text = program.preprocess(lookup)
        if count == 0:
            break
    return text

def preprocess_file(path):
    with open(path) as fp:
        text = fp.read()
    return preprocess(text)
