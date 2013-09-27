Pareto JSON export
==================

This product allows exporting a partial or full Plone instance to JSON. It is
generic and knows how to serialize Archetypes schemas (including
schemaextender fields) as well as 'core' Zope objects. Since it uses ZCML
for serializer registration, it's easy to override existing serializers or
plug in new ones.

Installation
------------

Installing happens using the normal Plone mechanism, so you can visit
portal_quickinstaller's 'install' tab and install the product. This will
create a new permission and role 'JSONImporter' that can be used to explicitly
allow only JSON export to certain users.

Usage
-----

Once the product is installed, any object inside the Zope object tree will
sport a view called 'json_export', which supports a single GET variable
called 'recursive' to explain whether you want only the object's JSON, or
that of all children as well. Example::

  http://my.plone/Plone/@@json_export

will export the data of the 'Plone' object, but no more. Passing the
'recursive' flag like this::

  http://my.plone/Plone/@@json_export?recursive=true

will export the 'Plone' object's data, and that of all its children,
recursively.

Questions, remarks, etc.
------------------------

Mail guido.wesdorp@pareto.nl or johnnydebris@gmail.com.
