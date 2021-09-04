# -*- coding: utf-8 -*

from random import randrange

from qgis.utils import iface
from qgis.core import QgsProject, QgsMessageLog
from qgis.core import QgsVectorLayer, QgsFeature, QgsField, edit
from qgis.core import QgsGeometry, QgsPoint, QgsPointXY, QgsWkbTypes
from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsMarkerSymbol
from .algorithmNewPoint import dst
from qgis.PyQt.QtCore import QVariant

from .csv_utils import labels

class QgsController:

    LINE_LAYER_BASE_NAME = "lines"
    POINT_LAYER_BASE_NAME = "points"
    INTER_LAYER_BASE_NAME = "intersections"

    def __init__(self):
        # Store references to the layers
        self.layerLine = None
        self.layerPoint = None
        self.layerInter = None
        self.set_EPSG4326()
        # Autozoom and properties
        self.curr_extent = None
        self.segment_length = 1

    def createLayers(self, array, layer_suffix = ""):
        """Create a layer based on the given model rows.

        Parameters
        ----------
        array : list of TrackingModel items
        layer_suffix : str
            A potential suffix to add to all the layer created
        """

        # Draw the available points on their layers
        self.drawLines(array, self.LINE_LAYER_BASE_NAME + layer_suffix)
        self.drawPoints(array, self.POINT_LAYER_BASE_NAME + layer_suffix)
        self.set_id(array)
        self.set_filter([row['id_observation'] for row in array], False)

    def clearLayers(self):
        self.clearLayer(self.layerLine)
        self.layerLine = None
        self.clearLayer(self.layerPoint)
        self.layerPoint = None
        self.clearLayer(self.layerInter)
        self.layerInter = None
        iface.mapCanvas().refresh()

        self.curr_extent = None

    def clearLayer(self, layer):
        """Suppression d'un layer (clear)"""
        if layer is not None:
            try:
                QgsProject.instance().removeMapLayers([layer.id()])
            except:
                QgsMessageLog.logMessage('Layer already removed',
                                         'Radiotrack', level = QGis.Info)

    def drawLines(self, rows, layer_name):
        """Draw the lines on a layer
        """

        # Specify the geometry type
        self.layerLine = QgsVectorLayer('LineString?crs=epsg:4326', layer_name, 'memory')
        self.layerLine.setCrs(self.CRS)
        # Avoid warning when closing project
        self.layerLine.setCustomProperty("skipMemoryLayersCheck", 1)
        with edit(self.layerLine):
            self.layerLine.addAttribute(QgsField("id", QVariant.String))
            self.layerLine.addAttribute(QgsField("filter", QVariant.Int))
            self.layerLine.addAttribute(QgsField("biangulation", QVariant.Int))
        self.layerLine.setSubsetString('NOT filter')
        provLine = self.layerLine.dataProvider()

        # Create and add line features
        features = []
        for row in rows:
            new_geometry = self.makeLine_geometry(row)
            new_feature = QgsFeature()
            new_feature.setGeometry(new_geometry)
            features.append(new_feature)
        provLine.addFeatures(features)

        # Add the layer to the Layers panel
        QgsProject.instance().addMapLayers([self.layerLine])

        #XXX return fids here
        fids = [feature.id() for feature in self.layerLine.getFeatures()]

    def drawPoints(self, rows, layer_name):
        """Draw the points on a layer
        """

        # Specify the geometry type
        self.layerPoint = QgsVectorLayer('Point?crs=epsg:4326', layer_name, 'memory')
        self.layerPoint.setCrs(self.CRS)
        # Avoid warning when closing project
        self.layerPoint.setCustomProperty("skipMemoryLayersCheck", 1)
        with edit(self.layerPoint):
            self.layerPoint.addAttribute(QgsField("id", QVariant.String))
            self.layerPoint.addAttribute(QgsField("filter", QVariant.Int))
            self.layerPoint.addAttribute(QgsField("biangulation", QVariant.Int))
        self.layerPoint.setSubsetString('NOT filter')
        provPoint = self.layerPoint.dataProvider()

        # Create and add point features
        features = []
        for row in rows:
            new_geometry = self.makePoint_geometry(row)
            new_feature = QgsFeature()
            new_feature.setGeometry(new_geometry)
            features.append(new_feature)
        provPoint.addFeatures(features)

        # Custom renderer for colors
        renderer = QgsCategorizedSymbolRenderer()
        renderer.setClassAttribute("id")
        self.layerPoint.setRenderer(renderer)

        # Add the layer to the Layers panel
        QgsProject.instance().addMapLayers([self.layerPoint])

        #XXX return ids here (check this it the same as for line)
        ids = [feature.id() for feature in self.layerPoint.getFeatures()]

    def updateRowLinePoint(self, row):
        """Update the value of a single observation"""
        self.layerLine.startEditing()
        self.layerPoint.startEditing()

        new_geometry = self.makeLine_geometry(row)
        self.layerLine.changeGeometry(row['id_observation'], new_geometry)
        new_geometry = self.makePoint_geometry(row)
        self.layerPoint.changeGeometry(row['id_observation'], new_geometry)

        self.layerLine.commitChanges()
        self.layerPoint.commitChanges()

        self.layerLine.updateExtents()
        self.layerPoint.updateExtents()

        """The current row geometries are updated when the row is edited.
        Thus, it is not an hidden row. Thus, if it has to be kept by the
        filter, the filtering will not be updated. In this case, we need
        to initialize the value to False."""
        self.set_filter([row['id_observation']], False)

    def makeLine_geometry(self, row_data):
        try:
            x = row_data[labels['X']]
            y = row_data[labels['Y']]
            azi = row_data[labels['AZIMUT']]
            x_res, y_res = dst(y, x, azi, self.segment_length)
            point = QgsPoint(x, y)
            point2 = QgsPoint(y_res, x_res)
            return QgsGeometry.fromPolyline([point, point2])
        except:
            return QgsGeometry()

    def makePoint_geometry(self, row_data):
        try:
            inX = row_data[labels['X']]
            inY = row_data[labels['Y']]
            return QgsGeometry.fromPointXY(QgsPointXY(inX, inY))
        except:
            return QgsGeometry()

    def set_id(self, array):
        renderer = self.layerPoint.renderer()
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

        fieldIdx = self.layerPoint.dataProvider().fieldNameIndex('id')
        attrs = {row['id_observation']: {fieldIdx: row['id']} for row in array}

        self.layerLine.dataProvider().changeAttributeValues(attrs)
        self.layerLine.triggerRepaint()

        self.layerPoint.dataProvider().changeAttributeValues(attrs)
        self.layerPoint.triggerRepaint()

    def get_id_colors(self):
        return {cat.value(): cat.symbol().color()
                for cat in self.layerPoint.renderer().categories()}

    def set_filter(self, id_rows, is_filtered):
        if len(id_rows) == 0 or self.layerPoint is None or self.layerLine is None:
            return

        # Assumes that the fieldIdx is the same in both layers
        fieldIdx = self.layerPoint.dataProvider().fieldNameIndex('filter')
        attrs = {feature_id: {fieldIdx: is_filtered} for feature_id in id_rows}

        self.layerLine.dataProvider().changeAttributeValues(attrs)
        self.layerLine.triggerRepaint()
        self.layerLine.updateExtents()

        self.layerPoint.dataProvider().changeAttributeValues(attrs)
        self.layerPoint.triggerRepaint()
        self.layerPoint.updateExtents()

        # If zoom set has not changed (autozoom), adjust the zoom
        if self.autoZoom():
            self.updateZoom()

    def drawIntersection(self, biangs):
        #TODO change name of layer
        #TODO add point renderer for color based on name
        #TODO add filtering depending on line
        self.clearLayer(self.layerInter)

        # Specify the geometry type
        self.layerInter = QgsVectorLayer('Point?crs=epsg:4326', 'intersection', 'memory')
        self.layerInter.setCrs(self.CRS)
        # Avoid warning when closing project
        self.layerInter.setCustomProperty("skipMemoryLayersCheck", 1)

        provInter = self.layerInter.dataProvider()
        features = []
        for obs1, obs2 in biangs:
            geom1 = self.layerLine.getGeometry(obs1)
            geom2 = self.layerLine.getGeometry(obs2)
            newGeom = geom1.intersection(geom2)
            if newGeom.type() == QgsWkbTypes.PointGeometry:
                newFeat = QgsFeature()
                newFeat.setGeometry(newGeom)
                features.append(newFeat)
        provInter.addFeatures(features)

        QgsProject.instance().addMapLayers([self.layerInter])
        self.layerInter.triggerRepaint()

    def updateZoom(self):
        full_extent = self.updateFullExtent()
        # Does not zoom to full extent because it does not integrate well
        # with a basemap
        iface.mapCanvas().zoomToFeatureExtent(full_extent)
        self.curr_extent = iface.mapCanvas().extent()

    def updateFullExtent(self):
        full_extent = self.layerPoint.extent()
        full_extent.combineExtentWith(self.layerLine.extent())
        # Assumes that the CRS is the same in both layers
        sourceCrs = self.layerPoint.crs()
        destCrs = QgsProject.instance().crs()
        xform = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
        geom = QgsGeometry.fromRect(full_extent)
        return xform.transform(full_extent)

    def autoZoom(self):
        if self.curr_extent is None:
            return True
        current_extent = iface.mapCanvas().extent()
        return current_extent.contains(self.curr_extent) and \
           self.curr_extent.contains(current_extent)

    def set_segment_length(self, length):
        self.segment_length = length

    def set_EPSG4326(self):
        self.CRS = QgsCoordinateReferenceSystem('epsg:4326')
        self.updateCRS()

    def set_project_CRS(self):
        self.CRS = QgsProject.instance().crs()
        self.updateCRS()

    def updateCRS(self):
        if self.layerLine is None or self.layerPoint is None:
            return
        self.layerLine.setCrs(self.CRS)
        self.layerLine.triggerRepaint()
        self.layerLine.updateExtents()
        self.layerPoint.setCrs(self.CRS)
        self.layerPoint.triggerRepaint()
        self.layerPoint.updateExtents()
        if self.autoZoom():
            self.updateZoom()
        if self.layerInter is None:
            return
        self.layerInter.setCrs(self.CRS)
        self.layerInter.triggerRepaint()
        self.layerInter.updateExtents()
