# -*- coding: utf-8 -*

from random import randrange

from qgis.utils import iface
from qgis.core import QgsVectorLayer, QgsFeature, QgsPoint, QgsGeometry, QgsField, QgsWkbTypes
from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem, edit
from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsMarkerSymbol
from .algorithmNewPoint import dst
from .compat import QgsProject, buildGeomPoint, message_log_levels
from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QVariant

from .csv_utils import labels

# Store references to the layers
layerLine = None
layerPoint = None
layerInter = None

LINE_LAYER_BASE_NAME = "lines"
POINT_LAYER_BASE_NAME = "points"

# Autozoom and properties
curr_extent = None
segment_length = 1
CRS = QgsCoordinateReferenceSystem('epsg:4326')

def createLayers(array, layer_suffix = ""):
    """Create a layer based on the given model rows.

    Parameters
    ----------
    array : list of TrackingModel items
    layer_suffix : str
        A potential suffix to add to all the layer created
    """

    # Draw the available points on their layers
    drawLines(array, LINE_LAYER_BASE_NAME + layer_suffix)
    drawPoints(array, POINT_LAYER_BASE_NAME + layer_suffix)
    set_id(array)
    set_filter([row['id_observation'] for row in array], False)

def clearLayers():
    global layerLine
    global layerPoint
    global layerInter
    global curr_extent

    clearLayer(layerLine)
    layerLine = None
    clearLayer(layerPoint)
    layerPoint = None
    clearLayer(layerInter)
    layerInter = None
    iface.mapCanvas().refresh()

    curr_extent = None

def clearLayer(layer):
    """Suppression d'un layer (clear)"""
    if layer is not None:
        try:
            QgsProject.instance().removeMapLayers([layer.id()])
        except:
            QgsMessageLog.logMessage('Layer already removed',
                                     'Radiotrack', level=message_log_levels["Info"])

def drawLines(rows, layer_name):
    global layerLine
    """Draw the lines on a layer
    """

    # Specify the geometry type
    layerLine = QgsVectorLayer('LineString?crs=epsg:4326', layer_name, 'memory')
    layerLine.setCrs(CRS)
    # Avoid warning when closing project
    layerLine.setCustomProperty("skipMemoryLayersCheck", 1)
    with edit(layerLine):
        layerLine.addAttribute(QgsField("id", QVariant.String))
        layerLine.addAttribute(QgsField("filter", QVariant.Int))
        layerLine.addAttribute(QgsField("biangulation", QVariant.Int))
    layerLine.setSubsetString('NOT filter')
    provLine = layerLine.dataProvider()

    # Create and add line features
    features = []
    for row in rows:
        new_geometry = makeLine_geometry(row)
        new_feature = QgsFeature()
        new_feature.setGeometry(new_geometry)
        features.append(new_feature)
    provLine.addFeatures(features)

    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayers([layerLine])

    #XXX return fids here
    fids = [feature.id() for feature in layerLine.getFeatures()]

def drawPoints(rows, layer_name):
    global layerPoint
    """Draw the points on a layer
    """

    # Specify the geometry type
    layerPoint = QgsVectorLayer('Point?crs=epsg:4326', layer_name, 'memory')
    layerPoint.setCrs(CRS)
    # Avoid warning when closing project
    layerPoint.setCustomProperty("skipMemoryLayersCheck", 1)
    with edit(layerPoint):
        layerPoint.addAttribute(QgsField("id", QVariant.String))
        layerPoint.addAttribute(QgsField("filter", QVariant.Int))
        layerPoint.addAttribute(QgsField("biangulation", QVariant.Int))
    layerPoint.setSubsetString('NOT filter')
    provPoint = layerPoint.dataProvider()

    # Create and add point features
    features = []
    for row in rows:
        new_geometry = makePoint_geometry(row)
        new_feature = QgsFeature()
        new_feature.setGeometry(new_geometry)
        features.append(new_feature)
    provPoint.addFeatures(features)

    # Custom renderer for colors
    renderer = QgsCategorizedSymbolRenderer()
    renderer.setClassAttribute("id")
    layerPoint.setRenderer(renderer)

    # Add the layer to the Layers panel
    QgsProject.instance().addMapLayers([layerPoint])

    #XXX return ids here (check this it the same as for line)
    ids = [feature.id() for feature in layerPoint.getFeatures()]

def updateRowLinePoint(row):
    """Update the value of a single observation"""
    layerLine.startEditing()
    layerPoint.startEditing()

    new_geometry = makeLine_geometry(row)
    layerLine.changeGeometry(row['id_observation'], new_geometry)
    new_geometry = makePoint_geometry(row)
    layerPoint.changeGeometry(row['id_observation'], new_geometry)

    layerLine.commitChanges()
    layerPoint.commitChanges()

    layerLine.updateExtents()
    layerPoint.updateExtents()

    """The current row geometries are updated when the row is edited.
    Thus, it is not an hidden row. Thus, if it has to be kept by the
    filter, the filtering will not be updated. In this case, we need
    to initialize the value to False."""
    set_filter([row['id_observation']], False)

def makeLine_geometry(row_data):
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

def makePoint_geometry(row_data):
    try:
        inX = row_data[labels['X']]
        inY = row_data[labels['Y']]
        return buildGeomPoint(inX, inY)
    except:
        return QgsGeometry()

def set_id(array):
    renderer = layerPoint.renderer()
    ids = set([cat.value() for cat in renderer.categories()])
    for row in array:
        if row['id'] not in ids:
            """Generate a random color such that the lightness is sufficient to
            read text when used in background. The sum of RGB is at
            least 256 (which is one third of the max lightness)."""
            rgb = randrange(256), randrange(256), randrange(256)
            lighter = max(0, 256 - sum(rgb)) // 3
            rgb = tuple(col + lighter for col in rgb)
            symbol = QgsMarkerSymbol.createSimple({'size' : "3.0",
                                                   'color' : "%d,%d,%d" % rgb})
            cat = QgsRendererCategory(row['id'], symbol, row['id'])
            renderer.addCategory(cat)
            ids.add(row['id'])

    fieldIdx = layerPoint.dataProvider().fieldNameIndex('id')
    attrs = {row['id_observation']: {fieldIdx: row['id']} for row in array}

    layerLine.dataProvider().changeAttributeValues(attrs)
    layerLine.triggerRepaint()

    layerPoint.dataProvider().changeAttributeValues(attrs)
    layerPoint.triggerRepaint()

def get_id_colors():
    return {cat.value(): cat.symbol().color()
            for cat in layerPoint.renderer().categories()}

def set_filter(id_rows, is_filtered):
    if len(id_rows) == 0 or layerPoint is None or layerLine is None:
        return

    # Assumes that the fieldIdx is the same in both layers
    fieldIdx = layerPoint.dataProvider().fieldNameIndex('filter')
    attrs = {feature_id: {fieldIdx: is_filtered} for feature_id in id_rows}

    layerLine.dataProvider().changeAttributeValues(attrs)
    layerLine.triggerRepaint()
    layerLine.updateExtents()

    layerPoint.dataProvider().changeAttributeValues(attrs)
    layerPoint.triggerRepaint()
    layerPoint.updateExtents()

    # If zoom set has not changed (autozoom), adjust the zoom
    if autoZoom():
        updateZoom()

def drawIntersection(biangs):
    #TODO change name of layer
    #TODO add point renderer for color based on name
    #TODO add filtering depending on line
    global layerLine
    global layerPoint
    global layerInter

    clearLayer(layerInter)

    # Specify the geometry type
    layerInter = QgsVectorLayer('Point?crs=epsg:4326', 'intersection', 'memory')
    layerInter.setCrs(CRS)
    # Avoid warning when closing project
    layerInter.setCustomProperty("skipMemoryLayersCheck", 1)

    provInter = layerInter.dataProvider()
    features = []
    for obs1, obs2 in biangs:
        geom1 = layerLine.getGeometry(obs1)
        geom2 = layerLine.getGeometry(obs2)
        newGeom = geom1.intersection(geom2)
        if newGeom.type() == QgsWkbTypes.PointGeometry:
            newFeat = QgsFeature()
            newFeat.setGeometry(newGeom)
            features.append(newFeat)
    provInter.addFeatures(features)

    QgsProject.instance().addMapLayers([layerInter])
    layerInter.triggerRepaint()

def updateZoom():
    global curr_extent

    full_extent = updateFullExtent()
    # Does not zoom to full extent because it does not integrate well
    # with a basemap
    iface.mapCanvas().zoomToFeatureExtent(full_extent)
    curr_extent = iface.mapCanvas().extent()

def updateFullExtent():
    full_extent = layerPoint.extent()
    full_extent.combineExtentWith(layerLine.extent())
    # Assumes that the CRS is the same in both layers
    sourceCrs = layerPoint.crs()
    destCrs = QgsProject.instance().crs()
    xform = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
    geom = QgsGeometry.fromRect(full_extent)
    return xform.transform(full_extent)

def autoZoom():
    if curr_extent is None:
        return True
    current_extent = iface.mapCanvas().extent()
    return current_extent.contains(curr_extent) and \
       curr_extent.contains(current_extent)

def set_segment_length(length):
    global segment_length
    segment_length = length

def set_EPSG4326():
    global CRS
    CRS = QgsCoordinateReferenceSystem('epsg:4326')
    updateCRS()

def set_project_CRS():
    global CRS
    CRS = QgsProject.instance().crs()
    updateCRS()

def updateCRS():
    if layerLine is None or layerPoint is None:
        return
    layerLine.setCrs(CRS)
    layerLine.triggerRepaint()
    layerLine.updateExtents()
    layerPoint.setCrs(CRS)
    layerPoint.triggerRepaint()
    layerPoint.updateExtents()
    if autoZoom():
        updateZoom()
