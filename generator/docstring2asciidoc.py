import _ast
import ast
import re


def processFunctionDocstring(docstring, adocFile, argNum):
    # adocFile.write(docstring + "\n\n" + ("~" * 100) + "\n\n")
    lines = docstring.split("\n")

    mode = "none"
    codeMode = False
    for li in lines:
        lis = li.strip()
        if codeMode:
            if lis.startswith("```"):
                adocFile.write("----\n\n")
                codeMode = False
            else:
                adocFile.write(li + "\n")
        elif "TODO" in li:
            mode = "todo"
        elif li == "Args:":
            adocFile.write("=== Parameter" + ("s" if argNum > 1 else "") + ":\n")
            mode = "param"
        elif li in ["Args:", "Returns:", "Endpoint:", "Endpoints:", "Uses:", "Raises:", "Notes:"]:
            adocFile.write("=== {}\n".format(li))
            mode = "none"
        else:
            if mode == "todo":
                break
            pname = re.compile("^ {4,4}.+:$")
            if pname.search(li) and mode == "param":
                if not li.startswith("     "):
                    adocFile.write("* `{}`: ".format(li.strip(" :'")))
                else:
                    if lis == "Example:":
                        adocFile.write("+\nExample:")
                    else:
                        adocFile.write("{} +\n".format(lis))
            else:
                if lis.startswith("```"):
                    if not codeMode:
                        codeMode = True
                    adocFile.write(lis.replace("```", ("\n+" if mode == "param" else "") + "\n[source,indent=0]\n----\n"))
                elif lis.startswith("`") and lis.endswith("`"):
                    if mode == "params":
                        adocFile.write(" +\n" + lis + " +\n +\n")
                    else:
                        adocFile.write(" +\n" + lis + "\n+\n")
                else:
                    lf = re.compile(" /$")
                    if lf.search(li) or " plus" in li:
                        li = lf.sub(" +", li)
                    if mode != "code":
                        li = li.lstrip()
                    if "See https://docs.tigergraph.com" in li:
                        li = re.sub(r"See (https[^ ]+)", r" +\nSee the \1[documentation] for more details.", li)
                    if "see https://docs.tigergraph.com" in li:
                        li = re.sub(r"see (https[^ ]+)", r"see the \1[documentation]", li)
                    if '"*"' in li:
                        li = li.replace('"*"', '"&#42;"')
                    adocFile.write(li + "\n")
    adocFile.write("\n\n")

def processTypes(node) -> str:
    if isinstance(node, _ast.List):
        typeList = ""
        for t in node.elts:
            if isinstance(t, _ast.Name):
                typeList += t.id + ", "
            elif isinstance(t, _ast.Attribute):
                t2 = t.value
                if isinstance(t2, _ast.Name):
                    typeList += t2.id + ("." + str(t.attr if t.attr else "")) + ", "
                else:
                    typeList += ": ???1 " + str(type(t2))
            else:
                typeList += ": ???2 " + str(type(t)) + ", "
        return ": [" + typeList[:-2] + "]"
    elif isinstance(node, _ast.Name):
        return ": " + node.id
    elif isinstance(node, _ast.Attribute):
        v = node.value
        if isinstance(v, _ast.Name):
            return ": " + v.id + ("." + str(node.attr if node.attr else ""))
        else:
            return ": ???3 " + str(type(v))
    elif str(type(node)) == "<class 'NoneType'>":
        return ""
    else:
        return ": ???4 " + str(type(node))

def processFunction(node, adocFile):
    if node.name.startswith("_"):
        return

    adocFile.write("== {}\n".format(node.name))

    argList = ""

    args = node.args.args
    argNum = len(args)
    defs = node.args.defaults
    defNum = len(defs)
    defOffset = argNum - defNum

    i = 0

    # Arguments
    for a in args:
        if a.arg != "self":
            # argList += a.arg + ", "
            argList += a.arg + processTypes(a.annotation)
            if i >= defOffset:
                de = defs[i - defOffset].value
                if isinstance(de, str):
                    argList += " = \"" + de + "\""
                else:
                    argList += " = " + str(de)
            argList += ", "
        i += 1
    argList = argList[:-2]

    # Return type(s)
    retList = str(processTypes(node.returns))

    adocFile.write("`{}({}) -> {}`\n\n".format(node.name, argList, retList))

    processFunctionDocstring(ast.get_docstring(node), adocFile, argNum - 1)


def processClassDocstring(node, adocFile):
    adocFile.write("= {}\n\n".format(ast.get_docstring(node).strip(".")))


def processClass(node, adocFile):
    processClassDocstring(node, adocFile)

    for child in ast.iter_child_nodes(node):
        if isinstance(child, _ast.FunctionDef):
            processFunction(child, adocFile)
            # return


def main():
    srcPath = "/Users/szilardbarany/GitHub/pyTigerGraph/pyTigerGraph/"
    srcName = "pyTigerGraphEdge.py"

    adocPath = "/Users/szilardbarany/GitHub/pytigergraph-docs/modules/core-functions/pages/"
    adocName = srcName.replace("pyTigerGraph", "").lower().replace("py", "adoc")

    srcFile = open(srcPath + srcName, "r")
    src = srcFile.read()
    srcFile.close()

    adocFile = open(adocPath + adocName, "w")

    node = ast.parse(src, srcName, "exec")

    for child in ast.iter_child_nodes(node):
        if isinstance(child, _ast.ClassDef):
            processClass(child, adocFile)

    adocFile.close()


if __name__ == '__main__':
    main()
