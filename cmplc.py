import sys
from lark import Lark, tree

if(len(sys.argv) != 2):
    print(r'''
          // Wrong number of parameters!      \\
          \\ python hlogoc.py inputfile.hlogo //
          -------------------------------------
          \   ^__^ 
          \  (oo)\_______
             (__)\       )\/\\
                 ||----w |
                 ||     ||
        ''')
    
c_grammar = r"""
    start: funcdef+

    // Definición de la función
    funcdef: "function" funcname "(" args ")" "{" block "}"

    args: (word ("," word)*)?

    block: (statement)*

    statement: return_stmt
            | if_stmt
            | expr ";"        // Expresión como statement (e.g., llamadas a funciones)
            | ";"             // Para permitir líneas vacías

    if_stmt: "if" "(" condition ")" "{" block "}"
          | "if" "(" condition ")" "{" block "}" "else" "{" block "}"

    condition: expr ("==" | "!=" | "<" | ">" | "<=" | ">=") expr

    return_stmt: "return" expr ";"

    expr: func_call        // Llamada a una función
        | word             // Identificadores
        | NUMBER           // Números

    func_call: funcname "(" (expr ("," expr)*)? ")" // Soporte para argumentos en llamadas a funciones

    funcname: word -> name

    // Defino la palabra con números
    word: CNAME_WITH_NUMBER

    // Expresión regular para las palabras
    CNAME_WITH_NUMBER: /[a-zA-Z]+[a-zA-Z0-9]*/

    // Regla para números
    NUMBER: /[0-9]+/

    %ignore " "       // Ignorar espacios simples
    %ignore /\r?\n/   // Ignorar saltos de línea

"""

# This function will traverse the AST and you can use it to emit the 
# code you want at every node of it.
def translate_program(ast, out):
    print("Tree node", ast)
    if ast.data == "start":
        out.write("import turtle\n")
        out.write("t = turtle.Turtle()\n")
        # Call the method recursively to visit the children
        for c in ast.children:
            translate_program(c, out)
        out.write("turtle.mainloop() \n")
        
    elif ast.data == "basic_instruction":
        # This will be run when the node is a basic_instruction
        [left, right] = ast.children
        #out.write(left.data + " " + right.data)
        if left.value == "FD":
            out.write("t.forward(")
            out.write(right.value)
            out.write(")\n")
    else:
        # No implementation fro the node was found
        print("There is nothing to do for ast node ", ast)


# def translate_funcdef

input = sys.argv[1]
output = sys.argv[1] + str(".py")
print("Input file: ", input)
parser = Lark(c_grammar)

with open(input) as inputFile:
    with open(output, 'w') as out:
        ast = parser.parse(inputFile.read())
        print(ast.pretty())
        tree.pydot__tree_to_png(ast, "tree.png")
        tree.pydot__tree_to_dot(ast, "tree.dot", rankdir="TD")
        translate_program(ast, out)