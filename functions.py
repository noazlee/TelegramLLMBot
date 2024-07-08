
def python_math_execution(math_string):
    try:
        answer = eval(math_string)
        if answer:
            return str(answer)
    except:
        return 'invalid code generated' 

functions = [ 
    {
        "type": "function",
        "function": {
            "name": "python_math_execution",
            "description": "Solve a math problem using python code",
            "parameters": {
                "type": "object",
                "properties": {
                    "math_string": {
                        "type":
                        "string",
                        "description":
                        "A string that solves a math problem that conforms with python syntax that could be passed directly to an eval() function",
                    },
                },
                "required": ["math_string"],
            },
        },
    },
]

def run_function(name: str, args: dict): 
    if name == "svg_to_png_bytes":
        return svg_to_png_bytes(args["svg_string"])
    elif name == "python_math_execution":
        return python_math_execution(args["math_string"])
    else:
        return None