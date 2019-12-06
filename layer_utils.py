# -*- coding: utf-8 -*
from qgis.utils import iface
from qgis.core import QgsVectorLayer, QgsFeature, QgsPoint, QgsGeometry
from .algorithmNewPoint import dst
from .compat import QgsProject, buildGeomPoint, message_log_levels
from qgis.core import QgsMessageLog

from .csv_utils import table_info

# Store references to the layers
layer_line = None
layer_point = None

LINE_LAYER_BASE_NAME = "lines"
POINT_LAYER_BASE_NAME = "points"

ONE_KM = 12
STEP = 0.1

def compute_line_distance(row_data):
    """Process the data to find the length of the line on the world

    Parameters
    ----------
    row_data : list
        An array of data from the model

    Return
    ------
    res_distance : float
        The distance for the line
    """
    distance = row_data['PUISSANCE_SIGNAL'] + row_data['NIVEAU_FILTRE']
    res_distance = 1 - (distance - ONE_KM) * STEP
    return res_distance

def create_layers(array, layer_suffix = ""):
    """Create a layer based on the given model rows.

    Parameters
    ----------
    array : list of TrackingModel items
    layer_suffix : str
        A potential suffix to add to all the layer created
    """

    # Draw the available points on their layer
    clear_layers()
    draw_points(array, POINT_LAYER_BASE_NAME + layer_suffix)
    draw_lines(array, LINE_LAYER_BASE_NAME + layer_suffix)

def draw_points(rows, layer_name):
    global layer_point
    """Draw the points on a layer
    """

    # Specify the geometry type
    layer_point = QgsVectorLayer('Point?crs=epsg:4230', layer_name, 'memory')
    layer_point.setCustomProperty("skipMemoryLayersCheck", 1)
    prov_point = layer_point.dataProvider()

    # Create and add point features
    features = []
    for row in rows:
        new_geometry = make_point_geometry(row)
        new_feature = QgsFeature()
        new_feature.setGeometry(new_geometry)
        features.append(new_feature)
    prov_point.addFeatures(features)
    layer_point.updateExtents()
    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayers([layer_point])

def draw_lines(rows, layer_name):
    global layer_line
    """Draw the lines on a layer
    """

    # Specify the geometry type
    layer_line = QgsVectorLayer('LineString?crs=epsg:4230', layer_name, 'memory')
    layer_line.setCustomProperty("skipMemoryLayersCheck", 1)
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


def make_point_geometry(row):
    if row['can_draw_point']:
        inX = row['data']['X']
        inY = row['data']['Y']
        return buildGeomPoint(inX, inY)
    else:
        return QgsGeometry()

def make_line_geometry(row):
    if row['can_draw_line']:
        data = row['data']
        x = data['X']
        y = data['Y']
        line_distance = compute_line_distance(data)
        x_res, y_res = dst(y, x, data['AZIMUT'], line_distance)
        point = QgsPoint(x, y)
        point2 = QgsPoint(y_res, x_res)
        return QgsGeometry.fromPolyline([point, point2])
    else:
        return QgsGeometry()

def update_point(row):
    global layer_point

    new_geometry = make_point_geometry(row)

    layer_point.startEditing()
    layer_point.changeGeometry(row['data']['ID_OBSERVATION'], new_geometry)
    layer_point.commitChanges()

def update_line(row):
    global layer_line

    new_geometry = make_line_geometry(row)

    layer_line.startEditing()
    layer_line.changeGeometry(row['data']['ID_OBSERVATION'], new_geometry)
    layer_line.commitChanges()

def update_layers(row_info):
    update_point(row_info)
    update_line(row_info)

def clear_layers():
    global layer_point
    global layer_line

    if layer_point is not None:
        QgsProject.instance().removeMapLayers([layer_point.id()])
        layer_point = None
    if layer_line is not None:
        QgsProject.instance().removeMapLayers([layer_line.id()])
        layer_line = None
    iface.mapCanvas().refresh()

def clear_layer(layer):
    """Suppression d'un layer (clear)"""
    layers = QgsProject.instance().mapLayersByName(layer)
    QgsProject.instance().removeMapLayers([layer.id() for layer in layers])
    iface.mapCanvas().refresh()
