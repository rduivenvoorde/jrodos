
Documentation
=============

.. contents::
   :local:


What does it do
---------------

The JRodos plugin is a plugin to:

- view JRodos model outputs in QGIS (requested via Geoserver-JRodos WPS + REST interface for project information)
- view Measurements (requested via Measurements-WFS + SOAP interface for parameters) in QGIS
- load Rain/Weatherinformation from KNMI (WMS-Time service)
- check if TimeManager plugin is installed
- registres the above layers in TimeManager plugin to be able to (re)'play' a time/model frame


Make it work
------------

Install both(!!!) the JRodos plugin and the TimeManager plugin using QGIS Plugin Manager.

Make sure both plugins are active.

If you need some map data as background/reference layers, install 'QuickMapServices' plugin or 'PDOK Services Plugin'
via the plugin manager of QGIS.

Click de JRodos button to start the dialogs.

How does it work
----------------

The plugin is an extensive user of online services

The http communication is done via 'Providers' (provider classes)

The JRodos Model output dialog
..............................

First the available JRodos (output) projects are retrieved via a REST service (output is JSON, jrodos_project_provider.py):

http://jrodos.dev.cal-net.nl:8080/jrodos-rest-service/jrodos/projects

This will result in a list of 'projects'.

Selecting a project will result in the firing of a REST url to retrieve the information of the information
 (output is JSON, jrodos_project_provider.py):

http://jrodos.dev.cal-net.nl:8080/jrodos-rest-service/jrodos/projects/1268

At the same time a WPS request is fired to retrieve specific time related information of that project.
That is the Duration of the model/prognosis, the timetep used and the start of the release.
The JRodos WPS service running on:

http://jrodos.dev.cal-net.nl:8080/geoserver/wps

And needs 4 parameters:

- taskArg (the project name and optional the task name). Example: ``project='wps-test-multipath'&amp;model='LSMC'``
- dataitem (the JRodos) datapath ``path='Model data=;=Output=;=Prognostic Results=;=Potential doses=;=Total potential dose=;=effective'``
- columns (the timestep, an integer starting with 0)
- vertical (currently always 0)
- threshold (only return values > this value, defaults to 0)

When OK is pushed, the same WPS service is used to retrieve all model data (currently as zipped shapefiles).

The shapefiles are saved in the users /tmp directory.

Then for every timestep a shapefile is loaded, all features (gridcells) which have NOT zero values get an attribute
 added with a TimeStamp and are loaded in QGIS.

When all shapefiles are loaded in this one (memory) layer, the layer is registred with TimeManager.
The user can now use TimeManager to play the different timesteps.


The Measurements dialog
.......................

After the JRodos model dialog the Measurements Dialog is shown. If the JRodos model contained a starttime and endtime
these are prefilled in the Measurements Dialog (as you probably want to see the actual measurements in that area).

The user can choose one of the three different 'integration'-time periods:

- 10 minute data (600 seconds)
- 1 hour data (3600 minutes)
- 24 hour data (86400 minutes)

The user can choose a Quantity and a Substance. The information for this Quantity and Substance lookup list
are retrieved via a SOAP service and the CalnetMeasurementsUtilsProvider in ``calnet_measurements_utils_provider.py``

When OK is pushed, that actual data is requested (from the Measurements Postgres database) via a WFS service.

The RainRadar
.............

A timebase rainradar layer is requested from a WMS-T service of the KNMI

Example parameters:

- Name: KNMI Regen
- Url: http://geoservices.knmi.nl/cgi-bin/RADNL_OPER_R___25PCPRR_L3.cgi
- Layers: RADNL_OPER_R___25PCPRR_L3_COLOR
- Styles:
- CRS: EPSG:28992

Or

- Name: KNMI Regen
- Url: http://geoservices.knmi.nl/cgi-bin/RADNL_OPER_R___25PCPRR_L3.cgi
- Layers: RADNL_OPER_R___25PCPRR_L3_KNMI
- Styles: default
- CRS: EPSG:28992