# -*- coding: utf-8 -*
from qgis.utils import iface
from qgis.core import QgsVectorLayer, QgsFeature, QgsPoint, QgsGeometry
from .algorithmNewPoint import dst
from .compat2qgis import QgsProject
from .compat2qgis import buildGeomPoint

# Store references to the layers
layer_line = None
layer_point = None

def createLayerLines(coordLines, layerName):
    global layer_line
    """Création d'un layer composé de lignes"""
    clearLayer(layerName)
    # Specify the geometry type
    layer_line = QgsVectorLayer('LineString?crs=epsg:4230', layerName, 'memory')
    layer_line.setCustomProperty("skipMemoryLayersCheck", 1)
    prov_line = layer_line.dataProvider()
    # Create and add line features
    features = []
    for coordonnee in coordLines:
        if type(coordonnee) is list:
            x_res,y_res = dst(coordonnee[1], coordonnee[2], coordonnee[3], coordonnee[4])
            point = QgsPoint(coordonnee[2], coordonnee[1])
            point2 = QgsPoint(y_res,x_res)
            # Add a new feature and assign the geometry
            feat_line = QgsFeature(coordonnee[0])
            feat_line.setGeometry(QgsGeometry.fromPolyline([point, point2]))
            features.append(feat_line)
        else:
            feat_no_line = QgsFeature(coordonnee)
            features.append(feat_no_line)
    prov_line.addFeatures(features)

    # Update extent of the layer
    layer_line.updateExtents()
    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayers([layer_line])

def updateLine(coordonnee):
    global layer_line

    x_res,y_res = dst(coordonnee[1], coordonnee[2], coordonnee[3], coordonnee[4])
    point = QgsPoint(coordonnee[2], coordonnee[1])
    point2 = QgsPoint(y_res,x_res)
    new_geometry = QgsGeometry.fromPolyline([point, point2])

    layer_line.startEditing()
    layer_line.changeGeometry(coordonnee[0], new_geometry)
    layer_line.commitChanges()

def removeLine(line_id):
    global layer_line
    layer_line.startEditing()
    layer_line.changeGeometry(line_id, QgsGeometry())
    layer_line.commitChanges()

def createLayerPoints(points, layerName):
    global layer_point
    """Création d'un layer composé de points"""

    clearLayer(layerName)
    # Specify the geometry type
    layer_point = QgsVectorLayer('Point?crs=epsg:4230', layerName, 'memory')
    layer_point.setCustomProperty("skipMemoryLayersCheck", 1)
    prov_point = layer_point.dataProvider()
    # Create and add point features
    features = []
    for point in points:
        if type(point) is list:
            feature_id = point[0]
            inX = point[1]
            inY = point[2]
            # Add a new feature and assign the geometry
            feat_point = QgsFeature(feature_id)
            feat_point.setGeometry(buildGeomPoint(inX, inY))
            features.append(feat_point)
        else:
            feat_no_point = QgsFeature(point)
            features.append(feat_no_point)
    prov_point.addFeatures(features)

    # Update extent of the layer
    layer_point.updateExtents()
    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayers([layer_point])

def updatePoint(point_id, coord_x, coord_y):
    global layer_point
    """Updates the point of an existing layer, or creates the point if it can't
    update it"""
    new_geometry = buildGeomPoint(coord_y, coord_x)
    layer_point.startEditing()
    if not layer_point.changeGeometry(point_id, new_geometry):
        # Force the creation of a new point
        feat_point = QgsFeature(point_id)
        feat_point.setGeometry(new_geometry)
        layer_point.addFeature(feat_point)
    layer_point.commitChanges()

def removePoint(point_id):
    global layer_point
    layer_point.startEditing()
    layer_point.changeGeometry(point_id, QgsGeometry())
    layer_point.commitChanges()

def clearLayer(layer):
    """Suppression d'un layer (clear)"""
    layers = QgsProject.instance().mapLayersByName(layer)
    QgsProject.instance().removeMapLayers([layer.id() for layer in layers])
    iface.mapCanvas().refresh()