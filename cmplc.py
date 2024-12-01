import sys
import re
from lark import Lark, tree, Tree, Token


if(len(sys.argv) != 2):
    print(r'''
          // Wrong number of parameters!\\
          \\ python cmplc.py program.src//
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
    %ignore /\/\/.*/

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


def get_comparison_operator_name(operator):
    # Diccionario que mapea operadores de comparación a nombres
    comparison_operator_map = {
        '==': 'icmp eq',
        '!=': 'icmp ne',
        '<': 'icmp slt',
        '>': 'icmp sgt',
        '<=': 'icmp sle',
        '>=': 'icmp sge',
    }
    # Devolver el nombre correspondiente al operador de comparación
    return comparison_operator_map.get(operator, 'unknown')  # Devuelve 'unknown' si el operador no está en el diccionario


temp_var_counter = 0 # Contador para las variables temporales (2 porque %1 esta reservado)

def get_temp_var(isParam=False):
    global temp_var_counter
    if temp_var_counter == 1 and not isParam:
        temp_var_counter += 1
    temp_var_counter += 1
    return f"%{temp_var_counter - 1}"

def get_property(node, property_name):
    matching_children = []  # Lista para almacenar coincidencias
    for child in node.children:
        # Verifica si el nodo es un Tree o un Token
        if isinstance(child, Tree):
            if child.data == property_name:  # Si es un Tree, accedes a 'data'
                matching_children.append(child)
        elif isinstance(child, Token):
            if child.type == property_name:  # Si es un Token, accedes a 'type'
                matching_children.append(child)
    
    # Si solo hay un elemento, retornarlo directamente
    if len(matching_children) == 1:
        return matching_children[0]
    
    # Si hay más de uno, retornar la lista
    return matching_children


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
    for arg in arguments.children:
        if isinstance(arg, Tree):
            arg_names.append([arg.children[0].value, get_temp_var(True)])
    
    # Por alguna razón después de los argumentos hay q dejar una instancia
    get_temp_var(True)

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
    out.write(" {\n")

    # Reservamos la memoria de los argumentos y creamos los apuntadores
    for arg in arg_names:
        out.write("\t")
        temp_var = get_temp_var()
        out.write(f"{temp_var} = alloca i32, align 4\n")
        out.write(f"\tstore i32 {arg[1]}, ptr {temp_var}, align 4\n")
        # Actualizamos el valor de la variable temporal, ya que no podemos usar el argumento como variable
        arg[1] = temp_var


    block = get_property(ast, "block")
    statement_return = []
    for child in block.children:
        if child.data == "statement":
            statement_return.append(translate_statement(child, out))

    if len(statement_return) == 1:
        out.write(f"\tret i32 {statement_return[0]}\n")
    else:
        out.write(f"\tret i32 {statement_return[0]}\n")

    out.write("}\n\n")
    global temp_var_counter
    temp_var_counter = 0
    arg_names = []


def translate_statement(statement, out):
    if statement.children[0].data == "return_stmt":
        return translate_return_stmt(statement.children[0], out)
    elif statement.children[0].data == "if_stmt":
        return translate_if_stmt(statement.children[0], out)


def traverse_expression(exp, translated_expressions):
    for e in exp:
        if isinstance(e, list):
            # Llamada recursiva, pasando `translated_expressions` como parámetro
            traverse_expression(e, translated_expressions)
            for arg in translated_expressions:
                if arg[0] in e:
                    e[e.index(arg[0])] = arg[1]

            translated_expressions.append([e, get_temp_var()])


def translate_return_stmt(return_stmt, out):
    expr_children = get_property(return_stmt, "expr")
    return_expr = translate_expr(expr_children, out)

    transformed_expressions = []

    # Si la expresión de retorno es una variable
    if isinstance(return_expr, str):
        return return_expr

    traverse_expression([return_expr], transformed_expressions)

    for expr in transformed_expressions:
        if len(expr[0]) == 3:
            out.write(f"\t{expr[1]} = {get_operator_name(expr[0][1])} nsw i32 {expr[0][0]}, {expr[0][2]}\n")

    # Obtener la última expresión transformada
    final_var = transformed_expressions[-1][1] if transformed_expressions else None

    return final_var


def translate_if_stmt(if_stmt, out, save_var=None):
    condition = get_property(if_stmt, "condition")
    blocks = get_property(if_stmt, "block")
    if save_var is None:
        return_var = get_temp_var()
    else:
        return_var = save_var

    # Reserva espacio para la variable de retorno
    if save_var is None:
        out.write(f"\t{return_var} = alloca i32, align 4\n")

    # Traduce la condición del if
    condition_expr = translate_condition(condition, out)
    comp_var = get_temp_var()
    true_label = get_temp_var()
    false_label_placeholder = "##" + str(comp_var)

    # Genera la comparación basada en la condición
    out.write(
        f"\t{comp_var} = {get_comparison_operator_name(condition_expr[1])} i32 {condition_expr[0]}, {condition_expr[2]}\n"
    )
    out.write(f"\tbr i1 {comp_var}, label {true_label}, label {false_label_placeholder}\n")

    # Manejo del bloque "true"
    out.write(f"\n{interpret_number(true_label)}:\n")
    if isinstance(blocks, list):
        false_label = translate_block(blocks[0], out, return_var)
    else:
        false_label = translate_block(blocks, out, return_var)

    # Manejo del bloque "false" (si existe)
    if isinstance(blocks, list):
        end_label = get_temp_var()
        out.write(f"\tbr label {end_label}\n")

        out.write(f"\n{interpret_number(false_label)}:\n")
        final_var = translate_block(blocks[1], out, return_var)
        out.write(f"\tbr label {end_label}\n")

    else:
        end_label = false_label
        out.write(f"\tbr label {end_label}\n")
        final_var = get_temp_var()

    # Finaliza el bloque
    if save_var is None:
        out.write(f"\n{interpret_number(end_label)}:\n")
        out.write(f"\t{final_var} = load i32, ptr {return_var}, align 4\n")
    else:
        print("save_var", save_var)
        out.write(f"\n{interpret_number(end_label)}:\n")

    # Reabrimos el archivo y reemplazamos el marcador de posición
    out.flush()  # Aseguramos que todo está escrito al disco
    with open(out.name, "r+") as f:
        content = f.read()
        # Reemplaza el marcador de posición con el valor correcto
        updated_content = content.replace(false_label_placeholder, false_label)
        # Sobrescribe el archivo con el nuevo contenido
        f.seek(0)
        f.write(updated_content)
        f.truncate()

    return final_var
    

def translate_block(block, out, return_var):
    """
    Traduce un bloque de código y actualiza la variable de retorno si es necesario.
    """
    for statement in block.children:
        if statement.data == "statement":
            if statement.children[0].data == "return_stmt":
                return_value = translate_return_stmt(statement.children[0], out)
                out.write(f"\tstore i32 {return_value}, ptr {return_var}, align 4\n")
                return get_temp_var()
            elif statement.children[0].data == "if_stmt":
                print("return_value", return_var)
                return_value = translate_if_stmt(statement.children[0], out, return_var)
                return get_temp_var()



def interpret_number(str):
    return int(re.search(r'\d+', str).group(0)) if re.search(r'\d+', str) else 0


def translate_expr(expr, out):
    expr_def = []
    for child in expr.children:
        if isinstance(child, Tree):  # Es un "term"
            expr_def.append(translate_term(child, out))

        elif isinstance(child, Token):  # Es un operador de suma o resta
            expr_def.append(child.value)
        else:
            print("Tipo inesperado de expresión:", type(child))

    if len(expr_def) == 1:
        return expr_def[0]
    return expr_def


def translate_term(term, out):
    term_def = []
    for child in term.children:
        if isinstance(child, Tree):  # Es un "factor"
            term_def.append(translate_factor(child, out))
        elif isinstance(child, Token): # Es un operador de multiplicación o división
            term_def.append(child.value)
        else:
            print("Tipo inesperado de término:", type(child))

    if len(term_def) == 1:
        return term_def[0]
    
    return term_def

def translate_factor(factor, out):
    global arg_names

    for child in factor.children:
        if isinstance(child, Tree):
            if child.data == "func_call":
                # Manejo de llamadas a funciones
                function_name = get_property(child, "name").children[0].children[0].value
                
                expr_children = get_property(child, "expr")
                return_expr = []
                
                
                if isinstance(expr_children, Tree):
                    return_expr.append(translate_return_stmt(child, out))
                else:
                    for arg in expr_children:
                        return_expr.append(translate_expr(arg, out))

                args_string = ", ".join(f"i32 noundef {arg}" for arg in return_expr)

                temp_var = get_temp_var()
                out.write(f"\t{temp_var} = call i32 @{function_name}({args_string})\n")

                return temp_var

            elif child.data == "word":
                # Buscar el nombre de la variable en los argumentos
                variable_name = child.children[0].value
                for arg in arg_names:
                    if arg[0] == variable_name:
                        var = arg[1]  # Apuntador actual del argumento

                        # Generar nueva variable temporal para la carga
                        temp_var = get_temp_var()
                        out.write(f"\t{temp_var} = load i32, ptr {var}, align 4\n")
                        return temp_var

        elif isinstance(child, Token):
            if child.type == "NUMBER":
                # Manejo directo de números
                return child.value

    raise ValueError(f"Factor no reconocido: {factor}")



def translate_condition(cond, out):
    def_condition = []
    for child in cond.children:
        if isinstance(child, Tree):
            if child.data == "expr":
                def_condition.append(translate_expr(child, out))
        elif isinstance(child, Token):
            def_condition.append(child.value)
    return def_condition


input = sys.argv[1]
output = "program.ll"
print("Input file: ", input)
parser = Lark(c_grammar, start='start', keep_all_tokens=True)

with open(input) as inputFile:
    with open(output, 'w') as out:
        ast = parser.parse(inputFile.read())
        print(ast.pretty())
        tree.pydot__tree_to_png(ast, "tree.png")
        tree.pydot__tree_to_dot(ast, "tree.dot", rankdir="TD")
        translate_program(ast, out)