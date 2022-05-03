import _ast
import ast
import json
import os
import re


def processFunctionDocstring(docstring, adocFile, argNum):
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
            adocFile.write("[discrete]\n")
            adocFile.write("==== **Parameter" + ("s" if argNum > 1 else "") + ":**\n")
            mode = "param"
        elif li in ["Args:", "Returns:", "Endpoint:", "Endpoints:", "Uses:", "Raises:", "Notes:",
            "Example:", "Examples:", "Usage:"]:
            adocFile.write("[discrete]\n")
            adocFile.write("==== **{}**\n".format(li))
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
                    adocFile.write(lis.replace("```",
                        ("\n+" if mode == "param" else "") + "\n[source,indent=0]\n----\n"))
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
                        li = re.sub(r"See (https[^ ]+)",
                            r" +\nSee the \1[documentation] for more details.", li)
                    if "see https://docs.tigergraph.com" in li:
                        li = re.sub(r"see (https[^ ]+)", r"see the \1[documentation]", li)
                    if '"*"' in li:
                        li = li.replace('"*"', '"&#42;"')
                    adocFile.write(li + "\n")
    adocFile.write("\n\n")


def processTypes(node, colon: bool = True) -> str:
    if colon:
        cln = ": "
    else:
        cln = ""
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
                    typeList += cln + "???1 " + str(type(t2))
            else:
                typeList += cln + "???2 " + str(type(t)) + ", "
        return cln + "[" + typeList[:-2] + "]"
    elif isinstance(node, _ast.Name):
        return cln + node.id
    elif isinstance(node, _ast.Attribute):
        v = node.value
        if isinstance(v, _ast.Name):
            return cln + v.id + ("." + str(node.attr if node.attr else ""))
        else:
            return cln + "???3 " + str(type(v))
    elif str(type(node)) == "<class 'NoneType'>":
        return ""
    elif str(node.value) == "TigerGraphConnection":
        return cln + "TigerGraphConnection"
    elif isinstance(node, ast.Constant):
        if node.value == "None":
            return cln + "None"
        else:
            return cln + str(node.value)
    elif isinstance(node, _ast.Subscript):
        if node.value.id == "Union":
            partial = ""
            '''
            for t in node.slice.value.elts:
                partial += processTypes(t, False) + ", "
            return cln + "Union[" + partial[:-2] + "]"
            '''
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.Tuple):
                    for t in child.elts:
                        partial += processTypes(t, False) + ", "
            return cln + "Union[" + partial[:-2] + "]"
    else:
        for child in ast.iter_child_nodes(node):
            print(child)
        return cln + "???4 " + str(type(node))


def processFunction(node, adocFile):
    if node.name.startswith("_") and node.name != "__init__":  # TODO cfg for __init__?
        return

    adocFile.write("=== {}\n".format(node.name if node.name != "__init__" else "Constructor"))

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
    retList = str(processTypes(node.returns, False))

    if retList:
        adocFile.write("`{}({}) -> {}`\n\n".format(node.name, argList, retList))
    else:
        adocFile.write("`{}({})`\n\n".format(node.name, argList))
    try:
        processFunctionDocstring(ast.get_docstring(node), adocFile, argNum - 1)
    except:
        raise (Exception("Error processing docstring for function {}".format(node.name)))


def processClassDocstring(node, adocFile, hasFileHeader):
    try:
        ds = ast.get_docstring(node)
        title = ds.split("\n")[0].rstrip(".")
        description = "\n".join(ds.split("\n")[1:])

        adocFile.write(("=" if hasFileHeader else "") + "= {}\n".format(title))
        adocFile.write("{}\n\n".format(description))
    except:
        raise Exception("No docstring for class {}".format(node.name))


def processClass(node, adocFile, hasFileHeader):
    processClassDocstring(node, adocFile, hasFileHeader)

    for child in ast.iter_child_nodes(node):
        if isinstance(child, _ast.FunctionDef):
            processFunction(child, adocFile)
            # return


def processFileHeader(src, adocFile) -> bool:
    srcList = src.split("\n")

    if not srcList[0].startswith('"""'):  # No file level docstring (single-class file, perhaps?)
        return False

    if srcList[0].startswith('"""') and srcList[0].endswith('"""'):  # Single-line docstring
        title = srcList[0].strip('"""').rstrip(".")
        description = ""
    else:  # Multi-line docstring
        endOfHeader = 0
        for i in range(len(srcList)):
            if srcList[i] == '"""':
                endOfHeader = i
                break
        header = "\n".join(srcList[:endOfHeader]).lstrip('"""')
        title = header.split("\n")[0].rstrip(".")
        description = "\n".join(header.split("\n")[1:])

    adocFile.write("= {}\n\n".format(title))
    if description:
        adocFile.write(description + "\n\n")

    return True


def main():
    cfgFile = "docstring2asciidoc_cfg.json"

    if not os.path.exists(cfgFile):
        print(f"Error: configuration file {cfgFile} was not found!")
        exit(1)

    cfg = {}
    try:
        cfg = json.load(open(cfgFile, "r"))
    except OSError as e:
        print("Error: {}".format(e))
        exit(2)

    if "source_root" not in cfg:
        print("Error: source code root folder is not specified!")
        exit(3)

    if not cfg["source_root"].endswith("/"):
        cfg["source_root"] += "/"

    if "doc_root" not in cfg:
        print("Error: documentation root folder is not specified!")
        exit(4)

    if not cfg["doc_root"].endswith("/"):
        cfg["doc_root"] += "/"

    if "mapping" not in cfg or len(cfg["mapping"]) == 0:
        print("Error: documentation mapings are not specified!")
        exit(5)

    for s, d in cfg["mapping"].items():
        if s.startswith("#"):  # Skip this mapping
            continue
        srcFilePath = cfg["source_root"] + s
        docFilePath = cfg["doc_root"] + d

        print("Processing " + s + " -> " + d)

        srcFile = open(srcFilePath, "r")
        src = srcFile.read()
        srcFile.close()

        adocFile = open(docFilePath, "w")

        hasFileHeader = processFileHeader(src, adocFile)

        node = ast.parse(src, "<irrelevant>", "exec")

        for child in ast.iter_child_nodes(node):
            if isinstance(child, _ast.ClassDef):
                processClass(child, adocFile, hasFileHeader)

        adocFile.close()


if __name__ == '__main__':
    main()
