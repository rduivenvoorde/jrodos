
Technical and Developer Documentation
=====================================

.. contents::
   :local:

Sources live here: https://git.svc.cal-net.nl/qgis/jrodos/

There is a master and a develop branch

PyCharm is used for Python Developing (licensed version you can remote plugin development)

Build and Deployment
--------------------

On Linux you can use `make zip`, this will build a ready to use plugin zip with the
version number in the filename taken from the 'version' tag from the 'metadata.txt'

The zip will be copied to the 'repo` directory

To deploy: scp the plugins.xml from the plugins repo (http://repo.svc.cal-net.nl/repo/rivm/qgis/)
and edit the xml to correspond to the version and zip file name of this version. E.g.:

::

 cd repo
 scp root@repo.svc.cal-net.nl:/var/www/html/repo/rivm/qgis/plugins.xml .
 # do edits and copy both updated plugins.xml AND new plugin the the server
 scp plugins.xml root@repo.svc.cal-net.nl:/var/www/html/repo/rivm/qgis/
 scp JRodos.2.0.9.zip root@repo.svc.cal-net.nl:/var/www/html/repo/rivm/qgis/


Modules and Classes
-------------------

Main (QGIS Plugin) class is 'JRodos' in 'jrodos.py'

Logging: '__init.py__' has some magic to be able to write log lines to QGIS's Message Log panel

Settings: settings are done via 'JRodosSettings' class in 'jrodos_settings.py' working with
a small framework to easily create settings dialogs and write settings automagically to user QSettings.
(see module 'qgissettingmanager').

The plugin has a set of 'providers' in the 'providers' module. Providers are data provider classes
crafted to be able to retrieve data asynchronously(!!) (to be able to retrieve big chunks of data
without freezing up QGIS gui.

For the small Graph in the plugin `PyQtGraph library <https://www.pyqtgraph.org/>`_ (currently Version 0.10.0)is used.
That module/library is INCLUDED in the plugin (module 'pyqtgraph' in source dir) so no install is required.

ALl ui/gui files for dialogs etc are in the 'ui' module:

 - 'jrodos_dialog_base.ui' -> 'jrodos_dialog.py' will become the JRodos Model dialog
 - 'jrodos_measurements_dialog_base.ui' -> 'jrodos_measurements_dialog' will become the JRodos Measurements dialog
 - 'jrodos_graph_widget.ui' -> 'jrodos_graph_widget' for the 'Graph panel'
 - 'jrodos_filter_dialog.ui' -> 'jrodos_filter_dialog' for the generic list (eg for the full list of JRodos 'paths')


Workflow
--------

The main function (to be started when you push the little 'JRodos' button) is 'JRodos.run'.

That will:

 - Create a group 'JRodos plugin layers' in the layer group (OR try to re-use that group if already available)

 - Show the JRodos model dialog which:

    - Using: 'JRodosProjectProvider' goes to a REST service to retrieve all projects:
      http://jrodos.prd.cal-net.nl/rest-2.0/jrodos/projects
    - Upon the selection of one project from that list:
      Get the specifig Project information (also using 'JRodosProjectProvider'), eg
      http://jrodos.prd.cal-net.nl/rest-2.0/jrodos/projects/6851
      Which will then fill the Tasks (Models) and DataItems
      (DataPaths like: 'Total Effective Potential Dose') dropdowns and fill other information
    - Upon selection of a Task switch the DataPaths to the for that Task available ones
    - Then 'JRodosModelOutputProvider' (providers/jrodos_model_output_provider.py) is started to actually
      fire a WPS POST request, to retrieve a zip with a GeoPackage and (optional) a sld/style file
    - NOTE: the full WPS-xml data plus other WPS parameters are written to 'jrodos_output_settings.txt' in the output directory
    - Upon retrieving the data, save it in the output directory and then load that file into a memory layer

 - Show the Measurements dialog:

    - IF the user loaded a Model, set the start/end times to the Model ones

 - Retrieve the CalWeb projects
   http://microservices.prd.cal-net.nl:8300/calweb/projects
   (and/or current active one)
   http://microservices.prd.cal-net.nl:8300/calweb/projects/current






