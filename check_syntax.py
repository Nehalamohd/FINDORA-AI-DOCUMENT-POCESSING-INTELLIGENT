
import sys

def check_indentation(filename):
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if '\t' in line:
                print(f"Line {i+1} CONTAINS TAB: {repr(line)}")
                
        compile(open(filename).read(), filename, 'exec')
        print("Syntax OK")
    except IndentationError as e:
        print(f"IndentationError: {e}")
    except Exception as e:
        print(f"Error: {e}")

check_indentation('ai_micoservice/app/llm.py')
