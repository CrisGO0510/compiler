import sys
from lark import Lark, tree, Tree, Token

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

    expr: term (("+" | "-") term)*  // Expresiones con suma y resta
    term: factor (("*" | "/") factor)*  // Expresiones con multiplicación y división
    factor: func_call               // Llamadas a funciones
        | word                    // Identificadores
        | NUMBER                  // Números
        | "(" expr ")"            // Agrupación

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

def get_operator_name(operator):
    # Diccionario que mapea operadores a nombres
    operator_map = {
        '+': 'add',
        '-': 'sub',
        '*': 'mul',
        '/': 'sdiv',
    }
    
    # Devolver el nombre correspondiente al operador
    return operator_map.get(operator, 'unknown')  # Devuelve 'unknown' si el operador no está en el diccionario


temp_var_counter = 2 # Contador para las variables temporales (2 porque %1 esta reservado)

def get_temp_var():
    global temp_var_counter
    temp_var_counter += 1
    return f"%{temp_var_counter - 1}"

def get_property(node, property_name):
    for child in node.children:
        # Verifica si el nodo es un Tree o un Token
        if isinstance(child, Tree):
            if child.data == property_name:  # Si es un Tree, accedes a 'data'
                return child
        elif isinstance(child, Token):
            if child.type == property_name:  # Si es un Token, accedes a 'type'
                return child
    return None

# Función para traducir el AST a código LLVM
def translate_program(ast, out):
    if ast.data == "start":
        for index, child in enumerate(ast.children):
            if child.data == "funcdef":
                translate_funcdef(child, out, index)

arg_names = []

def translate_funcdef(ast, out, index):
    # Extrae el nombre de la función
    name = get_property(ast, "name")  # Obtiene el nodo hijo con nombre "name"
    function_name = name.children[0].children[0].value

    # Extrae los nombres de los argumentos
    arguments = get_property(ast, "args")
    global arg_names
    arg_names = [[arg.children[0].value, get_temp_var()] for arg in arguments.children]
    
    print("arg_names:", arg_names)

    # Escribir la definición de la función

    out.write("define dso_local i32 @")
    out.write(function_name)

    # Escribimos los argumentos
    out.write("(")
    for i, arg in enumerate(arg_names):
        out.write("i32 noundef ")
        out.write(arg[1])
        if i < len(arg_names) - 1:
            out.write(", ")
    out.write(")")
    out.write(" #")
    out.write(str(index))
    out.write(" {\nwrite:\n")

    # Reservamos la memoria de los argumentos y creamos los apuntadores
    for arg in arg_names:
        out.write("\t")
        temp_var = get_temp_var()
        out.write(temp_var)
        out.write(" = alloca i32, align 4\n")
        out.write("\tstore i32 ")
        out.write(arg[1])
        out.write(", ptr ")
        out.write(temp_var)
        out.write(", align 4\n")
        # Actualizamos el valor de la variable temporal, ya que no podemos usar el argumento como variable
        arg[1] = temp_var


    block = get_property(ast, "block")
    for child in block.children:
        if child.data == "statement":
            translate_statement(child, out)

    out.write("}\n")
    global temp_var_counter
    temp_var_counter = 2
    arg_names = []


def translate_statement(statement, out):
    if statement.children[0].data == "return_stmt":
        translate_return_stmt(statement.children[0], out)
    # elif ast.data == "if_stmt":
    #     translate_if_stmt(ast, out)
    # elif ast.data == "expr":
    #     translate_expr(ast, out)

def traverse_expression(exp, translated_expressions):
    for e in exp:
        if isinstance(e, list):
            # Llamada recursiva, pasando `translated_expressions` como parámetro
            traverse_expression(e, translated_expressions)
            print("List:", e)

            for arg in translated_expressions:
                print("ARG:", arg[0])
                if arg[0] in e:
                    print("AAAAAAAA:", arg)
                    e[e.index(arg[0])] = arg[1]

            translated_expressions.append([e, get_temp_var()])


def translate_return_stmt(return_stmt, out):
    expr_children = get_property(return_stmt, "expr")
    return_expr = translate_expr(expr_children, out)
    print("Return statement:", return_expr)

    transformed_expressions = []

    traverse_expression([return_expr], transformed_expressions)
    print("translated_expressions:", transformed_expressions)

    for expr in transformed_expressions:
        if len(expr[0]) == 3:
            out.write(f"\t{expr[1]} = {get_operator_name(expr[0][1])} nsw i32 {expr[0][0]}, {expr[0][2]}\n")

    # Obtener la última expresión transformada
    final_var = transformed_expressions[-1][1] if transformed_expressions else None

    if final_var:
        out.write(f"\tret i32 {final_var}\n")

    # out.write(f"\t{temp_var} = load i32, ptr {var}, align 4\n")



def translate_expr(expr, out):
    expr_def = []
    for child in expr.children:
        if isinstance(child, Tree):  # Es un "term"
            print("Esta expresión es un árbol (Tree):", child.data)
            expr_def.append(translate_term(child, out))

        elif isinstance(child, Token):  # Es un operador de suma o resta
            print("Esta expresión es un token (Token):")
            print("\tTipo:", child.type)  # Ejemplo: PLUS
            print("\tValor:", child.value)  # Ejemplo: "+"
            expr_def.append(child.value)
        else:
            print("Tipo inesperado de expresión:", type(child))

    # print("EEEEEE:", expr_def)
    return expr_def

def translate_term(term, out):
    term_def = []
    for child in term.children:
        if isinstance(child, Tree):  # Es un "factor"
            print("Este término es un árbol (Tree):", child.data)
            term_def.append(translate_factor(child, out))
        elif isinstance(child, Token): # Es un operador de multiplicación o división
            print("Este término es un token (Token):")
            print("\tTipo:", child.type)
            print("\tValor:", child.value)
            term_def.append(child.value)
        else:
            print("Tipo inesperado de término:", type(child))

    # print("AAAAAAAA:", term_def)
    if len(term_def) == 1:
        return term_def[0]
    
    return term_def

def translate_factor(factor, out):
    global arg_names

    for child in factor.children:
        if isinstance(child, Tree):
            if child.data == "func_call":
                # Manejo de llamadas a funciones
                funcname = get_property(child, "name")
                args = get_property(child, "expr")
                translate_expr(args, out)

            elif child.data == "word":
                # Buscar el nombre de la variable en los argumentos
                variable_name = child.children[0].value
                for arg in arg_names:
                    if arg[0] == variable_name:
                        var = arg[1]  # Apuntador actual del argumento

                # Generar nueva variable temporal para la carga
                temp_var = get_temp_var()
                out.write(f"\t{temp_var} = load i32, ptr {var}, align 4\n")
                return temp_var  # Devuelve el nuevo nombre temporal generado

            elif child.data == "expr":
                return translate_expr(child, out)

        elif isinstance(child, Token):
            if child.type == "NUMBER":
                return child.value

    return None  # Por defecto, si no encuentra nada

input = sys.argv[1]
output = sys.argv[1] + str(".ll")
print("Input file: ", input)
parser = Lark(c_grammar, start='start', keep_all_tokens=True)

with open(input) as inputFile:
    with open(output, 'w') as out:
        ast = parser.parse(inputFile.read())
        print(ast.pretty())
        tree.pydot__tree_to_png(ast, "tree.png")
        tree.pydot__tree_to_dot(ast, "tree.dot", rankdir="TD")
        translate_program(ast, out)