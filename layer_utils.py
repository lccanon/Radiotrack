# -*- coding: utf-8 -*
from qgis.utils import iface
from qgis.core import QgsVectorLayer, QgsFeature, QgsPoint, QgsGeometry, QgsField, QgsCoordinateTransform, QgsCoordinateReferenceSystem, edit
from .algorithmNewPoint import dst
from .compat import QgsProject, buildGeomPoint, message_log_levels
from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QVariant

from .csv_utils import labels

# Store references to the layers
layer_line = None
layer_point = None
full_extent = None
curr_extent = None
CRS = QgsCoordinateReferenceSystem('epsg:4326')

LINE_LAYER_BASE_NAME = "lines"
POINT_LAYER_BASE_NAME = "points"

segment_length = 1

def set_segment_length(length):
    global segment_length
    segment_length = length

def create_layers(array, layer_suffix = ""):
    """Create a layer based on the given model rows.

    Parameters
    ----------
    array : list of TrackingModel items
    layer_suffix : str
        A potential suffix to add to all the layer created
    """

    # Draw the available points on their layers
    draw_lines(array, LINE_LAYER_BASE_NAME + layer_suffix)
    draw_points(array, POINT_LAYER_BASE_NAME + layer_suffix)
    set_filter([row['id_observation'] for row in array], False)

def updateZoom():
    global curr_extent

    updateFullExtent()
    # Does not zoom to full extent because it does not integrate well
    # with a basemap
    iface.mapCanvas().zoomToFeatureExtent(full_extent)
    curr_extent = iface.mapCanvas().extent()

def updateFullExtent():
    global full_extent

    full_extent = layer_point.extent()
    full_extent.combineExtentWith(layer_line.extent())
    # Assumes that the CRS is the same in both layers
    sourceCrs = layer_point.crs()
    destCrs = QgsProject.instance().crs()
    xform = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
    geom = QgsGeometry.fromRect(full_extent)
    full_extent = xform.transform(full_extent)

def autoZoom():
    current_extent = iface.mapCanvas().extent()
    return current_extent.contains(curr_extent) and \
       curr_extent.contains(current_extent)

def set_EPSG4326():
    global CRS
    CRS = QgsCoordinateReferenceSystem('epsg:4326')
    updateCRS()

def set_project_CRS():
    global CRS
    CRS = QgsProject.instance().crs()
    updateCRS()

def updateCRS():
    if layer_line is None or layer_point is None:
        return
    layer_line.setCrs(CRS)
    layer_line.triggerRepaint()
    layer_line.updateExtents()
    layer_point.setCrs(CRS)
    layer_point.triggerRepaint()
    layer_point.updateExtents()
    updateZoom()

def draw_points(rows, layer_name):
    global layer_point
    """Draw the points on a layer
    """

    # Specify the geometry type
    layer_point = QgsVectorLayer('Point?crs=epsg:4326', layer_name, 'memory')
    layer_point.setCrs(CRS)
    # Avoid warning when closing project
    layer_point.setCustomProperty("skipMemoryLayersCheck", 1)
    with edit(layer_point):
        layer_point.addAttribute(QgsField("filter", QVariant.Int))
    layer_point.setSubsetString('NOT filter')
    prov_point = layer_point.dataProvider()

    # Create and add point features
    features = []
    for row in rows:
        new_geometry = make_point_geometry(row)
        new_feature = QgsFeature()
        new_feature.setGeometry(new_geometry)
        features.append(new_feature)
    prov_point.addFeatures(features)
    # Update extent of the layer
    layer_point.updateExtents()
    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayers([layer_point])

def draw_lines(rows, layer_name):
    global layer_line
    """Draw the lines on a layer
    """

    # Specify the geometry type
    layer_line = QgsVectorLayer('LineString?crs=epsg:4326', layer_name, 'memory')
    layer_line.setCrs(CRS)
    # Avoid warning when closing project
    layer_line.setCustomProperty("skipMemoryLayersCheck", 1)
    with edit(layer_line):
        layer_line.addAttribute(QgsField("filter", QVariant.Int))
    layer_line.setSubsetString('NOT filter')
    prov_line = layer_line.dataProvider()

    # Create and add line features
    features = []
    for row in rows:
        new_geometry = make_line_geometry(row)
        new_feature = QgsFeature()
        new_feature.setGeometry(new_geometry)
        features.append(new_feature)
    prov_line.addFeatures(features)
    # Update extent of the layer
    layer_line.updateExtents()
    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayers([layer_line])

def make_point_geometry(row_data):
    try:
        inX = row_data[labels['X']]
        inY = row_data[labels['Y']]
        return buildGeomPoint(inX, inY)
    except:
        return QgsGeometry()

def make_line_geometry(row_data):
    try:
        x = row_data[labels['X']]
        y = row_data[labels['Y']]
        azi = row_data[labels['AZIMUT']]
        x_res, y_res = dst(y, x, azi, segment_length)
        point = QgsPoint(x, y)
        point2 = QgsPoint(y_res, x_res)
        return QgsGeometry.fromPolyline([point, point2])
    except:
        return QgsGeometry()

def add_line_and_point(rows):
    layer_line.startEditing()
    layer_point.startEditing()

    for row in rows:
        new_geometry = make_line_geometry(row)
        layer_line.changeGeometry(row['id_observation'], new_geometry)
        new_geometry = make_point_geometry(row)
        layer_point.changeGeometry(row['id_observation'], new_geometry)

    layer_line.commitChanges()
    layer_point.commitChanges()

    layer_line.updateExtents()
    layer_point.updateExtents()

    set_filter([row['id_observation'] for row in rows], False)

def set_filter(id_rows, is_filtered):
    if len(id_rows) == 0 or layer_point is None or layer_line is None:
        return

    # Assumes that the fieldIdx is the same in both layers
    fieldIdx = layer_point.dataProvider().fieldNameIndex('filter')
    attrs = {feature_id: {fieldIdx: is_filtered} for feature_id in id_rows}

    layer_line.dataProvider().changeAttributeValues(attrs)
    layer_line.triggerRepaint()
    layer_line.updateExtents()

    layer_point.dataProvider().changeAttributeValues(attrs)
    layer_point.triggerRepaint()
    layer_point.updateExtents()

    # If zoom set has not changed (autozoom), adjust the zoom
    if curr_extent is None or autoZoom():
        updateZoom()

def clear_layers():
    global layer_point
    global layer_line

    if layer_point is not None:
        try:
            QgsProject.instance().removeMapLayers([layer_point.id()])
        except:
            QgsMessageLog.logMessage('Layer already removed', 'Radiotrack', level=message_log_levels["Info"])
        layer_point = None
    if layer_line is not None:
        try:
            QgsProject.instance().removeMapLayers([layer_line.id()])
        except:
            QgsMessageLog.logMessage('Layer already removed', 'Radiotrack', level=message_log_levels["Info"])
        layer_line = None
    iface.mapCanvas().refresh()

# unused method
def clear_layer(layer_name):
    """Suppression d'un layer (clear)"""
    layers = QgsProject.instance().mapLayersByName(layer_name)
    QgsProject.instance().removeMapLayers([layer.id() for layer in layers])
    iface.mapCanvas().refresh()
