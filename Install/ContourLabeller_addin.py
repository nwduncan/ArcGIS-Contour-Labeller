"""
Project: ArcMap Contour Labeller
Author: Nathan Duncan
Date: 13/09/2016
* Designed to be used with the Maplex labelling engine.
* Label rotation value follows ArcGIS arithmetic type.
* Resulting feature layers reside in your scratch workspace. After creating
  it's recommended that you exportthese to a more permanent workspace.
"""



# import modules
import arcpy
import pythonaddins
import itertools
import uuid
import os
import math


# remove temporary data and refresh
def remove_temp():

    """
    This function removes all temporary data and resets the toolbar.
    """

    # set layer to remove
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    rem_layer = arcpy.mapping.Layer(DrawLabelsTool.temp_layer_name)

    # remove layer from document and delete it from memory
    arcpy.mapping.RemoveLayer(df, rem_layer)
    arcpy.Delete_management(DrawLabelsTool.temp_label_layer)

    # reset toolbar status
    DrawLabelsTool.temp_layer_status = False
    CreateLabelsLayer.enabled = False
    ResetLabelLines.enabled = False

    # refresh
    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()


# this function helps explode and redraw the polylines
def pairs(input_iter):

    """
    A function that pairs items from an iterator as (current, next).
    Returns pairs as tuples in an itertools.izip object.

    Arguments:
    input_iter -- an iterable object. In this tool a list is supplied.

    Example:
    >>> for pair in pairs([1,2,3,4]):
    >>>     print pair
    (1, 2)
    (2, 3)
    (3, 4)
    """

    x, y = itertools.tee(input_iter)
    next(y, None)
    return itertools.izip(x, y)


def getAngle(p1, p2):

    """
    A function which returns the angle to be used for the label rotation.
    Uses the ArcGIS arithmetic angle type.
    """

    x_diff = p2[0] - p1[0]
    y_diff = p2[1] - p1[1]
    angle = math.degrees(math.atan2(y_diff, x_diff))
    angle = ((angle + 360) % 360)
    if angle <= 90:
        angle = angle + 270
    else:
        angle = angle - 90
    return angle



# Contour layer combobox class
class ContourLayerCombo(object):

    """
    Implementation for ContourLabeller.ContourLayerCombo (ComboBox)
    """

    def __init__(self):

        # initial default variables
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWWWWWWWWW'
        self.width = 'WWWWWWWWWWWWW'
        self.items = []
        self.layer = ''


    # on selection change...
    def onSelChange(self, selection):

        # set selected layer it as active and attempt to find the height field.
        self.layer = selection
        HeightFieldCombo.refresh()


    # on focus...
    def onFocus(self, focused):

        # repopulate the drop down with all possible contour feature layers
        # in the table of contents
        if focused:
            mxd = arcpy.mapping.MapDocument("CURRENT")
            layers = arcpy.mapping.ListLayers(mxd)

            # reset list items
            self.items = []

            # repopulate list items
            for layer in layers:

                if layer.isFeatureLayer:
                    desc = arcpy.Describe(layer)

                    # only use polyline layers...
                    if desc.featureClass.shapeType == 'Polyline':

                        # and do not include the temporary label lines layer
                        if (DrawLabelsTool.temp_layer_status == True and
                                layer.name == DrawLabelsTool.temp_layer_name):
                            pass

                        else:
                            self.items.append(layer.name)


    # on refresh...
    def refresh(self):

        mxd = arcpy.mapping.MapDocument("CURRENT")
        layers = arcpy.mapping.ListLayers(mxd)
        self.items = layers



# Draw contour label lines tool
class DrawLabelsTool(object):

    """
    Implementation for ContourLabeller.DrawLabelsTool (Tool)
    """

    def __init__(self):

        # initial default variables
        self.enabled = True
        self.shape = "Line"
        self.cursor = 3
        self.temp_layer_status = False
        self.temp_label_layer = ''
        self.temp_layer_name = ''


    # on mouse down...
    def onMouseDown(self, x, y, button, shift):

        # make sure the user is in data view
        mxd = arcpy.mapping.MapDocument("CURRENT")
        view = mxd.activeView
        if view == "PAGE_LAYOUT":
            pythonaddins.MessageBox("This tool will not work in Layout View. "
                                  + "Please change to Data View before running",
                                    "Error", 0)

        # create the temporary contour label lines layer if it doesn't
        # already exist
        else:

            # check status of layer
            if not self.temp_layer_status:

                # create a random string to be used as layer name
                self.temp_layer_name = 'a'+str(uuid.uuid4().hex)

                # create temporary feature class in memory
                self.temp_label_layer = arcpy.CreateFeatureclass_management('in_memory',
                                            self.temp_layer_name, 'POLYLINE')

                # add the 'label_rotation' field
                arcpy.AddField_management(self.temp_label_layer, 'label_rotation',
                                            "DOUBLE")

                # set the layer to visible if it is not already
                new_layer = arcpy.mapping.Layer(self.temp_layer_name)
                if not new_layer.visible:
                    new_layer.visible = True
                    arcpy.RefreshTOC()

                # create an arcpy.InsertCursor object to allow drawn lines
                # to be added to temporary layer
                self.i_cursor = arcpy.da.InsertCursor(self.temp_label_layer,
                                    ['SHAPE@', 'label_rotation'])

                # set status and enable buttons
                self.temp_layer_status = True
                CreateLabelsLayer.enabled = True
                ResetLabelLines.enabled = True


    # when a polyline has been drawn...
    def onLine(self, line_geometry):

        # make sure the user is in data view
        mxd = arcpy.mapping.MapDocument("CURRENT")
        view = mxd.activeView
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        sr = df.spatialReference.PCSName

        if view != "PAGE_LAYOUT" and sr != '':

            # geometry object
            geom = line_geometry

            # a list to populate with each xy coordinate used to draw the line
            # [[x1, y1], [x2, y2], [x3, y3]... ]
            points = []

            # a list to populate with the line geometry
            geom_lines = []

            # grab all the points in order and add it to the points list
            for part in geom:
                for point in part:
                    points.append([point.X, point.Y])

            # for each pair of points...
            for pair in pairs(points):

                # create an array...
                array = arcpy.Array([arcpy.Point(pair[0][0], pair[0][1]),
                                     arcpy.Point(pair[1][0], pair[1][1])])

                # use it to create a polyline...
                polyline = arcpy.Polyline(array)

                # and store it in the geom_lines list
                geom_lines.append(polyline)

            # write the lines to the temporary contour lines layer
            for line in geom_lines:

                # find the first and last point...
                first_point = (line.firstPoint.X, line.firstPoint.Y)
                last_point = (line.lastPoint.X, line.lastPoint.Y)

                # use these to determine the labal rotation value...
                angle = getAngle(first_point, last_point)
                try:
                    # and write the line and rotation to the contour lines layer
                    self.i_cursor.insertRow([line, angle])

                # error catching
                except:
                    e = sys.exc_info()[0]
                    print ("Contour Labeller: Error({0}): {1}\nError"
                            +" encountered when attempting to write"
                            +" geometries to the label lines layer".format(e.errno,
                            e.strerr))

            arcpy.RefreshActiveView()

        # display some error messages if the above conditions are not met
        else:

            # if drawing in the layout view
            if view == "PAGE_LAYOUT":
                pythonaddins.MessageBox("This tool will not work in Layout View. "
                                        +"Please change to Data View before running",
                                        "Error", 0)

            # if drawing in a dataframe with no spatial reference
            else:
                pythonaddins.MessageBox("No spatial reference detected.",
                                        "Error", 0)


# Contour height field combobox
class HeightFieldCombo(object):

    """
    Implementation for ContourLabeller.HeightFieldCombo (ComboBox)
    """

    def __init__(self):
        # inital default variables
        self.items = []
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWWWW'
        self.width = 'WWWWWWWW'
        self.value = ''


    # on selection change...
    def onSelChange(self, selection):

        self.value = selection

    # on refresh
    def refresh(self):

        # find all the fields within the ContourLayerCombo.layer layer
        # and populate the combobox items
        if ContourLayerCombo.layer != '':
            fields = [ f.name for f in arcpy.ListFields(ContourLayerCombo.layer) ]
            self.items = fields

            # find a field which contains any of the items in the use_field list
            # and assume it to be the contour's height. Edit this list to suit
            use_field = ['AHD', 'Height']
            test_for_fields = [ i for e in use_field for i in fields if e in i ]

            # if some fields are found use the first result to populate self.value
            if len(test_for_fields) > 0:
                self.value = test_for_fields[0]

            # if none found, set value to '' and have the user choose
            else:
                self.value = ''



# Build contour points button
class CreateLabelsLayer(object):

    """
    Implementation for ContourLabeller.CreateLabelsLayer (Button)
    """

    def __init__(self):
        # initial default variables
        self.enabled = False
        self.checked = False


    # on button press...
    def onClick(self):

        # make sure the user is in data view
        mxd = arcpy.mapping.MapDocument("CURRENT")
        view = mxd.activeView
        if view == "PAGE_LAYOUT":
            pythonaddins.MessageBox("This tool will not work in Layout View. "
                                  + "Please change to Data View before running",
                                    "Error", 0)

        # make sure both the required combobox fields are filled
        elif ContourLayerCombo.layer == '' or HeightFieldCombo.value == '':
            pythonaddins.MessageBox("Make sure that you have selected both the"
                                  + " contour feature layer and height field"
                                  + " before running this tool.",
                                    "Error", 0)

        # if true then a new document has been opened or a layer has been
        # removed or something else entirely...
        elif not (arcpy.Exists(ContourLayerCombo.value) and
                    arcpy.Exists(DrawLabelsTool.temp_layer_name)):

            # reset toolbar status
            DrawLabelsTool.temp_layer_status = False
            CreateLabelsLayer.enabled = False
            ResetLabelLines.enabled = False

            # refresh
            arcpy.RefreshTOC()
            arcpy.RefreshActiveView()

        # if it's all good then use arcpy.Intersect_analysis to determine
        # contour label locations
        else:

            # selected contour layer and the temporary contour lable lines layer
            in_layers = [ContourLayerCombo.value, DrawLabelsTool.temp_layer_name]

            # creates the new layer in the scratchworkspace
            # resulting layer should be exported to a more permanent
            # location to avoid lost data
            # -
            # the resulting layer name contains a random string to avoid
            # overwriting when creating multiple label layers
            out_layer = os.path.join(arcpy.env.scratchWorkspace,
            'Contour_Labels_'+str(DrawLabelsTool.temp_layer_name[:5]))
            intersect_result = arcpy.Intersect_analysis(in_layers, out_layer,
                                "ALL", "", "POINT")

            # delete unessecary fields using arcpy.DeleteField_management
            # these are the fields we want to keep
            keep_fields = [u'OBJECTID', u'Shape', u'label_rotation',
                            HeightFieldCombo.value]

            # find all other fields and delete them
            delete_fields = [ f.name for f in arcpy.ListFields(intersect_result)
                              if f.name not in keep_fields ]
            arcpy.DeleteField_management(intersect_result, delete_fields)

            # remove the temporary data and refresh
            remove_temp()



# reset button
class ResetLabelLines(object):

    """
    Implementation for ContourLabeller.ResetLabelLines (Button)
    """


    def __init__(self):

        # initial default variables
        self.enabled = False
        self.checked = False

    # on button press...
    def onClick(self):

        # if true then a new document has been opened or a layer has been
        # removed or something else entirely...
        if not arcpy.Exists(DrawLabelsTool.temp_layer_name):

            # reset toolbar status
            DrawLabelsTool.temp_layer_status = False
            CreateLabelsLayer.enabled = False
            ResetLabelLines.enabled = False

            # refresh
            arcpy.RefreshTOC()
            arcpy.RefreshActiveView()

        # if theres currently some temporary data delete it and refresh
        else:
            remove_temp()
