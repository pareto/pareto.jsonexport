pareto.jsonexport - export Zope/Plone objects to JSON
=====================================================

This product allows exporting Zope/Plone objects to JSON, with a service that
notifies listeners (other services, accessed over HTTP) of changes in objects.

Note that it is by no means our goal to perform a full data export, only
data that is publically visible, and only the 'content data' (no special
metadata, no portlets, workflow state, etc.) are exported. The goal of this
is to expose a specific set of data as JSON for displaying Plone content
from another application, not to generate a full export for e.g. migration.

Export happens in a 'push' style, on changes in the database the remote
service is told (over HTTP) about the change, so data is 'pushed' to the remote
service, rather than that the remote service 'pulls' it from Plone.

Product contents
----------------

The product contains the following modules:

  * registry

    a simple registry (non-Zope object) to hold the mapping from class to
    exporter, so it's used to remember exporter code for Zope/Plone objects

  * exporters

    a set of exporter classes (and a base class)

  * service

    a simple Zope service that listens to changes on objects, determines
    whether such a change should lead to an export, and if so performs the
    export and pushes the results to the remote service
