# -*- coding: utf-8 -*
from qgis.utils import iface
from qgis.core import QgsVectorLayer, QgsFeature, QgsPoint, QgsGeometry, QgsField, edit
from .algorithmNewPoint import dst
from .compat import QgsProject, buildGeomPoint, message_log_levels
from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QVariant

from .csv_utils import labels

# Store references to the layers
layer_line = None
layer_point = None

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

    # Draw the available points on their layer
    draw_points(array, POINT_LAYER_BASE_NAME + layer_suffix)
    draw_lines(array, LINE_LAYER_BASE_NAME + layer_suffix)
    set_filter([row['data']['id_observation'] for row in array], False)

def draw_points(rows, layer_name):
    global layer_point
    """Draw the points on a layer
    """

    # Specify the geometry type
    layer_point = QgsVectorLayer('Point?crs=epsg:4230', layer_name, 'memory')
    # Avoid warning when closing project
    layer_point.setCustomProperty("skipMemoryLayersCheck", 1)
    with edit(layer_point):
        layer_point.addAttribute(QgsField("filter", QVariant.Int))
    layer_point.setSubsetString('NOT filter')
    prov_point = layer_point.dataProvider()

    # Create and add point features
    features = []
    for row in rows:
        new_geometry = make_point_geometry(row['data'])
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
    layer_line = QgsVectorLayer('LineString?crs=epsg:4230', layer_name, 'memory')
    # Avoid warning when closing project
    layer_line.setCustomProperty("skipMemoryLayersCheck", 1)
    with edit(layer_line):
        layer_line.addAttribute(QgsField("filter", QVariant.Int))
    layer_line.setSubsetString('NOT filter')
    prov_line = layer_line.dataProvider()

    # Create and add line features
    features = []
    for row in rows:
        new_geometry = make_line_geometry(row['data'])
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
    global segment_length
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
    global layer_point
    global layer_line

    layer_point.startEditing()
    layer_line.startEditing()

    # XXX redundant code
    for row in rows:
        new_geometry = make_point_geometry(row['data'])
        layer_point.changeGeometry(row['data']['id_observation'], new_geometry)
        new_geometry = make_line_geometry(row['data'])
        layer_line.changeGeometry(row['data']['id_observation'], new_geometry)

    layer_point.commitChanges()
    layer_line.commitChanges()

    layer_point.updateExtents()
    layer_line.updateExtents()

    set_filter([row['data']['id_observation'] for row in rows], False)

def set_filter(id_rows, filter):
    global layer_point
    global layer_line

    if len(id_rows) == 0:
        return

    # Assumes that the fieldIdx is the same in both layers
    fieldIdx = layer_point.dataProvider().fieldNameIndex('filter')
    attrs = {id: {fieldIdx: filter} for id in id_rows}

    layer_point.dataProvider().changeAttributeValues(attrs)
    layer_point.triggerRepaint()

    layer_line.dataProvider().changeAttributeValues(attrs)
    layer_line.triggerRepaint()

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
