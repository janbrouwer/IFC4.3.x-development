import os
import re
import sys
import html
import json

from collections import defaultdict

import xmi

# python ./scripts/to_json-schema.py ./schemas/HarmonisedUMLmodel.xml ./generated_schemas/IFC_4_2_SCHEMA.json

try:
    fn = sys.argv[1]
    try:
        OUTPUT = open(sys.argv[2], "w", encoding='utf-8')
    except IndexError as e:
        OUTPUT = sys.stdout
except:
    print("Usage: python to_ifcjson.py <schema.xml>", file=sys.stderr)
    exit()

xmi_doc = xmi.doc(fn)
bfn = os.path.basename(fn)

schema_name = xmi_doc.by_tag_and_type["packagedElement"]['uml:Package'][1].name.replace(
    "exp", "").upper()
schema_name = "".join(["_", c][c.isalnum()] for c in schema_name)
schema_name = re.sub(r"_+", "_", schema_name)
schema_name = schema_name.strip('_')

schemaName = schema_name

def toLowerCamelcase(string):
    """Convert string from upper to lower camelCase"""

    return string[0].lower() + string[1:]

def yield_parents(node):
    yield node
    if node.parentNode:
        yield from yield_parents(node.parentNode)


def get_path(xmi_node):
    nodes = list(yield_parents(xmi_node.xml))

    def get_name(n):
        if n.attributes:
            v = n.attributes.get('name')
            if v:
                return v.value
    node_names = [get_name(n) for n in nodes]
    return node_names[::-1]


included_packages = set(("IFC 4.2 schema (13.11.2019)", "Common Schema",
                         "IFC Ports and Waterways", "IFC Road", "IFC Rail - PSM"))


def skip_by_package(element):
    return not (set(get_path(xmi_doc.by_id[element.idref])) & included_packages)


HTML_TAG_PATTERN = re.compile('<.*?>')
MULTIPLE_SPACE_PATTERN = re.compile(r'\s+')


def strip_html(s):
    S = html.unescape(s or '')
    i = S.find('\n')
    return re.sub(HTML_TAG_PATTERN, '', S)


def format(s):
    return re.sub(MULTIPLE_SPACE_PATTERN, ' ', ''.join([' ', c][c.isalnum() or c in '.,'] for c in s)).strip()

def generate_definitions():
    """
    A generator that yields a json-schema dict
    """
    make_defaultdict = lambda: defaultdict(make_defaultdict)
    classifications = defaultdict(make_defaultdict)
    definitions = defaultdict(make_defaultdict)

    class_name_to_node = {}

    for c in xmi_doc.by_tag_and_type["element"]["uml:Class"]:

        if skip_by_package(c):
            continue

        class_name_to_node[c.name] = c
        stereotype = (c/"properties")[0].stereotype
        if stereotype is not None:
            stereotype = stereotype.lower()
        
    class_names = sorted(classifications.keys() | {c.get('Parent') for c in classifications.values() if c.get('Parent')})
    annotated = set()

    def element_by_id(id):
        return [x for x in xmi_doc.by_tag_and_type['element']['uml:Class'] if x.idref == id][0]

    def annotate_parent(cn):
        if cn in annotated:
            return
        annotated.add(cn)
        node = class_name_to_node.get(cn)
        attributes = {}
        for la in node/("attribute"):
            attributes[toLowerCamelcase(la.name)] = {
            "$ref": "#/definitions/@todo:IFCTYPE"
            }
        
        if node is None:
            # probably an enumeration value handled above
            return
        try:
            for rel in (node | "links")/"Generalization":
                pc = xmi_doc.by_id[rel.end]
                className = toLowerCamelcase(cn)
                parentClassName = toLowerCamelcase(pc.name)

                # @todo Figure out why parentClassName sometimes contains className

                classifications[cn] = {
                    "description": format(strip_html((element_by_id(rel.start)/"properties")[0].documentation)),
                    "type": "object",
                    "properties": {
                        "type": {
                            "const": className
                        }
                    },
                    "allOf": [
                        {
                            "$ref": "#/definitions/" + className
                        }
                    ],
                    "required": [
                        "type"
                    ]
                }
                definitions[className] = {
                    "type": "object",
                    "properties": attributes,
                    "allOf": [
                        {
                            "$ref": "#/definitions/" + parentClassName
                        }
                    ],
                    "required": ["@todo:NON-OPTIONAL"]
                }
                annotate_parent(pc.name)
        except ValueError as e:
            print(e, file=sys.stderr)

    product = [c for c in xmi_doc.by_tag_and_type['element']['uml:Class'] if c.name == 'IfcRoot'][0] # in ('IfcRoot','IfcOwnerHistory','IfcGeometricRepresentationContext')][0]
    subtypes = []

    def visit_subtypes(t):
        sts = [element_by_id(g.start) for g in (
            t | "links")/"Generalization" if g.end == t.idref]
        subtypes.extend(x.name for x in sts)
        for t in sts:
            visit_subtypes(t)

    visit_subtypes(product)

    for cn in class_names:
        annotate_parent(cn)

    for cn in subtypes:
        annotate_parent(cn)

    data = {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'title': 'IFC.JSON',
        'description': 'This is the schema for representing IFC4 data in JSON',
        'version': schema_name,
        "type": "object",
        'properties': {
            "file_schema": {
                "const": schema_name
            },
            "data": {
                "type": "array",
                "items": {
                    "anyOf": list(classifications.values())
                },
            }
        },
        "required": [
            "file_schema", "data"
        ],
        "definitions": definitions
    }

    return data
json.dump(generate_definitions(), OUTPUT, indent=2)