import pytest

from name_improve import definition_improve, name_improve

CHECKS = {
    "IfcActionRequest": "Action Request",
    "IfcPrestressingRail": "Prestressing Rail",
    "Railing": "Railing",
    "APPROACHSIGNAL": "Approach Signal",
    "BLADEPITCHANGLE": "Blade Pitch Angle",
    "TexCoordIndex_L[3:?]": "Tex Coord Index",
    "IfcComplexNumber_A[1:2]": "Complex Number",
    "GlobalId": "Global ID",
    "N20": "N2O",
    "ACTIVEBALISE": "Active Balise",
    "ASSIGNEE": "Assignee",
    "WCDMA": "WCDMA",
    "IfcWallSOLIDWALL": "Wall Solid Wall",
    "SPANDREL": "Spandrel",
    "CATENARYWIRE": "Catenary Wire",
    "DIRECTEVAPORATIVEAIRWASHER": "Direct Evaporative Air Washer",
    "IfcElectricApplianceDISHWASHER": "Electric Appliance Dishwasher",
    "HEATEXCHANGERS": "Heat Exchangers",
    "DXCOOLINGCOIL": "DX Cooling Coil",
    "NominalFlowrate": "Nominal Flow Rate",
    "NumberofBlades": "Number of Blades",
    "CurrentContent3rdHarmonic": "Current Content 3rd Harmonic",
    "IC60269": "IC 60269",
    "Pset_WallCommon": "Wall Common",
    "Qto_WallBaseQuantities": "Wall Base Quantities",
    "IfcRelDefinesByProperties": "Defines By Properties",
    "Relaxations": "Relaxations",
}


@pytest.mark.parametrize("src, want", CHECKS.items())
def test_name_improve(src, want):
    assert name_improve(src) == want


def test_definition_improve_flattens_linebreaks():
    assert definition_improve("A wall.\n\nMore text.") == "A wall.; More text."
