import traceback

def error_handling(e):
    tb = traceback.extract_tb(e.__traceback__)
    for error in tb:
        print(f'{type(e).__name__}: {str(e)}')
        print('Line number:', error.lineno)
        print('Line:', error.line)
        print('=='*45) 