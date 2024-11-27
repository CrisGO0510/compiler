import sys
from lark import Lark, tree

# print(
#     r'''
#     < Hi High-LOGO! >
#     ---------------
#         \   ^__^
#          \  (oo)\_______
#             (__)\       )\/\
#                 ||----w |
#                 ||     ||
#     '''
# )

if (len(sys.argv) != 2):
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
# Here we define the grammar. It is tha same as in
# the web IDE. You can work on the grammar there if
# you wish to and then paste it here.
high_logo_grammar = r"""
    // A HIgh-LOGO program consists of one or more basic instructions
    start: basic_instruction+				

    basic_instruction: INSTNAME INTNUM

    INSTNAME: "FD"
    INTNUM : /-?\d+(\.\d+)?([eE][+-]?\d+)?/

    %ignore /[ \t\n\f\r]+/
"""

# This function will traverse the AST and you can use it to emit the 
# code you want at every node of it.
def translate_program(ast, out):
    # print("Tree node", ast)
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

input = sys.argv[1]
output = sys.argv[1] + str(".py")
print("Input file: ", input)
parser = Lark(high_logo_grammar)

with open(input) as inputFile:
    with open(output, 'w') as out:
        ast = parser.parse(inputFile.read())
        print(ast.pretty())
        tree.pydot__tree_to_png(ast, "tree.png")
        tree.pydot__tree_to_dot(ast, "tree.dot", rankdir="TD")
        translate_program(ast, out)