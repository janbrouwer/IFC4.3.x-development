IfcInventory
============
An inventory is a list of items within an enterprise.  
  
Various types of inventory can be included. These are identified by the range
of values within the inventory type enumeration which includes space, asset,
and furniture. User defined inventories can also be defined for lists of
particular types of element such as may be required in operating and
maintenance instructions. Such inventories should be constrained to contain a
list of elements of a restricted type.  
  
There are a number of actors that can be associated with an inventory, each
actor having a role. Actors within the scope of the project are indicated
using the
[IfcRelAssignsToActor](../../ifckernel/lexical/ifcrelassignstoactor.htm)
relationship in which case roles should be defined through the
[IfcActorRole](../../ifcactorresource/lexical/ifcactorrole.htm) class;
otherwise principal actors are identified as attributes of the class. In the
existence of both, direct attributes take precedence.  
  
There are a number of costs that can be associated with an inventory, each
cost having a role. These are specified through the _CurrentValue_ and
_OriginalValue_ attributes.  
  
> HISTORY  New entity in IFC2.0.  
  
{ .change-ifc2x4}  
> IFC4 CHANGE  All attributes optional, Where Rule removed.  
[ _bSI
Documentation_](https://standards.buildingsmart.org/IFC/DEV/IFC4_2/FINAL/HTML/schema/ifcsharedfacilitieselements/lexical/ifcinventory.htm)


Attribute definitions
---------------------
| Attribute      | Description                                                                                                                                           |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| Jurisdiction   | The organizational unit to which the inventory is applicable.                                                                                         |
| LastUpdateDate | The date on which the last update of the inventory was carried out.\X\0D\X\0D{ .change-ifc2x4}\X\0D> IFC4 CHANGE Type changed from IfcDateTimeSelect. |

Associations
------------
| Attribute          | Description   |
|--------------------|---------------|
| ResponsiblePersons |               |
| CurrentValue       |               |
| OriginalValue      |               |
| PredefinedType     |               |

