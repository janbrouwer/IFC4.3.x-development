import re
from types import SimpleNamespace

import pytest

from to_bsdd import (
    annotate,
    annotation_pattern,
    class_property_code,
    data_type_for,
    descendants,
    documentation_url,
    entity_classes,
    expand_predefined_types,
    register_property,
    render_class_properties,
    scope_provenance,
    spine_to_top,
)

SUPERTYPE = {
    "IfcObjectDefinition": "IfcRoot",
    "IfcRelationship": "IfcRoot",
    "IfcObject": "IfcObjectDefinition",
    "IfcTypeObject": "IfcObjectDefinition",
    "IfcProduct": "IfcObject",
    "IfcWall": "IfcProduct",
    "IfcWallType": "IfcTypeObject",
    "IfcRelAggregates": "IfcRelationship",
    "IfcGeometricRepresentationItem": "IfcRepresentationItem",
    "IfcLightSource": "IfcGeometricRepresentationItem",
    "IfcLightSourceAmbient": "IfcLightSource",
    "IfcCartesianPoint": "IfcGeometricRepresentationItem",
}
CHILDREN = {}
for child, parent in SUPERTYPE.items():
    CHILDREN.setdefault(parent, set()).add(child)
NAMES = set(SUPERTYPE) | set(SUPERTYPE.values())

ANCHORS = {"IfcObject": "occurrences", "IfcLightSource": "lighting"}


def test_scope_includes_down_cone_and_spine_to_root():
    scope = scope_provenance(ANCHORS, NAMES, SUPERTYPE, CHILDREN)
    for name in ("IfcObject", "IfcProduct", "IfcWall", "IfcObjectDefinition", "IfcRoot",
                 "IfcLightSource", "IfcLightSourceAmbient"):
        assert name in scope, name
    assert scope["IfcRoot"] == "supertype spine of IfcObject"
    assert scope["IfcWall"] == "descendant of IfcObject"


def test_scope_excludes_unreachable_families():
    scope = scope_provenance(ANCHORS, NAMES, SUPERTYPE, CHILDREN)
    for name in ("IfcTypeObject", "IfcWallType", "IfcRelationship", "IfcRelAggregates",
                 "IfcRepresentationItem", "IfcGeometricRepresentationItem", "IfcCartesianPoint"):
        assert name not in scope, name


def test_anchor_missing_from_schema_is_skipped():
    assert scope_provenance({"IfcBogus": ""}, NAMES, SUPERTYPE, CHILDREN) == {}


def test_spine_kept_only_when_it_reaches_top():
    assert spine_to_top("IfcWall", SUPERTYPE)[-1] == "IfcRoot"
    assert spine_to_top("IfcLightSource", SUPERTYPE) == []


def test_descendants_is_inclusive_and_transitive():
    assert descendants("IfcObject", CHILDREN) == {"IfcObject", "IfcProduct", "IfcWall"}


def test_class_property_code():
    assert class_property_code("FireRating", "Pset_WallCommon") == "FireRating_from_WallCommon"
    long = class_property_code("IsCurrentTolerancePositiveOnly",
                               "Pset_ProtectiveDeviceTrippingUnitTimeAdjustment")
    assert long == "IsCurrentTolerancePositiveOnly_from_...PPDTUTA"
    squeezed = class_property_code("SomeRatherLongPropertyName", "Pset_SomeRatherLongPropertySetName")
    assert "..." in squeezed and len(squeezed) <= 50


def test_data_type_for():
    assert data_type_for("string") == "String"
    assert data_type_for("REAL") == "Real"
    assert data_type_for("PEnum_Status") == "String"
    assert data_type_for("IfcWindowStyleOperationEnum") == "String"
    assert data_type_for("logical") is None


def test_annotate_wraps_published_italic_markup_as_wikilink():
    pattern = annotation_pattern({"IfcAlignmentHorizontal"}, {"IfcAlignmentHorizontal"})
    assert annotate("An _IfcAlignmentHorizontal_ is", pattern) == "An [[IfcAlignmentHorizontal]] is"


def test_annotate_still_wraps_bare_published_names():
    pattern = annotation_pattern({"IfcAlignmentSegment"}, {"IfcAlignmentSegment"})
    assert annotate("IfcAlignmentSegment", pattern) == "[[IfcAlignmentSegment]]"


def test_annotate_does_not_double_wrap_when_both_forms_appear():
    pattern = annotation_pattern({"IfcWall"}, {"IfcWall"})
    assert annotate("IfcWall and _IfcWall_", pattern) == "[[IfcWall]] and [[IfcWall]]"


def test_annotate_strips_unpublished_italic_markup_to_plain_text():
    pattern = annotation_pattern({"IfcAlignmentHorizontal"}, {"IfcAlignmentHorizontal", "IfcCartesianPoint"})
    assert annotate("An _IfcCartesianPoint_ is", pattern) == "An IfcCartesianPoint is"


def test_annotate_leaves_bare_unpublished_names_untouched():
    pattern = annotation_pattern({"IfcAlignmentHorizontal"}, {"IfcAlignmentHorizontal", "IfcCartesianPoint"})
    assert annotate("IfcCartesianPoint here", pattern) == "IfcCartesianPoint here"


def test_allowed_value_labels_stay_plain_but_lose_italic_markup():
    from to_bsdd import render_allowed_values

    pattern = annotation_pattern({"Temperature", "IfcWall"}, {"Temperature", "IfcWall"})
    values = [
        {"Value": "OPERATINGTEMPERATURE", "Description": "Operating Temperature", "Package": "P"},
        {"Value": "1000", "Description": "1000", "Package": "P"},
        {"Value": "WALLMOUNTED", "Description": "Mounted on an _IfcWall_", "Package": "P"},
    ]
    rendered = render_allowed_values(values, "Prop", pattern, [])
    assert [v["Description"] for v in rendered] == ["Operating Temperature", "1000", "Mounted on an IfcWall"]


def test_annotation_codes_excludes_logical_filler_values():
    from to_bsdd import TYPE_TO_VALUES, annotation_codes

    classes = {
        "IfcWall": {
            "Parent": "",
            "Psets": {
                "Pset_WallCommon": {
                    "IsExternal": _prop(
                        "Is External",
                        Values=[{"Value": v, "Description": v, "Package": "P"} for v in TYPE_TO_VALUES["logical"]],
                    ),
                },
            },
        },
    }
    codes = annotation_codes(classes)
    assert not codes & set(TYPE_TO_VALUES["logical"])
    assert annotate("TRUE or FALSE", annotation_pattern(codes, codes)) == "TRUE or FALSE"


def test_documentation_url_points_predefined_types_at_their_entity_page():
    entity, child = {"Parent": "IfcProduct"}, {"Parent": "IfcBeam", "PredefinedPin": "BEAM"}
    assert documentation_url("IfcBeam", entity, "4.3").endswith("/IFC4_3/HTML/lexical/IfcBeam.htm")
    assert documentation_url("IfcBeamBEAM", child, "4.3") == documentation_url("IfcBeam", entity, "4.3")
    assert documentation_url("IfcBeam", entity, "4.0") == ""


def _prop(name, **extra):
    return {"Type": "string", "Name": name, "Definition": "", "Kind": "Single", "Package": "P", **extra}


CLASSES = {
    "IfcElement": {
        "Parent": "",
        "Package": "P",
        "Psets": {
            "Attributes": {
                "PredefinedType": _prop(
                    "Predefined Type",
                    Values=[{"Value": "SOLIDWALL", "Description": "Solid Wall", "Package": "P"},
                            {"Value": "POLYGONAL", "Description": "Polygonal", "Package": "P"}],
                    ValuesPerClass=True,
                ),
            },
        },
    },
    "IfcWall": {
        "Parent": "IfcElement",
        "Package": "P",
        "Psets": {"Pset_WallCommon": {"FireRating": _prop("Fire Rating")}},
    },
    "IfcWallSOLIDWALL": {
        "Parent": "IfcWall",
        "Package": "P",
        "Psets": {},
        "PredefinedPin": "SOLIDWALL",
    },
}
NO_ANNOTATION = annotation_pattern({"zzz-never-matches"}, {"zzz-never-matches"})


def _render(code):
    return render_class_properties(code, CLASSES, NO_ANNOTATION, {}, [])


def test_class_properties_inherit_down_the_spine():
    codes = {cp["Code"] for cp in _render("IfcWall")}
    assert codes == {"FireRating_from_WallCommon", "PredefinedType_from_Attributes"}


def test_parent_carries_full_enum_and_child_pins_one_value():
    parent_pt = next(cp for cp in _render("IfcElement") if cp["PropertyCode"] == "PredefinedType")
    assert [v["Value"] for v in parent_pt["AllowedValues"]] == ["SOLIDWALL", "POLYGONAL"]
    child_pt = next(cp for cp in _render("IfcWallSOLIDWALL") if cp["PropertyCode"] == "PredefinedType")
    assert [v["Value"] for v in child_pt["AllowedValues"]] == ["SOLIDWALL"]


def test_inherited_duplicates_collapse_to_one_class_property():
    properties, seen = {}, []
    for cp in render_class_properties("IfcWallSOLIDWALL", CLASSES, NO_ANNOTATION, properties, []):
        assert cp["Code"] not in seen
        seen.append(cp["Code"])
    assert "PredefinedType" in properties and "FireRating" in properties
    assert "AllowedValues" not in properties["PredefinedType"]


def test_pot_files_group_by_package_and_dedupe_first_wins(tmp_path, caplog):
    from to_bsdd import dedupe_translations, message, write_pot_files

    to_translate = [
        message("IfcWall", "Wall", "Core"),
        message("IfcWall_DEFINITION", "A wall.", "Core"),
        message("IfcWall", "Wall", "Core"),                 # identical duplicate: silent
        message("IfcWall_DEFINITION", "Another wall.", "Core"),  # conflicting duplicate: warned
        message("FireRating", "Fire Rating", "Shared"),
        message("", "dropped", "Core"),
        message("NoSource", "", "Core"),
    ]
    deduped = dedupe_translations(to_translate)
    assert [t["msgid"] for t in deduped] == ["IfcWall", "IfcWall_DEFINITION", "FireRating"]
    assert deduped[1]["msgstr"] == "A wall."
    assert "IfcWall_DEFINITION" in caplog.text

    write_pot_files(to_translate, tmp_path)
    core = (tmp_path / "pot" / "Core.pot").read_text(encoding="utf-8")
    assert 'msgid "IfcWall"\nmsgstr "Wall"' in core and core.count('msgid "IfcWall"') == 1
    assert "X-Crowdin-SourceKey: msgstr" in core
    shared = (tmp_path / "pot" / "Shared.pot").read_text(encoding="utf-8")
    assert 'msgid "FireRating"\nmsgstr "Fire Rating"' in shared


def test_deprecated_property_is_published_with_inactive_status():
    properties = {}
    register_property("Reference", _prop("Reference", Deprecated=True), NO_ANNOTATION, properties, [])
    register_property("FireRating", _prop("Fire Rating"), NO_ANNOTATION, properties, [])
    assert properties["Reference"]["Status"] == "Inactive"
    assert "Status" not in properties["FireRating"]


def _real_schema_scope():
    from xmi_document import xmi_document
    from to_bsdd import ANCHORS, DEFAULT_SCHEMA, entity_tree, schema_items

    schema = schema_items(xmi_document(str(DEFAULT_SCHEMA)))
    supertype_of, children_of = entity_tree(schema.entities)
    return scope_provenance(ANCHORS, {e.name for e in schema.entities}, supertype_of, children_of)


@pytest.mark.integration
def test_real_schema_scope_invariants():
    from to_bsdd import ANCHORS

    scope = _real_schema_scope()
    for name in ("IfcRoot", "IfcObjectDefinition", "IfcWall", "IfcActor", "IfcLightSourceAmbient", *ANCHORS):
        assert name in scope, name
    for name in ("IfcExtrudedAreaSolid", "IfcCartesianPoint", "IfcRelAggregates",
                 "IfcPropertySingleValue", "IfcTypeObject", "IfcWallType"):
        assert name not in scope, name


@pytest.mark.integration
def test_every_documentation_url_resolves_to_a_documented_entity():
    from to_bsdd import REPO_ROOT

    pages = {path.stem for path in (REPO_ROOT / "docs" / "schemas").glob("*/*/Entities/*.md")}
    assert sorted(_real_schema_scope().keys() - pages) == []


def _fake_entity(name, children=()):
    return SimpleNamespace(name=name, meta={}, markdown_content="", markdown_definition="",
                           markdown="", package="P", id=name, children=list(children))


def test_material_classtype_covers_only_the_material_classes():
    from to_bsdd import MATERIAL_CLASSES

    entities = [_fake_entity(n) for n in ("IfcMaterial", "IfcConstructionMaterialResource", "IfcWall")]
    classes, _ = entity_classes(entities, {e.name for e in entities}, MATERIAL_CLASSES)
    materials = {name for name, content in classes.items() if content["ClassType"] == "Material"}
    assert materials == {"IfcMaterial", "IfcConstructionMaterialResource"}


def test_predefined_type_children_never_inherit_material_classtype():
    from to_bsdd import MATERIAL_CLASSES

    predefined_attr = SimpleNamespace(name="PredefinedType", node=SimpleNamespace(resolve=lambda key: "enum_id"))
    entity = _fake_entity("IfcConstructionMaterialResource", children=[predefined_attr])
    literal = SimpleNamespace(name="CONCRETE", markdown="", id="lit_concrete")
    enum = SimpleNamespace(children=[literal])
    schema = SimpleNamespace(entities=[entity], enumerations={"IfcConstructionMaterialResourceTypeEnum": enum})
    xmi = SimpleNamespace(by_id={"enum_id": SimpleNamespace(name="IfcConstructionMaterialResourceTypeEnum")})

    classes, class_by_entity_id = entity_classes([entity], {entity.name}, MATERIAL_CLASSES)
    expand_predefined_types(schema, classes, class_by_entity_id, xmi)

    assert classes["IfcConstructionMaterialResource"]["ClassType"] == "Material"
    assert classes["IfcConstructionMaterialResourceCONCRETE"]["ClassType"] == "Class"


ITALIC_MARKUP = re.compile(r"_Ifc\w+_")


@pytest.mark.integration
def test_export_leaves_no_italic_markup_or_boolean_wikilinks(tmp_path):
    import subprocess
    import sys

    from to_bsdd import DEFAULT_SCHEMA, REPO_ROOT

    code_dir = REPO_ROOT / "code"
    subprocess.run([sys.executable, "to_bsdd.py", str(DEFAULT_SCHEMA), str(tmp_path)], cwd=code_dir, check=True)

    import json

    ifc_json = (tmp_path / "IFC.json").read_text(encoding="utf-8")
    assert not ITALIC_MARKUP.findall(ifc_json)
    assert "[[TRUE]]" not in ifc_json and "[[FALSE]]" not in ifc_json and "[[UNKNOWN]]" not in ifc_json

    doc = json.loads(ifc_json)
    labels = [v.get("Description", "") for p in doc["Properties"] for v in p.get("AllowedValues", [])]
    labels += [v.get("Description", "") for c in doc["Classes"] for cp in c["ClassProperties"]
               for v in cp.get("AllowedValues", [])]
    assert labels and not any("[[" in label for label in labels)

    for unpublished in ("IfcRelAggregates", "IfcLinearPlacement", "IfcLocalPlacement",
                        "IfcShellBasedSurfaceModel", "IfcRelAssignsToGroupByFactor"):
        assert "[[%s]]" % unpublished not in ifc_json, unpublished

    msgstrs = [m.group(1) for pot in (tmp_path / "pot").glob("*.pot")
               for m in re.finditer(r'^msgstr "(.+)"$', pot.read_text(encoding="utf-8"), re.M)]
    assert msgstrs
    assert not any(ITALIC_MARKUP.search(msgstr) for msgstr in msgstrs)
    assert not any("[[TRUE]]" in msgstr or "[[FALSE]]" in msgstr or "[[UNKNOWN]]" in msgstr for msgstr in msgstrs)
