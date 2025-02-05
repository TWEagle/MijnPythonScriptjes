from cx_Freeze import setup, Executable

setup(

name="Password Generator",

version="1.0",

description="Hiermee wordt een wachtwoord gegenereerd worden die ik nodig heb voor PKI.",

executables=[Executable("c:/d/OneDrive - TWEagle/MPS/MijnPythonScriptjes/DCBaaS/passgen.py")],

)