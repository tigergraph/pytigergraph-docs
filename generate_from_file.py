from pydoc import doc
import sys
import re

f = open(sys.argv[1], 'r').readlines()
out = open(sys.argv[2], 'w')
out.write("= "+sys.argv[3]+"\n\n")
prevFuncHeader = False
prevParam = False
i = 0
while i < len(f):
    if "def " in f[i] and "(self" in f[i] and "def _" not in f[i]: # Function header
        header = f[i].split("def")[1].replace("self, ", "").strip()
        title = header.split("(")[0].strip()
        while ") -> " not in header: # iterate until end of header
            i += 1
            try:
                header += f[i].strip("\n").strip()
            except: # Function does not have a return type
                i -= 1
                break
        out.write("## " + title+"\n")
        out.write("``"+header.strip(":")+"``\n\n")
        prevFuncHeader = True
    elif '"""' == f[i].strip() and prevFuncHeader: # End of doc string
        prevFuncHeader = False
        out.write("\n")
    elif prevFuncHeader: # Docstring
        docstring = f[i]
        docstring = docstring.replace('"""', "").replace("  ", "")
        docstring = docstring.replace("\t", "").replace("Args:", "#### Parameters:\n")
        docstring = docstring.replace("Returns:", "#### Returns:\n")
        if "#### Parameters:\n" in docstring or "#### Returns:\n" in docstring:
            out.write(docstring)
            if "#### Parameters:\n" in docstring:
                prevParam = True
            else:
                prevParam = False
        elif prevParam and ":\n" in docstring:
            out.write("``"+docstring.replace(":", "``:\n"))
        elif "." in docstring:
            out.write(docstring+"\n")
        else:
            out.write(docstring)
    elif f[i].strip() == "\n": # consolidate doc string
        pass
    else:  # Code
        pass
    i += 1

out.close()
